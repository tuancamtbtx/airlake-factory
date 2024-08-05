import datetime
import functools
from typing import Any, Dict

from dateutil.parser import parse as datetime_parser

from airfactory.common import utils
from airfactory.common.logger import LoggerMixing
from airfactory.compiler.dagcompiler import CommonCompiler, AbstractCompiler
from airfactory.core.alert import task_fail_alert
from airfactory.core.consts import (
  DefaultARGsFields,
  DagFields,
)


class DagCompilerV1(LoggerMixing, CommonCompiler, AbstractCompiler):
  def __init__(self, path_conf: str):
    self.path_conf = path_conf

  def compile(cls, conf: Dict[str, Any]) -> Dict[str, Any]:
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
