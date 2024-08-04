from airfactory.dagbuilder import AirlakeDagBuilder


dag = AirlakeDagBuilder(
    dag_name="test_dag",
    dag_config={
        "apiVersion": "airfactory/v1.0.0",
        "schedule_interval": "0 0 * * *",
        "timetable": {
            "start_date": "2024-08-01",
            "end_date": "2024-08-02",
        },
        "default_args": {
            "owner": "nguyenvantuan140397@gmail.com",
            "depends_on_past": False,
            "email_on_failure": False,
            "email_on_retry": False,
            "retries": 1,
            "default_view": "tree",
            "tags": ["example"],
        },
        "tasks": {
            "task1": {
                "operator": "airflow.operators.bash.BashOperator",
                "bash_command": "echo 1",
                "execution_timeout": 60,
                "sla": 30,
            },
            "task2": {
                "operator": "airflow.operators.bash.BashOperator",
                "bash_command": "echo 2",
                "execution_timeout": 60,
                "sla": 30,
                "dependencies": ["task1"],
            },
        }
    },
).build()
print(dag)