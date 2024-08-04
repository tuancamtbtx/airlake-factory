from airfactory.dagbuilder import AirlakeDagBuilder
from airfactory.compiler.dagcompiler import CommonCompiler
from airfactory.dagconfig import AirlakeDagConfig

dag_conf = AirlakeDagConfig(
    path="./tests/dags/test.yaml"
)
dag_config = dag_conf.read_content()
print(dag_config)
dag = AirlakeDagBuilder(
    dag_name="test_dag",
    dag_config={
        "name": "test_dag",
        "schedule": "0 0 * * *",
        "default_args": {
            "owner": "airflow",
            "depends_on_past": False,
            "start_date": "2024-08-01",
            "email_on_failure": False,
            "email_on_retry": False,
            "retries": 1,
        },
        "tasks": {
            "task_1": {
                "operator": "airflow.operators.bash.BashOperator",
                "bash_command": "echo ",
            },
            "task_2": {
                "operator": "airflow.operators.bash.BashOperator",
                "bash_command": "echo 1",   
                "dependencies": ["task_1"]
            },
        }
    },
).build()
print(dag)