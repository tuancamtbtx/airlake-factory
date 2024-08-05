from airfactory.dagbuilder import AirlakeDagBuilder
from airfactory.dagconfig import AirlakeDagConfig,TeamConfig


team_conf = TeamConfig(
	name="bigdata",
	pool="bigdata",
	prefix="bigdata",
	owner="bigdata",
	team_dir="bigdata",
	repo_id="bigdata",
	role_id=1,
	alert=None,
	conns=None,
	type="yaml"
)
dag_conf = AirlakeDagConfig(
    path="./tests/dags/test.yaml"
)
dag_config = dag_conf.read_content()
merge_config = dag_conf.merge_conf(
	conf=dag_config,
	sub_path="de",
	default_conf=team_conf
)
compile_config =dag_conf.compile(merge_config)
print(compile_config)

dag = AirlakeDagBuilder(
    dag_name=compile_config["name"],
    dag_config=compile_config,
).build()
print(dag)