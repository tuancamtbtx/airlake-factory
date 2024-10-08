"""Module contains exceptions for airlake-factory"""


class DagFactoryException(Exception):
  """
  Base class for all dag-factory errors.
  """


class DagFactoryConfigException(Exception):
  """
  Raise for dag-factory config errors.
  """
