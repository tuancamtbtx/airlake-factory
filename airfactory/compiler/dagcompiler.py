import abc
import datetime
import functools
import inspect
import os
from copy import deepcopy
from typing import Iterable, Dict, Any, List, Callable

import jsonschema
# from airflow.kubernetes.secret import Secret
# from airflow.kubernetes.volume import Volume
# from airflow.kubernetes.volume_mount import VolumeMount
from airflow.models import BaseOperator
from airflow.utils.module_loading import import_string
from dateutil.parser import parse as datetime_parser

from airfactory.core import k8s
from airfactory.core.alert import task_fail_alert
from airfactory.core.consts import (
  DefaultARGsFields,
  ExecutorConfig,
  TaskFields,
  OperatorName,
  DagFields,
)
from airfactory.common import utils
from airfactory.utils.merge import merge


class AbstractCompiler(abc.ABC):
  REFRESH_SEC = 5 * 60.0
  _scaffolds_conf = dict()
  _operators_conf = dict()


class CommonCompiler(abc.ABC):
  DEFAULT_TZ = "Asia/Ho_Chi_Minh"
  REF_VAR = "$refs."
  REF_VAR_FILE = "$vars."
  LOOKUP_VAR_DIR = "vars"
  # these fields will perform deepmerge instead of override
  SHOULD_MERGE_FIELDS = ["executor_config", "env_vars", "secrets", "conf"]

  @classmethod
  def compile_instance(cls, conf: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve datetime instance, add failure_callback and other stuff like k8s resources"""
    default_args = conf.get(DagFields.DefaultArgs) or {}

    start_date = default_args.get(DefaultARGsFields.StartDate)
    if not start_date:
      yesterday = datetime.date.today() - datetime.timedelta(days=2)
      start_date = yesterday.strftime("%Y-%m-%d")
    if isinstance(start_date, str):
      start_date = datetime_parser(start_date)
      retries = utils.safe_int(default_args.get("retries", 3)) or 3
      retry_delay_minutes = (
          utils.safe_int(default_args.get("retry_delay_minutes", None)) or 20
      )

      default_args_updated = {
        DefaultARGsFields.StartDate: utils.get_start_date(
          date_value=start_date, timezone=cls.DEFAULT_TZ
        ),
        "on_failure_callback": task_fail_alert,
        "retries": retries,
        "retry_delay": datetime.timedelta(minutes=retry_delay_minutes),
      }

      task_processing = [
        cls._k8s_resource_reservation,
        cls._k8s_volumne_parsed,
        cls._time_delta_parsed,
      ]
      tasks = {
        task_name: functools.reduce(
          lambda res, fn: fn(res), task_processing, task_conf
        )
        for task_name, task_conf in conf[DagFields.Tasks].items()
      }
      updated = {
        DagFields.DefaultArgs: {**default_args, **default_args_updated},
        DagFields.Tasks: tasks,
      }
    return {**conf, **updated}

  def operators_conf(self) -> Dict[str, Any]:
    # return self._operators_conf
    pass
  
  def _resolve_task_ops(self, task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Resolve short hand operator to full module path
    BigQueryOperator -> airflow.contrib.operators.bigquery_operator.BigQueryOperator
    and also apply default_params
    """
    task_conf = task.copy()
    if task_conf[TaskFields.Operator] not in self.operators_conf:
      return task

    # 1. verify user input params first
    operator = self.operators_conf[task_conf.pop(TaskFields.Operator)]
    if operator.params:
      jsonschema.validate(task, operator.params)

    new_conf = {
      TaskFields.Operator: operator.module,
      TaskFields.Dependencies: task_conf.pop(TaskFields.Dependencies, None),
    }
    params = task_conf
    if operator.default_params:
      params = {
        **operator.default_params,
        **task_conf,
        **merge(operator.default_params, task_conf, self.SHOULD_MERGE_FIELDS),
      }
    return {**params, **new_conf}

  @classmethod
  def compile_instance(cls, conf: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve datetime instance, add failure_callback and other stuff like k8s resources"""
    default_args = conf.get(DagFields.DefaultArgs) or {}

    start_date = default_args.get(DefaultARGsFields.StartDate)
    if not start_date:
      yesterday = datetime.date.today() - datetime.timedelta(days=2)
      start_date = yesterday.strftime("%Y-%m-%d")
    if isinstance(start_date, str):
      start_date = datetime_parser(start_date)

    retries = utils.safe_int(default_args.get("retries", 3)) or 3
    retry_delay_minutes = (
        utils.safe_int(default_args.get("retry_delay_minutes", None)) or 20
    )

    default_args_updated = {
      DefaultARGsFields.StartDate: utils.get_start_date(
        date_value=start_date, timezone=cls.DEFAULT_TZ
      ),
      "on_failure_callback": task_fail_alert,
      "retries": retries,
      "retry_delay": datetime.timedelta(minutes=retry_delay_minutes),
    }

    task_processing = [
      cls._k8s_resource_reservation,
      cls._k8s_volumne_parsed,
      cls._time_delta_parsed,
    ]
    tasks = {
      task_name: functools.reduce(
        lambda res, fn: fn(res), task_processing, task_conf
      )
      for task_name, task_conf in conf[DagFields.Tasks].items()
    }
    updated = {
      DagFields.DefaultArgs: {**default_args, **default_args_updated},
      DagFields.Tasks: tasks,
    }
    return {**conf, **updated}

  @classmethod
  def _resolve_task_conns(
      cls,
      task: Dict[str, Any],
      conns: List[any],
  ) -> Dict[str, Dict[str, Any]]:
    if not conns:
      return task
    operator_name = task[TaskFields.Operator]
    opcls: Callable[..., BaseOperator] = import_string(operator_name)
    signature = inspect.signature(opcls.__init__)
    args_overrides = {}
    for conn in conns:
      for replace_field in conn.replace_fields:
        if replace_field in signature.parameters:
          args_overrides[replace_field] = conn.conn_id
    return {**task, **args_overrides}

  @classmethod
  def _resolve_task_files(
      cls,
      task: Dict[str, Any],
      default_args: Dict[str, Any],
  ) -> Dict[str, Any]:
    """Resolve references from file"""
    parent_folder = default_args.get(DefaultARGsFields.ParentFolder)
    file_name = default_args.get(DefaultARGsFields.FileName)
    if not parent_folder or not file_name:
      return task

    ref_path = os.path.join(
      parent_folder, cls.LOOKUP_VAR_DIR, os.path.splitext(file_name)[0]
    )
    task = task.copy()
    for key, value in task.items():
      if not isinstance(value, str) or not value.startswith(cls.REF_VAR_FILE):
        continue
      ref_key = value[len(cls.REF_VAR_FILE):]
      task[key] = utils.read_content(os.path.join(ref_path, ref_key))
    return task

  @classmethod
  def _resolve_task_refs(
      cls, task: Dict[str, Any], refs: Dict[str, str]
  ) -> Dict[str, Any]:
    """Resolve sql references"""
    task = task.copy()
    for key, value in task.items():
      if not isinstance(value, str) or not value.startswith(cls.REF_VAR):
        continue
      ref_key = value[len(cls.REF_VAR):]
      task[key] = refs.get(ref_key)
    return task

  @classmethod
  def _resolve_taskgroups(
      cls,
      task: Dict[str, Any],
      common_resolver: Iterable[Callable[[Dict[str, Any]], Dict[str, Any]]],
  ) -> Dict[str, Any]:
    """Resolve sugdag references. Only single subdag level is allow"""
    if not task[TaskFields.Operator].endswith(OperatorName.TaskGroup):
      return task

    task = task.copy()
    child = {}
    for child_name, child_conf in task[TaskFields.Tasks].items():
      child[child_name] = functools.reduce(
        lambda res, fn: fn(res), common_resolver, child_conf
      )
    task[TaskFields.Tasks] = child
    return task

  @classmethod
  def _resolves_pod_override(cls, task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Set k8s resources"""
    if TaskFields.ExecutorConfig not in task and TaskFields.HighCPUs not in task:
      return task

    # since we already have pod_override, skip build it
    executor_config = task.get(TaskFields.ExecutorConfig, None) or {}
    if ExecutorConfig.PodOverride in executor_config:
      return task

    task = deepcopy(task)
    high_cpu = task.pop(TaskFields.HighCPUs, None) == "yes"
    pod_override_builder = executor_config.pop(
      ExecutorConfig.PodOverrideBuilder, None
    )
    if high_cpu and not pod_override_builder:
      pod_override_builder = {"node_preset": "db_sync"}

    pod_spec = k8s.build_pod_spec(pod_override_builder)
    executor_config[ExecutorConfig.PodOverride] = pod_spec
    task[TaskFields.ExecutorConfig] = executor_config
    return task

  @classmethod
  def _k8s_resource_reservation(
      cls, task: Dict[str, Any]
  ) -> Dict[str, Dict[str, Any]]:
    """Set k8s resources"""
    if TaskFields.ExecutorConfig not in task:
      return task
    task = deepcopy(task)
    executor_config = task.pop(TaskFields.ExecutorConfig, None) or {}
    pod_override = executor_config.pop(ExecutorConfig.PodOverride, None)
    if not pod_override:
      return task

    pod = k8s.build_pod_override(pod_override)
    updated_task = {
      TaskFields.ExecutorConfig: {ExecutorConfig.PodOverride: pod},
    }
    # for k8s pod, set the target resources in destination pod to
    if OperatorName.K8S in task[TaskFields.Operator]:
      updated_task[TaskFields.ExecutorConfig] = {
        ExecutorConfig.PodOverride: k8s.default_pod_override()
      }
      updated_task["affinity"] = pod.spec.affinity
      updated_task["resources"] = k8s.get_base_container(pod).resources
      updated_task["tolerations"] = k8s.TOLERATIONS_SPEC

    out = {**task, **updated_task}
    return out

  @classmethod
  def _k8s_volumne_parsed(cls, task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if OperatorName.K8S not in task[TaskFields.Operator]:
      return task
    # parse secrets
    secret_specs = task.get("secrets", None) or []
    # secret_parsed = [Secret(**args) for args in secret_specs]
    # parse volumn
    volumes = task.get("volumes", None) or []
    # volume_parseds = [Volume(**args) for args in volumes]
    volume_mounts = task.get("volume_mounts", None) or []
    # volume_mount_parseds = [
    #   VolumeMount(sub_path=None, read_only=True, **args) for args in volume_mounts
    # ]
    updated_spec = {
      # "secrets": secret_parsed,
      # "volumes": volume_parseds,
      # "volume_mounts": volume_mount_parseds,
      "is_delete_operator_pod": True,
      "image_pull_policy": "Always",
    }
    return {**task, **updated_spec}

  @classmethod
  def _time_delta_parsed(cls, task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if OperatorName.TimeDeltaSensor not in task[TaskFields.Operator]:
      return task
    updated = {
      "delta": datetime.timedelta(seconds=int(task.get('delta', 1))),
    }
    return {**task, **updated}
