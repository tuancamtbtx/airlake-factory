from airfactory.dagfactory import AirlakeDagFactory


import unittest

import jsonschema


class TestAirlakeFactory(unittest.TestCase):
    def test_schema_validate(self):
        from jsonschema.exceptions import ValidationError
        s = {
            "type": "object",
            "properties": {"sql": {"type": "string", "minLength": 2}},
            "required": ["sql"],
        }
        data = {"sql": "SELECT 2"}
        jsonschema.validate(data, s)

        with self.assertRaises(ValidationError) as ctx:
            jsonschema.validate({"sql": None}, s)
    def test_dag_factory(self):
        config_filepath = "./conf/example_dag_factory.yaml"
        factory = AirlakeDagFactory(config_filepath=config_filepath)
        factory.cleans_dags()
        factory.generate_dags(globals())
        self.assertTrue(True)