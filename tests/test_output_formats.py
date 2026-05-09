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
            details={"Old Module": "pkg/alpha.py", "New Module": "pkg/beta.py"},
        )
    ]

    output = findings_to_markdown(findings)

    assert "# PyRef2 Refactoring Report" in output
    assert "## Move Method (1)" in output
    assert "| Change | Confidence |" in output
    assert "`pkg/`{`alpha.py:moved_helper` → `beta.py:moved_helper`}" in output


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
            refactoring_type="Move Method",
            original="foo/bar/pkg/alpha.py.transform_item",
            updated="foo/bar/pkg/beta.py.transform_item",
            location="foo/bar/pkg/beta.py",
            confidence=1.0,
        )
    ]

    output = findings_to_markdown(findings)

    assert (
        "`foo/bar/pkg/`"
        "{`alpha.py:transform_item` → "
        "`beta.py:transform_item`}"
    ) in output


def test_markdown_output_avoids_asymmetric_prefix_compaction() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Move Method",
            original=(
                "foo/bar/"
                "alpha.py._legacy_helper"
            ),
            updated=(
                "foo/bar/baz/"
                "beta.py.helper"
            ),
            location="foo/bar/baz/beta.py",
            confidence=1.0,
        )
    ]

    output = findings_to_markdown(findings)

    assert (
        "`foo/bar/`{`alpha.py:"
        "_legacy_helper` → "
        "`baz/beta.py:"
        "helper`}"
    ) in output


def test_markdown_output_without_common_prefix_has_no_braces() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Move Method",
            original="pkg.alpha.old_name",
            updated="core.beta.new_name",
            location="core/beta.py",
            confidence=0.8,
        )
    ]

    output = findings_to_markdown(findings)

    assert "`pkg/alpha.py:old_name` → `core/beta.py:new_name`" in output
