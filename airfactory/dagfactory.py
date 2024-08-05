from typing import Any, Dict, List

from airflow.models import DAG

from airfactory.common.logger import LoggerMixing
from airfactory.dagbuilder import AirlakeDagBuilder
from airfactory.dagconfig import AirlakeDagConfig, TeamConfig


class AirlakeDagFactory(LoggerMixing):

  def __init__(self, config_filepath: str, team_conf: TeamConfig = None) -> None:
    self.config_filepath = config_filepath
    self.team_conf = team_conf

  def cleans_dags(self, globals: Dict[str, Any]) -> None:
    """
    Clean old DAGs that are not on YAML config but were auto-generated through dag-factory

    :param globals: The globals() from the file used to generate DAGs. The dag_id
        must be passed into globals() for Airflow to import
    """
    dags: Dict[str, Any] = self.build_dags()

    # filter dags that exists in globals and is auto-generated by dag-factory
    dags_in_globals: Dict[str, Any] = {}
    for k, glb in globals.items():
      if isinstance(glb, DAG) and hasattr(glb, "is_dagfactory_auto_generated"):
        dags_in_globals[k] = glb

    # finding dags that doesn't exist anymore
    dags_to_remove: List[str] = list(set(dags_in_globals) - set(dags))

    # removing dags from DagBag
    for dag_to_remove in dags_to_remove:
      del globals[dag_to_remove]

  # pylint: disable=redefined-builtin
  @staticmethod
  def register_dags(dags: Dict[str, DAG], globals: Dict[str, Any]) -> None:
    """Adds `dags` to `globals` so Airflow can discover them.

    :param: dags: Dict of DAGs to be registered.
    :param globals: The globals() from the file used to generate DAGs. The dag_id
        must be passed into globals() for Airflow to import
    """
    for dag_id, dag in dags.items():
      globals[dag_id] = dag

  def _load_config(self) -> Dict[str, Any]:
    dag_conf = AirlakeDagConfig(
      path=self.config_filepath
    )
    dag_config = dag_conf.read_content()
    merge_config = dag_conf.merge_conf(
      conf=dag_config,
      sub_path="de",
      default_conf=self.team_conf
    )
    compiled_config = dag_conf.compile(merge_config)
    return compiled_config

  def build_dags(self, ) -> Dict[str, DAG]:
    dags: Dict[str, Any] = {}

    conf: Dict[str, Any] = self._load_config()
    dag_id, dag = AirlakeDagBuilder(
      dag_name=conf["name"],
      dag_config=conf,
    ).build()
    dags[dag_id] = dag
    return dags

  def generate_dags(self, globals: Dict[str, Any]) -> None:
    dags: Dict[str, Any] = self.build_dags()
    self.register_dags(dags, globals)
