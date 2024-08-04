from airfactory.core.yaml import YamlReader

import unittest

import jsonschema
class TestAirlakeConfig(unittest.TestCase):
    def test_yaml_config():
        path = "./tests/dags/test.yaml"
        yaml_conf = YamlReader()
        content = yaml_conf.read(path)
        print(content)

