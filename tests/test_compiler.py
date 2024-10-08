from airfactory.dagbuilder import AirlakeDagBuilder
from airfactory.compiler.dagcompiler import CommonCompiler


dag = AirlakeDagBuilder(
    dag_name="test_dag",
    dag_config={
    "default_args": {
      "owner": "nguyenvantuan140397@gmail.com",
      "start_date": "2024-06-28",
      "conf_path": "tests/dags/test.yaml",
      "parent_folder": "tests/dags",
      "file_name": "test.yaml"
    },
    "schedule": "0 2 * * *",
    "tasks": {
      "score_products": {
        "operator": "BigQueryOperator",
        "sql": "SELECT * FROM `dwh.product.vw_product_fraud_score`",
        "destination_dataset_table": "dwh.product.product_scoring_{{ macros.localtz.ds_nodash(ti) }}"
      },
      "update_realtime_cached": {
        "operator": "BigqueryToSheetOperator",
        "sheet_url": "product.product_scores",
        "sql": "SELECT CAST(sku AS STRING) sku, product_fraud_score_new score\nFROM `dwh.product.vw_product_fraud_score_update`\nWHERE sku IS NOT NULL\n",
        "dependencies": ["score_products"]
      }
    }
  },
).build()
print(dag)