from __future__ import annotations

from pathlib import Path

from git import Actor, Repo

from pyref2.service import analyze_revision_range, analyze_revisions


def test_detect_move_method_between_git_revisions(tmp_path: Path) -> None:
    repo_path = _build_move_method_repository(tmp_path)

    findings = analyze_revisions(str(repo_path), "HEAD~1", "HEAD")

    assert any(f.refactoring_type == "Move Method" for f in findings)
    assert any(
        finding.details.get("Old Module") == "pkg/alpha.py"
        and finding.details.get("New Module") == "pkg/beta.py"
        for finding in findings
        if finding.refactoring_type == "Move Method"
    )


def test_detect_move_method_from_revision_range(tmp_path: Path) -> None:
    repo_path = _build_move_method_repository(tmp_path)

    repo = Repo(repo_path)
    repo.git.update_ref("refs/remotes/origin/main", "HEAD~1")

    findings = analyze_revision_range(str(repo_path), "origin/main..HEAD")

    assert any(f.refactoring_type == "Move Method" for f in findings)


def test_detect_move_method_from_single_revision(tmp_path: Path) -> None:
    repo_path = _build_move_method_repository(tmp_path)

    findings = analyze_revision_range(str(repo_path), "HEAD")

    assert any(f.refactoring_type == "Move Method" for f in findings)


def test_detect_move_method_from_working_tree_changes(tmp_path: Path) -> None:
    repo_path = _build_repository_with_working_tree_move(tmp_path)

    findings = analyze_revision_range(str(repo_path), None)

    assert any(f.refactoring_type == "Move Method" for f in findings)


def _build_move_method_repository(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    repo = Repo.init(repo_path)
    actor = Actor("PyRef2 Tests", "tests@example.com")

    _write_file(
        repo_path / "pkg" / "alpha.py",
        (
            "def moved_helper(value):\n"
            "    result = value + 1\n"
            "    return result * 2\n\n\n"
            "def process(value):\n"
            "    return moved_helper(value)\n"
        ),
    )
    repo.index.add(["pkg/alpha.py"])
    repo.index.commit(
        "initial",
        author=actor,
        committer=actor,
        author_date="2026-05-09T10:00:00",
        commit_date="2026-05-09T10:00:00",
    )

    _write_file(
        repo_path / "pkg" / "alpha.py",
        (
            "from pkg.beta import moved_helper\n\n\n"
            "def process(value):\n"
            "    return moved_helper(value)\n"
        ),
    )
    _write_file(
        repo_path / "pkg" / "beta.py",
        (
            "def moved_helper(value):\n"
            "    result = value + 1\n"
            "    return result * 2\n"
        ),
    )
    repo.index.add(["pkg/alpha.py", "pkg/beta.py"])
    repo.index.commit(
        "move helper",
        author=actor,
        committer=actor,
        author_date="2026-05-09T11:00:00",
        commit_date="2026-05-09T11:00:00",
    )

    return repo_path


def _build_repository_with_working_tree_move(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    repo = Repo.init(repo_path)
    actor = Actor("PyRef2 Tests", "tests@example.com")

    _write_file(
        repo_path / "pkg" / "alpha.py",
        (
            "def moved_helper(value):\n"
            "    result = value + 1\n"
            "    return result * 2\n\n\n"
            "def process(value):\n"
            "    return moved_helper(value)\n"
        ),
    )
    repo.index.add(["pkg/alpha.py"])
    repo.index.commit(
        "initial",
        author=actor,
        committer=actor,
        author_date="2026-05-09T10:00:00",
        commit_date="2026-05-09T10:00:00",
    )

    _write_file(
        repo_path / "pkg" / "alpha.py",
        (
            "from pkg.beta import moved_helper\n\n\n"
            "def process(value):\n"
            "    return moved_helper(value)\n"
        ),
    )
    _write_file(
        repo_path / "pkg" / "beta.py",
        (
            "def moved_helper(value):\n"
            "    result = value + 1\n"
            "    return result * 2\n"
        ),
    )

    return repo_path


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")