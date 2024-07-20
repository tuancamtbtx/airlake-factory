'''
Generated by Airflow Datalake! Do not edit!
author: tuancamtbtx
Timestamp 2024-07-19T16:33:52.556796+07:00
'''

from airflow import DAG

from airfactory.render import load_dag

conf = {'schedule_interval': '0 0 * * *', 'timetable': {'start_date': '2021-01-01', 'end_date': '2021-01-02'}, 'default_args': {'owner': 'airflow', 'depends_on_past': False, 'email_on_failure': False, 'email_on_retry': False, 'retries': 1}, 'tasks': {'task1': {'operator': 'airflow.operators.bash.BashOperator', 'bash_command': 'echo 1', 'execution_timeout': 60, 'sla': 30}, 'task2': {'operator': 'airflow.operators.bash.BashOperator', 'bash_command': 'echo 2', 'execution_timeout': 60, 'sla': 30}}}
name = 'test_dag'
load_dag(globals(), name, conf)