import os
import yaml
from typing import Any, Dict, List, Optional,Tuple
from dataclasses import dataclass
import dataclasses

import dacite

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
  def __init__(self,path: str):
    self.path = path
    self.dag_compilers = {
        SupportCompiler.V1: DagCompilerV1(
            path_conf=self.path
        )
    }

  def compile(self, conf: Dict[str, Any], extra: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    apiVerion = (
      conf.get("apiVerion") or conf.get("apiVersion") or SupportCompiler.V1
    )
    return list(self.dag_compilers[apiVerion].compile(conf, extra))
  
  def _try_gen(self, conf: Dict[str, Any]) -> Tuple[bool, List[str], str]:
    compiled_dags = []
    try:
      compiled_dags = self.compile(conf)
    except Exception as e:
      self.logger.error("Failed to compile the dags", exc_info=True)
      return False, compiled_dags, str(e)


  def read_content(self ):
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
      base_name = "{}_{}".format(name_prefix, base_name)
    conf[FIELD_DAGS_NAME] = base_name
    return conf
