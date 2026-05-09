"""Repository adapters for loading revision snapshots."""

from pyref2.repository.git_history import aggregate_revision, parse_revision_range

__all__ = ["aggregate_revision", "parse_revision_range"]