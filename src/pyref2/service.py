"""Application service layer for orchestrating analysis runs and output.

This is the bridge between CLI/repository adapters and the pure detection core.
"""

from __future__ import annotations

import json
import posixpath
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pyref2.core.ast_analysis import module_from_file
from pyref2.core.detectors import default_detectors
from pyref2.core.diff_engine import diff_modules
from pyref2.models.code_elements import ModuleEntity
from pyref2.models.refactorings import RefactoringFinding
from pyref2.repository import aggregate_revision, parse_revision_range


def analyze_files(before_path: str, after_path: str) -> list[RefactoringFinding]:
    """Run the full MVP pipeline on two Python files."""
    before_module = module_from_file(before_path, module_name="<module>")
    after_module = module_from_file(after_path, module_name="<module>")

    return _run_detectors(before_module, after_module)


def analyze_trees(before_root: str, after_root: str) -> list[RefactoringFinding]:
    """Run the full MVP pipeline on two source tree revisions."""
    before_module = _aggregate_tree(before_root, label="before-tree")
    after_module = _aggregate_tree(after_root, label="after-tree")

    return _run_detectors(before_module, after_module)


def analyze_revisions(
    repo_path: str,
    before_revision: str,
    after_revision: str,
) -> list[RefactoringFinding]:
    """Run the full MVP pipeline on two Git revisions from one repository."""
    before_module = aggregate_revision(repo_path, before_revision, label=before_revision)
    after_module = aggregate_revision(repo_path, after_revision, label=after_revision)

    return _run_detectors(before_module, after_module)


def analyze_revision_range(repo_path: str, revision_range: str) -> list[RefactoringFinding]:
    """Run revision analysis for a Git range like `origin/main..HEAD`."""
    before_revision, after_revision = parse_revision_range(revision_range)
    return analyze_revisions(repo_path, before_revision, after_revision)


def _run_detectors(
    before_module: ModuleEntity,
    after_module: ModuleEntity,
) -> list[RefactoringFinding]:
    """Apply the detector registry to two aggregated revisions."""

    # One structural diff is fanned out to multiple specialized detectors.
    module_diff = diff_modules(before_module, after_module)
    findings: list[RefactoringFinding] = []

    for detector in default_detectors():
        findings.extend(detector.detect(module_diff))

    findings.sort(key=lambda item: (item.refactoring_type, item.original, item.updated))
    return findings


def _aggregate_tree(root: str, label: str) -> ModuleEntity:
    """Parse all Python files below a source tree into one logical revision view."""
    root_path = Path(root)
    modules = [
        module_from_file(str(path), module_name=path.relative_to(root_path).as_posix())
        for path in sorted(root_path.rglob("*.py"))
        if path.is_file()
    ]

    methods = tuple(method for module in modules for method in module.methods)
    classes = tuple(class_entity for module in modules for class_entity in module.classes)
    return ModuleEntity(name=label, methods=methods, classes=classes)


def findings_to_json(findings: list[RefactoringFinding]) -> str:
    """Serialize findings using an explicit schema version for forward compatibility."""
    payload = {
        "schema_version": "0.1.0",
        "findings": [finding.to_dict() for finding in findings],
    }
    return json.dumps(payload, indent=2)


def findings_to_markdown(findings: list[RefactoringFinding]) -> str:
    """Render findings as a readable report for developers."""
    lines = ["# PyRef2 Refactoring Report", "", f"Total findings: {len(findings)}", ""]

    if not findings:
        lines.append("No refactorings detected.")
        return "\n".join(lines)

    grouped: dict[str, list[RefactoringFinding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.refactoring_type].append(finding)

    for refactoring_type in sorted(grouped):
        grouped_findings = grouped[refactoring_type]
        lines.extend(
            [
                f"## {refactoring_type} ({len(grouped_findings)})",
                "",
                "| Change | Confidence |",
                "| --- | ---: |",
            ]
        )

        for finding in grouped_findings:
            change = _format_compact_change(finding.original, finding.updated)
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_markdown_cell(change),
                        f"{finding.confidence:.2f}",
                    ]
                )
                + " |"
            )

        lines.append("")

    return "\n".join(lines)


def serialize_findings(
    findings: list[RefactoringFinding],
    output_format: Literal["json", "markdown"] = "json",
) -> str:
    """Serialize findings in the requested output format."""
    if output_format == "markdown":
        return findings_to_markdown(findings)
    return findings_to_json(findings)


def write_findings(
    path: str,
    findings: list[RefactoringFinding],
    output_format: Literal["json", "markdown"] = "json",
) -> None:
    output = serialize_findings(findings, output_format)
    Path(path).write_text(output, encoding="utf-8")


def _escape_markdown_cell(value: str) -> str:
    """Escape markdown table cell text to avoid malformed reports."""
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _format_compact_change(original: str, updated: str) -> str:
    """Render one finding as `<common-prefix>/{path-a:symbol -> path-b:symbol}`."""
    old_path, old_symbol = _split_reference(original)
    new_path, new_symbol = _split_reference(updated)

    common_prefix = _common_path_prefix(old_path, new_path)

    if common_prefix == ".":
        return f"`{old_path}:{old_symbol}` → `{new_path}:{new_symbol}`"

    old_suffix = _path_suffix(old_path, common_prefix)
    new_suffix = _path_suffix(new_path, common_prefix)

    return (
        f"`{common_prefix}/`"
        + "{"
        + f"`{old_suffix}:{old_symbol}` → `{new_suffix}:{new_symbol}`"
        + "}"
    )


def _split_reference(reference: str) -> tuple[str, str]:
    """Split `module.path.symbol` into `module/path.py`, `symbol`."""
    py_marker = ".py."
    if py_marker in reference:
        marker_index = reference.index(py_marker)
        path = reference[: marker_index + 3]
        symbol = reference[marker_index + len(py_marker) :]
        return path, symbol or "<module>"

    if reference.endswith(".py"):
        return reference, "<module>"

    parts = reference.split(".")
    if len(parts) < 2:
        return reference, "<module>"

    symbol_segment_count = 1
    if len(parts) >= 3 and parts[-2][:1].isupper():
        symbol_segment_count = 2

    module_parts = parts[:-symbol_segment_count]
    symbol_parts = parts[-symbol_segment_count:]

    path = "/".join(module_parts) + ".py"
    symbol = ".".join(symbol_parts) if symbol_parts else "<module>"
    return path, symbol


def _common_path_prefix(left: str, right: str) -> str:
    """Return shared path prefix using path segment boundaries."""
    shared_prefix = posixpath.commonpath([left, right])
    if shared_prefix in ("", "."):
        return "."
    return shared_prefix


def _path_suffix(path: str, prefix: str) -> str:
    """Return path without prefix while preserving filename-only outputs."""
    if prefix == ".":
        return path
    if path == prefix:
        return "."
    return path.removeprefix(prefix + "/")
