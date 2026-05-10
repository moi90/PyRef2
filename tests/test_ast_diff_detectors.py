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


def test_extract_module_level_variable_symbols() -> None:
    """Test that module-level variable and constant symbols are extracted."""
    module = parse_module(
        """
DEBUG_FLAG = True
timeout = 30
CONFIG = {"key": "value"}
""",
        module_name="config.py",
    )

    assert len(module.symbols) == 3
    symbol_names = {s.name for s in module.symbols}
    assert symbol_names == {"DEBUG_FLAG", "timeout", "CONFIG"}
    
    # Check kinds
    debug_flag_sym = next(s for s in module.symbols if s.name == "DEBUG_FLAG")
    assert debug_flag_sym.kind == "constant"
    
    timeout_sym = next(s for s in module.symbols if s.name == "timeout")
    assert timeout_sym.kind == "variable"


def test_detect_rename_symbol(tmp_path: Path) -> None:
    """Test detection of symbol rename in same location."""
    before = _write_module(
        tmp_path,
        "config.py",
        """
DEBUG_FLAG = True
""",
    )
    after = _write_module(
        tmp_path,
        "config_modified.py",
        """
VERBOSE_MODE = True
""",
    )

    findings = analyze_files(before, after)
    # File names differ, so this becomes a move + rename
    symbol_findings = [
        f for f in findings
        if f.refactoring_type in {"Rename Symbol", "Move Symbol"}
    ]

    assert symbol_findings, (
        f"Expected symbol findings but got: "
        f"{[f.refactoring_type for f in findings]}"
    )


def test_detect_move_symbol_to_different_module(tmp_path: Path) -> None:
    """Test detection of symbol move to a different module."""
    from pyref2.service import analyze_trees

    # Create before tree with symbol in alpha.py
    before_dir = tmp_path / "before"
    before_dir.mkdir()
    (before_dir / "alpha.py").write_text("CONFIG = {}", encoding="utf-8")
    (before_dir / "beta.py").write_text("", encoding="utf-8")

    # Create after tree with symbol in beta.py
    after_dir = tmp_path / "after"
    after_dir.mkdir()
    (after_dir / "alpha.py").write_text("", encoding="utf-8")
    (after_dir / "beta.py").write_text("CONFIG = {}", encoding="utf-8")

    findings = analyze_trees(str(before_dir), str(after_dir))
    move_findings = [
        f for f in findings if f.refactoring_type == "Move Symbol"
    ]

    assert move_findings, (
        f"Expected Move Symbol findings, got: "
        f"{[f.refactoring_type for f in findings]}"
    )


def test_detect_modify_symbol_value(tmp_path: Path) -> None:
    """Test detection of symbol value change."""
    before = _write_module(
        tmp_path,
        "before.py",
        """
TIMEOUT = 30
""",
    )
    after = _write_module(
        tmp_path,
        "after.py",
        """
TIMEOUT = 60
""",
    )

    findings = analyze_files(before, after)
    modify_findings = [
        f for f in findings if f.refactoring_type == "Modify Symbol"
    ]

    assert modify_findings
    status = modify_findings[0].details.get("Functional Change Status")
    assert status == "Functional Change Detected"


def test_unmatched_symbol_reports_add_and_remove(tmp_path: Path) -> None:
    """Conservative mode should report unmatched symbol as removed + added."""
    from pyref2.service import analyze_trees

    before_dir = tmp_path / "before"
    before_dir.mkdir()
    (before_dir / "config_a.py").write_text("DEBUG = True", encoding="utf-8")
    (before_dir / "config_b.py").write_text("", encoding="utf-8")

    after_dir = tmp_path / "after"
    after_dir.mkdir()
    (after_dir / "config_a.py").write_text("", encoding="utf-8")
    (after_dir / "config_b.py").write_text("VERBOSE = False", encoding="utf-8")

    findings = analyze_trees(str(before_dir), str(after_dir))
    finding_types = {f.refactoring_type for f in findings}

    assert "Remove Symbol" in finding_types
    assert "Add Symbol" in finding_types
