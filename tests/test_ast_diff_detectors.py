from __future__ import annotations

from pyref2.core.ast_analysis import parse_module
from pyref2.service import analyze_files


def _write_module(tmp_path, filename: str, source: str) -> str:
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


def test_detect_rename_method(tmp_path) -> None:
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


def test_detect_add_parameter(tmp_path) -> None:
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
    assert any(f.refactoring_type == "Add Parameter" for f in findings)


def test_detect_extract_method(tmp_path) -> None:
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
    assert any(f.refactoring_type == "Extract Method" for f in findings)
