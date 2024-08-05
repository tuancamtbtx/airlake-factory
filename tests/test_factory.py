from airfactory.dagfactory import AirlakeDagFactory
from airfactory.dagconfig import TeamConfig

config_filepath = "./tests/dags/test.yaml"
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
factory= AirlakeDagFactory(config_filepath=config_filepath, team_conf=team_conf)
print(factory._load_config())
# factory.cleans_dags(globals())
# factory.generate_dags(globals())