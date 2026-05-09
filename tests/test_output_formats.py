from __future__ import annotations

from pyref2.models.refactorings import RefactoringFinding
from pyref2.service import findings_to_markdown, serialize_findings


def test_markdown_output_contains_grouped_report() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Move Method",
            original="pkg.alpha.moved_helper",
            updated="pkg.beta.moved_helper",
            location="pkg/alpha.py",
            confidence=0.97,
            details={
                "Old Module": "pkg/alpha.py",
                "New Module": "pkg/beta.py",
                "Old Scope": None,
                "New Scope": None,
                "Functional Change Status": "Functional Change Detected",
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "# PyRef2 Refactoring Report" in output
    assert "## Module-Level Function Moves/Renames" in output
    assert "`pkg/`{`alpha.py` → `beta.py`}:`moved_helper` [Functional Change Detected]" in output


def test_serialize_findings_switches_between_json_and_markdown() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Rename Method",
            original="pkg.alpha.old_name",
            updated="pkg.alpha.new_name",
            location="pkg/alpha.py",
            confidence=0.9,
        )
    ]

    json_output = serialize_findings(findings, output_format="json")
    markdown_output = serialize_findings(findings, output_format="markdown")

    assert '"schema_version": "0.1.0"' in json_output
    assert "# PyRef2 Refactoring Report" in markdown_output


def test_markdown_output_compacts_references_with_nested_common_prefix() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Move Class",
            original="foo/bar/pkg/alpha.py.Customer",
            updated="foo/bar/pkg/beta.py.Customer",
            location="foo/bar/pkg/beta.py",
            confidence=1.0,
            details={
                "Functional Change Status": "Functional Change Detected",
                "Method Changes": [
                    {
                        "Kind": "Rename Method",
                        "Original": "transform_item",
                        "Updated": "transform_item_new",
                        "Functional Change Status": "No Functional Change",
                    }
                ],
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "## Class-Wise Changes" in output
    assert (
        "`foo/bar/pkg/`{`alpha.py` → `beta.py`}:`Customer` "
        "[Functional Change Detected]"
    ) in output
    assert "`transform_item → transform_item_new` [Rename Method; No Functional Change]" in output


def test_markdown_suppresses_same_name_method_without_functional_change() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Move Method",
            original="pkg.alpha.same_name",
            updated="pkg.beta.same_name",
            location="pkg/beta.py",
            confidence=0.97,
            details={
                "Old Module": "pkg/alpha.py",
                "New Module": "pkg/beta.py",
                "Old Scope": None,
                "New Scope": None,
                "Functional Change Status": "No Functional Change",
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "## Module-Level Function Moves/Renames" in output
    assert "- None" in output
    assert "same_name" not in output


def test_markdown_output_avoids_asymmetric_prefix_compaction() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Move Method",
            original=(
                "foo/bar/alpha.py."
                "Customer._legacy_helper"
            ),
            updated=(
                "foo/bar/baz/"
                "beta.py.helper"
            ),
            location="foo/bar/baz/beta.py",
            confidence=1.0,
            details={
                "Old Module": "foo/bar/alpha.py",
                "New Module": "foo/bar/baz/beta.py",
                "Old Scope": "Customer",
                "New Scope": None,
                "Functional Change Status": "Functional Change Detected",
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "## Mixed Scope Method Changes" in output
    assert (
        "`foo/bar/`{`alpha.py`:`Customer._legacy_helper` → "
        "`baz/beta.py`:`helper`} [Functional Change Detected]"
    ) in output


def test_markdown_output_without_common_prefix_has_no_braces() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Move Method",
            original="pkg.alpha.old_name",
            updated="core.beta.new_name",
            location="core/beta.py",
            confidence=0.8,
            details={
                "Old Module": "pkg/alpha.py",
                "New Module": "core/beta.py",
                "Old Scope": None,
                "New Scope": None,
                "Functional Change Status": "Functional Change Detected",
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert (
        "`pkg/alpha.py`:`old_name` → `core/beta.py`:`new_name` "
        "[Functional Change Detected]"
    ) in output


def test_markdown_reports_non_move_functional_changes() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Modify Method",
            original="pkg.alpha.compute",
            updated="pkg.alpha.compute",
            location="pkg/alpha.py",
            confidence=0.72,
            details={
                "Functional Change Status": "Functional Change Detected",
                "Functional Change Reasons": ["method body changed"],
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "## Other Refactorings" in output
    assert "### Modify Method" in output
    assert "`pkg/alpha.py`:`compute` [Functional Change Detected]" in output
