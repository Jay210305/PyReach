"""Exception hierarchy for PyReach.

All PyReach errors derive from :class:`PyReachError` so callers can catch a
single base type.
"""


class PyReachError(Exception):
    """Base class for all PyReach errors."""


class ConfigError(PyReachError):
    """Raised on invalid configuration or a missing manifest."""


class ParseError(PyReachError):
    """Raised when a manifest or source file cannot be parsed."""


class OSVError(PyReachError):
    """Raised when the OSV database is missing or corrupt."""


class AnalysisError(PyReachError):
    """Raised on AST or call graph analysis failure (reserved for later sprints)."""


class OutputError(PyReachError):
    """Raised on SARIF serialization or report write failure (reserved for later sprints)."""