from typing import Any, Dict

from airfactory.common.logger import LoggerMixing
from airfactory.compiler.dagcompiler import CommonCompiler, AbstractCompiler

class DagCompilerV1(LoggerMixing,CommonCompiler, AbstractCompiler):
  def __init__(self, path_conf: str):
    self.path_conf = path_conf

  def compile(self,conf: Dict[str, Any], extra: Dict[str, Any] = None):
    self.logger.info("Compile the dag config")
    return conf
