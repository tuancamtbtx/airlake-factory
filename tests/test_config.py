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
config = dag_conf.read_content()
merge_config = dag_conf.merge_conf(
	conf=config,
	sub_path="de",
	default_conf=team_conf
)
compile_config = dag_conf.compile(conf=merge_config)
print(compile_config)
