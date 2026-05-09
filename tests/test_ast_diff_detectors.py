from __future__ import annotations

from pathlib import Path

from pyref2.core.ast_analysis import parse_module
from pyref2.service import analyze_files


def _write_module(tmp_path: Path, filename: str, source: str) -> str:
    path = tmp_path / filename
    path.write_text(source, encoding="utf-8")
    return str(path)


def test_parse_module_extracts_class_and_methods() -> None:
    module = parse_module(
        """
class Service:
    def run(self, value):
        return value + 1

def helper(x):
    return x
""",
        module_name="service.py",
    )

    assert len(module.classes) == 1
    assert len(module.methods) == 2


def test_detect_rename_method(tmp_path: Path) -> None:
    before = _write_module(
        tmp_path,
        "before.py",
        """
def old_name(v):
    return v * 2
""",
    )
    after = _write_module(
        tmp_path,
        "after.py",
        """
def new_name(v):
    return v * 2
""",
    )

    findings = analyze_files(before, after)
    assert any(f.refactoring_type == "Rename Method" for f in findings)


def test_detect_add_parameter(tmp_path: Path) -> None:
    before = _write_module(
        tmp_path,
        "before.py",
        """
def compute(a):
    return a + 1
""",
    )
    after = _write_module(
        tmp_path,
        "after.py",
        """
def compute(a, b):
    return a + b
""",
    )

    findings = analyze_files(before, after)
    add_parameter_findings = [f for f in findings if f.refactoring_type == "Add Parameter"]
    assert add_parameter_findings
    assert all(
        finding.details.get("Functional Change Status") == "Functional Change Detected"
        for finding in add_parameter_findings
    )


def test_detect_extract_method(tmp_path: Path) -> None:
    before = _write_module(
        tmp_path,
        "before.py",
        """
def process(v):
    x = v + 1
    y = x * 2
    return y
""",
    )
    after = _write_module(
        tmp_path,
        "after.py",
        """
def helper(v):
    x = v + 1
    y = x * 2
    return y

def process(v):
    return helper(v)
""",
    )

    findings = analyze_files(before, after)
    extract_findings = [f for f in findings if f.refactoring_type == "Extract Method"]
    assert extract_findings
    assert all(
        "Functional Change Status" in finding.details for finding in extract_findings
    )


def test_detect_modify_method_without_move_or_rename(tmp_path: Path) -> None:
    before = _write_module(
        tmp_path,
        "before.py",
        """
def compute(a):
    return a + 1
""",
    )
    after = _write_module(
        tmp_path,
        "after.py",
        """
def compute(a):
    result = a + 1
    return result + 1
""",
    )

    findings = analyze_files(before, after)
    modify_findings = [f for f in findings if f.refactoring_type == "Modify Method"]

    assert modify_findings
    assert all(
        finding.details.get("Functional Change Status") == "Functional Change Detected"
        for finding in modify_findings
    )
    assert all(
        isinstance(finding.details.get("Method Diff"), str)
        and "@@" in finding.details["Method Diff"]
        for finding in modify_findings
    )


def test_detect_inline_method_has_functional_status(tmp_path: Path) -> None:
    before = _write_module(
        tmp_path,
        "before.py",
        """
def helper(v):
    return v + 1

def process(v):
    return helper(v)
""",
    )
    after = _write_module(
        tmp_path,
        "after.py",
        """
def process(v):
    return v + 1
""",
    )

    findings = analyze_files(before, after)
    inline_findings = [f for f in findings if f.refactoring_type == "Inline Method"]

    assert inline_findings
    assert all(
        "Functional Change Status" in finding.details for finding in inline_findings
    )
