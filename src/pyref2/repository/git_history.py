"""Git-backed loaders for analyzing repository revisions without checkout."""

from __future__ import annotations

from pathlib import Path

from git import BadName, Repo
from git.objects.blob import Blob

from pyref2.core.ast_analysis import parse_module
from pyref2.exceptions import RepositoryError
from pyref2.models.code_elements import ModuleEntity


def parse_revision_range(revision_range: str) -> tuple[str, str]:
    """Split a Git revision range of the form `A..B` into both endpoints."""
    if ".." not in revision_range:
        raise RepositoryError(
            "Revision range must use the 'A..B' form, for example 'origin/main..HEAD'."
        )

    before_revision, after_revision = revision_range.split("..", maxsplit=1)
    if not before_revision or not after_revision:
        raise RepositoryError(
            "Revision range must include both a start and end revision, for example 'main..HEAD'."
        )
    return before_revision, after_revision


def aggregate_revision(repo_path: str, revision: str, label: str) -> ModuleEntity:
    """Load all Python modules from one Git revision into a logical revision view."""
    repo = Repo(repo_path)
    try:
        commit = repo.commit(revision)
    except (BadName, ValueError) as exc:
        raise RepositoryError(f"Unable to resolve revision '{revision}'.") from exc

    modules = []
    for item in commit.tree.traverse():
        if not isinstance(item, Blob):
            continue
        blob_path = str(item.path)
        if not blob_path.endswith(".py"):
            continue

        source = item.data_stream.read().decode("utf-8")
        modules.append(parse_module(source, module_name=blob_path))

    methods = tuple(method for module in modules for method in module.methods)
    classes = tuple(class_entity for module in modules for class_entity in module.classes)
    return ModuleEntity(name=label, methods=methods, classes=classes)


def resolve_single_revision(repo_path: str, revision: str) -> tuple[str | None, str]:
    """Resolve one revision into the pair needed to report that commit's changes."""
    repo = Repo(repo_path)
    try:
        commit = repo.commit(revision)
    except (BadName, ValueError) as exc:
        raise RepositoryError(f"Unable to resolve revision '{revision}'.") from exc

    if not commit.parents:
        return None, commit.hexsha

    return commit.parents[0].hexsha, commit.hexsha


def aggregate_working_tree(repo_path: str, label: str) -> ModuleEntity:
    """Load Python modules from the current working tree (tracked + untracked)."""
    repo = Repo(repo_path)
    if repo.working_tree_dir is None:
        raise RepositoryError("Repository has no working tree.")

    working_tree_root = Path(repo.working_tree_dir)
    tracked_files = {
        path for path in repo.git.ls_files("*.py").splitlines() if path.strip()
    }
    untracked_files = {
        path
        for path in repo.git.ls_files("--others", "--exclude-standard", "*.py").splitlines()
        if path.strip()
    }

    modules = []
    for relative_path in sorted(tracked_files | untracked_files):
        file_path = working_tree_root / relative_path
        if not file_path.is_file():
            continue

        source = file_path.read_text(encoding="utf-8")
        modules.append(parse_module(source, module_name=relative_path))

    methods = tuple(method for module in modules for method in module.methods)
    classes = tuple(class_entity for module in modules for class_entity in module.classes)
    return ModuleEntity(name=label, methods=methods, classes=classes)