import dataclasses
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import dacite
import yaml

from airfactory.common.logger import LoggerMixing
from airfactory.common.utils import NoDatesSafeLoader
from airfactory.compiler.v1 import DagCompilerV1
from airfactory.core.consts import (
  DefaultARGsFields, DagFields, FIELD_DAGS_DEFAULT_ARGS, FIELD_DAGS_SCHEDULE_INTERVAL,
  FIELD_DAGS_NAME, FIELD_DAGS_ROLE_ID, FIELD_DAGS_CONF_PATH
)
from airfactory.dagbuilder import AirlakeDagBuilder


class DagLocation:
  def __init__(self, local_dir: str, sub_path: str):
    self.local_dir = local_dir
    self.sub_path = sub_path

  def absolute_location(self, repo_id: str, team_name: str) -> str:
    return os.path.join(
      self.local_dir,
      repo_id,
      self.sub_path,
      team_name,
    )


class RepoType:
  Python = "python"
  Yaml = "yaml"


class AlertingKind:
  Telegram = "telegram"
  Slack = "slack"


@dataclass
class Alerting:
  kind: str
  conn_id: str

  @staticmethod
  def from_dict(conf):
    return dacite.from_dict(data_class=Alerting, data=conf)


@dataclass
class TeamConnection:
  conn_id: str
  replace_fields: List[str]

  @staticmethod
  def from_list(items: List[Dict[str, Any]]):
    return [dacite.from_dict(data_class=TeamConnection, data=i) for i in items]


@dataclass
class TeamConfig:
  name: str
  prefix: str
  owner: str
  repo_id: Optional[str]
  role_id: Optional[int]
  alert: Optional[Alerting]
  conns: Optional[List[TeamConnection]]
  team_dir: Optional[str]
  pool: Optional[str]
  type: Optional[str] = "yaml"

  def is_yaml(self):
    return not self.type or self.type == RepoType.Yaml

  def is_python(self):
    return self.type == RepoType.Python


class SupportCompiler:
  V1 = "v1"


class AirlakeDagConfig(LoggerMixing):
  def __init__(self, path: str):
    self.path = path
    self.dag_compilers = {
      SupportCompiler.V1: DagCompilerV1(
        path_conf=self.path
      )
    }

  def compile(self, conf: Dict[str, Any], extra: Dict[str, Any] = None) -> Dict[str, Any]:
    apiVerion = (
        conf.get("apiVerion") or conf.get("apiVersion") or SupportCompiler.V1
    )
    return self.dag_compilers[apiVerion].compile(conf)

  def read_content(self):
    with open(self.path, "r") as f:
      conf = yaml.load(f, Loader=NoDatesSafeLoader)

    default_args = conf.get(DagFields.DefaultArg) or {}

    default_args[FIELD_DAGS_CONF_PATH] = str(self.path)
    default_args[DefaultARGsFields.ParentFolder] = os.path.dirname(self.path)
    default_args[DefaultARGsFields.FileName] = os.path.basename(self.path)

    conf[DagFields.DefaultArg] = default_args
    return conf

  def merge_conf(
      self, conf: Dict[str, Any], sub_path: str, default_conf: TeamConfig
  ) -> Dict[str, Any]:

    if default_conf.conns:
      conf[FIELD_DAGS_DEFAULT_ARGS]["conns"] = [
        dataclasses.asdict(i) for i in default_conf.conns
      ]

    if DagFields.Owner not in conf[FIELD_DAGS_DEFAULT_ARGS]:
      conf[FIELD_DAGS_DEFAULT_ARGS][DagFields.Owner] = (
          default_conf.owner or "airflow"
      )

    if default_conf.role_id:
      conf[FIELD_DAGS_DEFAULT_ARGS][FIELD_DAGS_ROLE_ID] = default_conf.role_id

    if not FIELD_DAGS_SCHEDULE_INTERVAL in conf:
      conf[FIELD_DAGS_SCHEDULE_INTERVAL] = None

    if default_conf.pool is not None:
      conf[FIELD_DAGS_DEFAULT_ARGS][DefaultARGsFields.Pool] = default_conf.pool

    # verify schedule_interval
    AirlakeDagBuilder.verify_cron(conf[FIELD_DAGS_SCHEDULE_INTERVAL])

    name_prefix = default_conf.prefix
    base_name = os.path.splitext(sub_path)[0]
    if not base_name.startswith(name_prefix):
      base_name = f"{name_prefix}_{base_name}_{conf[FIELD_DAGS_NAME]}"
    conf[FIELD_DAGS_NAME] = base_name
    return conf
