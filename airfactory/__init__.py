import os

_ROOT = os.path.dirname(os.path.dirname(__file__))


def resolve_root(*arg: str):
  return os.path.join(_ROOT, *arg)

## This is needed to allow Airflow to pick up specific metadata fields it needs for certain features.

__version__ = "v1.0.0"

def get_provider_info():
    return {
        "package-name": "airfactory", # Required
        "name": "airfactory", # Required
        "description": "Dag Factory for Apache Airflow.", # Required
        "versions": [__version__] # Required
    }