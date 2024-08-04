from typing import Any, Dict
import copy
import functools
from collections import OrderedDict


from airfactory.common.logger import LoggerMixing
from airfactory.compiler.dagcompiler import CommonCompiler, AbstractCompiler
from airfactory.core.consts import DagFields

class DagCompilerV1(LoggerMixing,CommonCompiler, AbstractCompiler):
  def __init__(self, path_conf: str):
    self.path_conf = path_conf

  def compile(self,conf: Dict[str, Any], extra_options: Dict[str, Any] = None):
    self.logger.info("Compile the dag config")
    conf = copy.deepcopy(conf)
    extra_options = extra_options or {}
    default_args = conf.pop(DagFields.DefaultArg, None) or {}
     # merge final conf
    conf = {**extra_options, **conf}

    refs: Dict[str, str] = conf.get(DagFields.Refs) or {}

    common_task_processing = []
    # common_task_processing.append(
    #         lambda task: self._resolve_task_refs(task, refs))
    # common_task_processing.append(
    #         lambda task: self._resolve_task_files(task, default_args)
    # )
    # common_task_processing.append(self._resolve_task_ops)
    # common_task_processing.append(self._resolves_pod_override)
    # common_task_processing.append(self._time_delta_parsed)

 

    task_processing = common_task_processing.copy()
    task_processing.append(
            lambda task: self._resolve_taskgroups(task, common_task_processing)
    )

    shared_tasks: Dict[str, Any] = {
            task_name: functools.reduce(
                lambda res, fn: fn(res), task_processing, task_conf
            )
            for task_name, task_conf in conf.get(DagFields.SharedTasks, {}).items()
        }
    shared_tags = conf.pop(DagFields.Tags, None) or []
    base_name = conf[DagFields.Name]

    for dag_name, dag_conf in conf[DagFields.Dags].items():
        dag_tasks = {}
        for task_name, task_conf in dag_conf[DagFields.Tasks].items():
                # get reference from shared_tasks
            if "value_from" in task_conf:
                    match_task = shared_tasks[
                        task_conf.pop("value_from")["shared_task"]
                    ]
                    # allow override some fields after refer
                    task_conf = {**match_task, **task_conf}

                # final resolver
            resolved_task_conf = functools.reduce(
                    lambda res, fn: fn(res), task_processing, task_conf
                )
            dag_tasks[task_name] = resolved_task_conf

            dag_default_args = {
                **default_args,
                **dag_conf.get(DagFields.DefaultArgs, {}),
            }
            tags = dag_conf.pop(DagFields.Tags, None) or []
            override_conf = {
                DagFields.Name: "{}_{}".format(base_name, dag_name),
                DagFields.Tasks: dag_tasks,
                DagFields.DefaultArgs: dag_default_args,
                DagFields.Tags: list(OrderedDict.fromkeys(tags + shared_tags)),
            }
            yield {**dag_conf, **override_conf}
