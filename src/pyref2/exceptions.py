"""Project-specific exception types."""


class PyRefError(Exception):
    """Base class for all PyRef2 errors."""


class ParseError(PyRefError):
    """Raised when source code cannot be parsed into an AST."""


class DetectionError(PyRefError):
    """Raised when refactoring detection fails."""


class RepositoryError(PyRefError):
    """Raised when repository-based analysis cannot load revisions."""
