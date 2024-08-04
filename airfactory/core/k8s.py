import dataclasses
from typing import Any, Dict, List, Optional
import os

import dacite
import yaml
from kubernetes.client import ApiClient, models as k8s
from kubernetes.client.models import V1Pod

from airfactory import resolve_root


class ImageTagType:
  Fixed = "fixed"
  Variable = "variable"


@dataclasses.dataclass
class ImageTag:
  type: str
  value: str

  @property
  def tag(self):
    if self.type == ImageTagType.Fixed:
      return self.value

    if self.type == ImageTagType.Variable:
      from airflow.models import Variable

      return Variable.get(self.value)
    raise Exception("Not support image tag type")


@dataclasses.dataclass
class PodOverrideBuilder:
  image_name: Optional[str] = None
  image_tag: Optional[ImageTag] = None
  image_pull_policy: Optional[str] = None
  node_preset: Optional[str] = None

  @staticmethod
  def from_dict(conf) -> "PodOverrideBuilder":
    return dacite.from_dict(data_class=PodOverrideBuilder, data=conf)


@dataclasses.dataclass
class NodePreset:
  resources: Optional[dict] = None
  affinity: Optional[dict] = None

  @property
  def k8s_resources(self) -> k8s.V1ResourceRequirements:
    return _convert_from_dict(self.resources, k8s.V1ResourceRequirements)


# keep the default in the code base to make sure
# if any bad things happend, we always have resource constrain
NODE_PRESET_DEFAULT = NodePreset(
  resources={
    "requests": {"cpu": "200m", "memory": "200Mi"},
    "limits": {"cpu": "1", "memory": "1000Mi"},
  },
  affinity={
    "nodeAffinity": {
      "requiredDuringSchedulingIgnoredDuringExecution": {
        "nodeSelectorTerms": [
          {
            "matchExpressions": [
              {
                "key": "ts.dedicated",
                "operator": "In",
                "values": ["preempt-8-32"],
              }
            ]
          }
        ]
      }
    }
  },
)


def _convert_from_dict(obj, new_class):
  api_client = ApiClient()
  return api_client._ApiClient__deserialize_model(obj, new_class)


def _build_node_presets() -> Dict[str, NodePreset]:
  """
  read preset k8s_provisonings
  """
  path = os.environ.get("NODE_PRESETS_PATH") or resolve_root(
    "conf", "k8s_provisonings.yaml"
  )
  with open(path, "r") as f:
    conf = yaml.safe_load(f)

  out = {}
  for name, item in conf["node_presets"].items():
    spec = NodePreset(affinity=item["affinity"], resources=item["resources"])
    out[name] = spec
  return out


CUSTOM_NODE_PRESETS = _build_node_presets()

TOLERATIONS = [
  {
    "effect": "NoSchedule",
    "key": "dedicated",
    "operator": "Equal",
    "value": "preempt-8-32",
  },
  {
    "effect": "NoSchedule",
    "key": "dedicated",
    "operator": "Equal",
    "value": "preempt-highmem",
  },
]

# only use for KubernetesPodOperator
TOLERATIONS_SPEC = [_convert_from_dict(obj, k8s.V1Toleration) for obj in TOLERATIONS]


def build_pod_spec(cfg_raw) -> Optional[dict]:
  """
  Take config from executor_config.pod_override_builder
  Examples
  """
  SPEC_FIELDS = "spec"
  cfg_raw = cfg_raw or {}
  pod = {
    k: v for k, v in cfg_raw.items() if k not in PodOverrideBuilder.__annotations__
  }
  pod_spec = pod.get(SPEC_FIELDS) or {}
  sidecars: List[dict] = list(
    filter(lambda c: c["name"] != "base", pod_spec.get("containers") or [])
  )
  bases: List[dict] = list(
    filter(lambda c: c["name"] == "base", pod_spec.get("containers") or [])
  )
  base_container: Dict[str, Any] = bases[0] if len(bases) > 0 else {"name": "base"}

  cfg = PodOverrideBuilder.from_dict(cfg_raw)
  if cfg.image_name:
    if cfg.image_tag is None:
      raise Exception("require image tag")
    base_container["image"] = f"{cfg.image_name}:{cfg.image_tag.tag}"

    if cfg.image_pull_policy:
      base_container["imagePullPolicy"] = cfg.image_pull_policy
  node = (
    CUSTOM_NODE_PRESETS[cfg.node_preset] if cfg.node_preset else NODE_PRESET_DEFAULT
  )
  if node.affinity is not None:
    pod_spec["affinity"] = node.affinity
  if node.resources is not None:
    base_container["resources"] = node.resources
  pod_spec["containers"] = sidecars + [base_container]
  pod[SPEC_FIELDS] = pod_spec
  return pod


def build_pod_override(cfg_raw) -> V1Pod:
  """
  Take a dict of raw config from the field `pod_override_builder`
  Build the resources constrain as well as pod info
  """
  default_pod = default_pod_override()
  if not cfg_raw:
    return default_pod

  pod_spec = {
    k: v for k, v in cfg_raw.items() if k not in PodOverrideBuilder.__annotations__
  }
  pod = _convert_from_dict(pod_spec, V1Pod)
  return pod


def default_pod_override() -> V1Pod:
  DEFAULT_PRESET = "default"
  node = CUSTOM_NODE_PRESETS.get(DEFAULT_PRESET) or NODE_PRESET_DEFAULT
  pod = V1Pod()
  pod.spec = k8s.V1PodSpec(containers=[])
  pod.spec.affinity = node.affinity
  container = k8s.V1Container(name="base")
  container.resources = node.resources
  pod.spec.containers = [container]
  return pod


def get_base_container(pod: V1Pod) -> k8s.V1Container:
  c = list(filter(lambda c: c.name == "base", pod.spec.containers))
  return c[0] if len(c) > 0 else None


def get_sidecars_container(pod: V1Pod) -> List[k8s.V1Container]:
  return list(filter(lambda c: c.name != "base", pod.spec.containers))
