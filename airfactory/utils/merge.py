from typing import Dict, Any, List

from deepmerge import always_merger


def _extract(obj: Dict[str, Any], mask: List[str]) -> Dict[str, Any]:
  return {k: obj[k] for k in mask if k in obj}


def merge(base: Dict[str, Any], by: Dict[str, Any], mask: List[str]) -> Dict[str, Any]:
  return always_merger.merge(_extract(base, mask), _extract(by, mask))
