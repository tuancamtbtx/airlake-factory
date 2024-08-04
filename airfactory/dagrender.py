"""
Render the config into the read to run dag
"""
from datetime import datetime
from typing import Dict, Any

import jinja2

from airfactory.common.logger import LoggerMixing
from airfactory.core.consts import DefaultARGsFields, DagFields, OperatorName
from airfactory.compiler.dagcompiler import CommonCompiler
from airfactory.dagbuilder import AirlakeDagBuilder

logger_factory = LoggerMixing()
logger_factory.logger.info("Render the config into the read to run dag")

DAG_TEMPLATE = jinja2.Template(
  """
'''
Generated by Airflow Datalake! Do not edit!
author: tuancamtbtx
Timestamp {{ timestamp }}
'''

from airflow import DAG

from airfactory.dagfactory import AirlakeDagFactory

config_filepath = {{yaml_conf}}

conf = {{ json_conf }}
name = '{{ name }}'
render(globals(), name, conf)
"""
)


class RenderToDagFile(LoggerMixing):
  def __init__(self, dag_repo, dag_config):
    self.dag_repo = dag_repo
    self.dag_config = dag_config

  def _get_yaml_path_config(self):
    return self.dag_repo + "/" + self.dag_config["name"] + ".py"

  @staticmethod
  def dump_to_py(yaml_conf: str = None):
    """Dumps configs from dict into python dag file"""
    return DAG_TEMPLATE.render(
      yaml_conf=yaml_conf,
      timestamp=datetime.now().astimezone().isoformat(),
    )

  def dump_to_py(name: str, conf: Dict[str, Any]):
    """Dumps configs from dict into python dag file"""
    conf[DagFields.DefaultArgs].pop("conns", None)
    conf[DagFields.DefaultArgs].pop("conf_path", None)
    conf[DagFields.DefaultArgs].pop("role_id", None)
    conf[DagFields.DefaultArgs].pop(DefaultARGsFields.ParentFolder, None)
    conf[DagFields.DefaultArgs].pop(DefaultARGsFields.FileName, None)
    conf.pop("refs", None)
    return DAG_TEMPLATE.render(
      name=name,
      json_conf=conf,
      timestamp=datetime.now().astimezone().isoformat(),
    )

  def render(g: Dict[str, Any], name: str, conf: Dict[str, Any]):
    """Given name of dag, render it into airflow dags"""
    conf = CommonCompiler.compile_instance(conf)
    dag_id, dag = AirlakeDagBuilder(name, conf).build()
    g[dag_id] = dag
