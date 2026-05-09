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
        and f.details.get("Functional Change Status") == "No Functional Change"
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
        and f.details.get("Functional Change Status") == "No Functional Change"
        for f in findings
        if f.refactoring_type == "Move Class"
    )
    assert any(
        isinstance(f.details.get("Method Changes"), list)
        for f in findings
        if f.refactoring_type == "Move Class"
    )
    assert not any(
        f.refactoring_type == "Move Method" and f.original.endswith("Customer.label")
        for f in findings
    )


def test_class_move_suppresses_child_rename_but_keeps_functional_check() -> None:
    findings = analyze_trees(
        _fixture_root("class_move_with_method_rename", "revision-A"),
        _fixture_root("class_move_with_method_rename", "revision-B"),
    )

    assert not any(f.refactoring_type == "Rename Method" for f in findings)

    move_class_findings = [f for f in findings if f.refactoring_type == "Move Class"]
    assert move_class_findings

    method_changes = move_class_findings[0].details.get("Method Changes")
    assert isinstance(method_changes, list)
    assert any(
        isinstance(change, dict)
        and change.get("Kind") == "Rename Method"
        and change.get("Original") == "label"
        and change.get("Updated") == "title"
        and change.get("Functional Change Status") == "No Functional Change"
        for change in method_changes
    )
