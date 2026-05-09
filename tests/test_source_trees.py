from __future__ import annotations

from pathlib import Path

from pyref2.service import analyze_trees

FIXTURES_ROOT = Path(__file__).parent / "source_trees"


def _fixture_root(name: str, revision: str) -> str:
    return str(FIXTURES_ROOT / name / revision)


def test_detect_move_method_across_modules() -> None:
    findings = analyze_trees(
        _fixture_root("move_method_across_modules", "revision-A"),
        _fixture_root("move_method_across_modules", "revision-B"),
    )

    assert any(f.refactoring_type == "Move Method" for f in findings)
    assert any(
        f.details.get("Old Module") == "pkg/alpha.py"
        and f.details.get("New Module") == "pkg/beta.py"
        for f in findings
        if f.refactoring_type == "Move Method"
    )


def test_detect_move_class_across_modules() -> None:
    findings = analyze_trees(
        _fixture_root("move_class_across_modules", "revision-A"),
        _fixture_root("move_class_across_modules", "revision-B"),
    )

    assert any(f.refactoring_type == "Move Class" for f in findings)
    assert any(
        f.details.get("Old Module") == "pkg/models.py"
        and f.details.get("New Module") == "pkg/domain.py"
        for f in findings
        if f.refactoring_type == "Move Class"
    )
    assert not any(
        f.refactoring_type == "Move Method" and f.original.endswith("Customer.label")
        for f in findings
    )
