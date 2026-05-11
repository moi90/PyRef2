"""Repository adapters for loading revision snapshots."""

from pyref2.repository.git_history import (
	aggregate_revision,
	aggregate_working_tree,
	parse_revision_range,
	resolve_single_revision,
)

__all__ = [
	"aggregate_revision",
	"aggregate_working_tree",
	"parse_revision_range",
	"resolve_single_revision",
]