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
                "Method Diff": (
                    "@@ -1,2 +1,2 @@\n"
                    "-def moved_helper(v):\n"
                    "+def moved_helper(v, strict=False):"
                ),
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "# PyRef2 Refactoring Report" in output
    assert (
        "`pkg/`{`alpha.py` → `beta.py`}:`moved_helper` "
        "[Moved and changed]"
    ) in output
    assert "```diff" in output
    assert "@@ -1,2 +1,2 @@" in output


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
                "Functional Change Reasons": ["class bases changed"],
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

    assert (
        "`foo/bar/pkg/`{`alpha.py` → `beta.py`}:`Customer` "
        "[Moved]"
    ) in output


def test_markdown_renders_same_name_move_without_functional_change() -> None:
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

    assert "`pkg/`{`alpha.py` → `beta.py`}:`same_name` [Moved]" in output


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

    assert (
        "`foo/bar/`{`alpha.py`:`Customer._legacy_helper` → "
        "`baz/beta.py`:`helper`} [Moved and changed]"
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
        "[Moved and changed]"
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
                "Method Diff": (
                    "@@ -1,2 +1,3 @@\n"
                    "-def compute(a):\n"
                    "+def compute(a):\n"
                    "+    result = a + 1"
                ),
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "- `pkg/alpha.py`" in output
    assert "`pkg/alpha.py`:`compute` [Changed]" in output
    assert "+    result = a + 1" in output


def test_markdown_no_functional_change_has_no_diff_block() -> None:
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
                "Method Diff": "@@ -1,1 +1,1 @@\n-unchanged\n+unchanged",
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "```diff" not in output


def test_markdown_lists_added_and_removed_symbols() -> None:
    findings = [
        RefactoringFinding(
            refactoring_type="Remove Symbol",
            original="pkg.alpha.DEBUG",
            updated="<none>",
            location="pkg/alpha.py",
            confidence=1.0,
            details={
                "Scope": "pkg/alpha.py",
                "Symbol Kind": "constant",
            },
        ),
        RefactoringFinding(
            refactoring_type="Add Symbol",
            original="<none>",
            updated="pkg.beta.VERBOSE",
            location="pkg/beta.py",
            confidence=1.0,
            details={
                "Scope": "pkg/beta.py",
                "Symbol Kind": "constant",
            },
        ),
    ]

    output = findings_to_markdown(findings)

    assert "- `pkg/alpha.py`" in output
    assert "- `pkg/beta.py`" in output
    assert "- `pkg/alpha.py`" in output
    assert "- `pkg/beta.py`" in output
    assert "`pkg/beta.py`:`VERBOSE` [Added]" in output
    assert "`pkg/alpha.py`:`DEBUG` [Removed]" in output


def test_move_class_with_method_changes_includes_diff() -> None:
    """Regression test: moved class with only method changes should be [Moved] without diff.
    
    When a class is moved and only contained methods changed (no class-level changes),
    it should be reported as [Moved] because the method changes are reported separately.
    """
    findings = [
        RefactoringFinding(
            refactoring_type="Move Class",
            original="pkg.module_a.Config",
            updated="pkg.module_b.Config",
            location="pkg/module_b.py",
            confidence=0.95,
            details={
                "Old Module": "pkg/module_a.py",
                "New Module": "pkg/module_b.py",
                "Original Line": 1,
                "Updated Line": 1,
                "Functional Change Status": "Functional Change Detected",
                "Functional Change Reasons": ["contained methods changed behavior"],
                "Method Changes": [
                    {
                        "Kind": "method",
                        "Original": "__init__",
                        "Updated": "__init__",
                        "Functional Change Status": "Functional Change Detected",
                        "Functional Change Reasons": ["signature changed"],
                        "Method Diff": (
                            "@@ -1,2 +1,3 @@\n"
                            "-def __init__(self, x):\n"
                            "+def __init__(self, x, y):\n"
                            "    pass"
                        ),
                    }
                ],
            },
        )
    ]

    output = findings_to_markdown(findings)

    # Should include the moved class as [Moved] (not [Moved and changed])
    # because only contained methods changed, which are reported separately
    assert (
        "`pkg/`{`module_a.py` → `module_b.py`}:`Config` [Moved]"
        in output
    )
    # Should NOT include a diff at the class level
    assert "```diff" not in output


def test_move_class_with_class_level_changes_includes_diff() -> None:
    """Test: moved class with class-level changes should show [Moved and changed]."""
    findings = [
        RefactoringFinding(
            refactoring_type="Move Class",
            original="pkg.module_a.Config",
            updated="pkg.module_b.Config",
            location="pkg/module_b.py",
            confidence=0.95,
            details={
                "Old Module": "pkg/module_a.py",
                "New Module": "pkg/module_b.py",
                "Original Line": 1,
                "Updated Line": 1,
                "Functional Change Status": "Functional Change Detected",
                "Functional Change Reasons": ["class bases changed"],
                "Method Changes": [
                    {
                        "Kind": "method",
                        "Original": "__init__",
                        "Updated": "__init__",
                        "Functional Change Status": "Functional Change Detected",
                        "Functional Change Reasons": ["signature changed"],
                        "Method Diff": (
                            "@@ -1,2 +1,3 @@\n"
                            "-def __init__(self, x):\n"
                            "+def __init__(self, x, y):\n"
                            "    pass"
                        ),
                    }
                ],
            },
        )
    ]

    output = findings_to_markdown(findings)

    # Should include the moved class as [Moved and changed] because bases changed
    assert (
        "`pkg/`{`module_a.py` → `module_b.py`}:`Config` [Moved and changed]"
        in output
    )
    # Without class source snapshots in details, renderer falls back to method diff.
    assert "```diff" in output
    assert "-def __init__(self, x):" in output
    assert "+def __init__(self, x, y):" in output


def test_move_class_residual_diff_hides_class_symbol_lines() -> None:
    """Class residual diff should hide assignment lines reported as class symbols."""
    findings = [
        RefactoringFinding(
            refactoring_type="Move Class",
            original="pkg.module_a.Config",
            updated="pkg.module_b.Config",
            location="pkg/module_b.py",
            confidence=0.95,
            details={
                "Old Module": "pkg/module_a.py",
                "New Module": "pkg/module_b.py",
                "Functional Change Status": "Functional Change Detected",
                "Functional Change Reasons": ["class structure changed"],
                "Class Source Before": (
                    "class Config:\n"
                    "    \"\"\"Old docstring.\"\"\"\n"
                    "    THRESHOLD = 10\n"
                    "\n"
                    "    def run(self):\n"
                    "        return 1\n"
                ),
                "Class Source After": (
                    "class Config:\n"
                    "    \"\"\"New docstring.\"\"\"\n"
                    "    THRESHOLD = 20\n"
                    "\n"
                    "    def run(self, debug=False):\n"
                    "        return 2\n"
                ),
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "`pkg/`{`module_a.py` → `module_b.py`}:`Config` [Moved and changed]" in output
    assert "-    \"\"\"Old docstring.\"\"\"" in output
    assert "+    \"\"\"New docstring.\"\"\"" in output
    assert "THRESHOLD" not in output
    assert "def run" not in output
    assert "    ..." in output


def test_move_class_with_only_lower_level_changes_is_not_class_changed() -> None:
    """If masked residual is identical, class should be [Moved] without class diff."""
    findings = [
        RefactoringFinding(
            refactoring_type="Move Class",
            original="pkg.module_a.TomlField",
            updated="pkg.module_b.TomlField",
            location="pkg/module_b.py",
            confidence=0.95,
            details={
                "Old Module": "pkg/module_a.py",
                "New Module": "pkg/module_b.py",
                "Functional Change Status": "Functional Change Detected",
                "Functional Change Reasons": ["class structure changed"],
                "Class Source Before": (
                    "class TomlField:\n"
                    "    KEY = 1\n"
                    "\n"
                    "    def apply_transform(self, raw_value):\n"
                    "        \"\"\"Old method docstring.\"\"\"\n"
                    "        return raw_value\n"
                ),
                "Class Source After": (
                    "class TomlField:\n"
                    "    KEY = 2\n"
                    "\n"
                    "    def apply_transform(self, raw_value):\n"
                    "        \"\"\"New method docstring.\"\"\"\n"
                    "        return raw_value\n"
                ),
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "`pkg/`{`module_a.py` → `module_b.py`}:`TomlField` [Moved]" in output
    assert "[Moved and changed]" not in output
    assert "```diff" not in output


def test_move_class_shows_comment_only_changes_in_class_symbol_block() -> None:
    """Comment-only edits inside class assignment blocks should remain visible."""
    findings = [
        RefactoringFinding(
            refactoring_type="Move Class",
            original="pkg.module_a.StringParser",
            updated="pkg.module_b.StringParser",
            location="pkg/module_b.py",
            confidence=0.95,
            details={
                "Old Module": "pkg/module_a.py",
                "New Module": "pkg/module_b.py",
                "Functional Change Status": "Functional Change Detected",
                "Functional Change Reasons": ["class structure changed"],
                "Class Source Before": (
                    "class StringParser:\n"
                    "    \"\"\"Old docstring.\"\"\"\n"
                    "\n"
                    "    _EXTRA_TYPES = {\n"
                    "        # Integer parser comment\n"
                    "        \"Integer\": _parse_integer,\n"
                    "    }\n"
                ),
                "Class Source After": (
                    "class StringParser:\n"
                    "    \"\"\"New docstring.\"\"\"\n"
                    "\n"
                    "    _EXTRA_TYPES = {\n"
                    "        \"Integer\": _parse_integer,\n"
                    "    }\n"
                ),
            },
        )
    ]

    output = findings_to_markdown(findings)

    assert "`pkg/`{`module_a.py` → `module_b.py`}:`StringParser` [Moved and changed]" in output
    assert "-        # Integer parser comment" in output
    assert "-    \"\"\"Old docstring.\"\"\"" in output
    assert "+    \"\"\"New docstring.\"\"\"" in output
