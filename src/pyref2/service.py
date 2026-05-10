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
    symbols = tuple(symbol for module in modules for symbol in module.symbols)
    return ModuleEntity(name=label, methods=methods, classes=classes, symbols=symbols)


def findings_to_json(findings: list[RefactoringFinding]) -> str:
    """Serialize findings using an explicit schema version for forward compatibility."""
    payload = {
        "schema_version": "0.1.0",
        "findings": [finding.to_dict() for finding in findings],
    }
    return json.dumps(payload, indent=2)


def findings_to_markdown(findings: list[RefactoringFinding]) -> str:
    """Render findings as a hierarchical report for developers."""
    lines = ["# PyRef2 Refactoring Report", "", f"Total findings: {len(findings)}", ""]

    if not findings:
        lines.append("No refactorings detected.")
        return "\n".join(lines)

    entries_by_file: dict[str, list[tuple[str, str | None]]] = defaultdict(list)

    def _append_file_entry(file_path: str, entry: str, diff_block: str | None = None) -> None:
        entries_by_file[file_path].append((entry, diff_block))

    for finding in findings:
        if finding.refactoring_type == "Move Class":
            old_path, old_symbol = _split_reference(finding.original)
            new_path, new_symbol = _split_reference(finding.updated)
            status = _functional_status(finding)
            class_label = "Moved and changed" if status == "Functional Change Detected" else "Moved"
            _append_file_entry(
                old_path,
                f"{_format_compact_change_line(old_path, old_symbol, new_path, new_symbol)} "
                f"[{class_label}]",
            )
            continue

        if finding.refactoring_type in {"Move Method", "Rename Method"}:
            old_path, old_scope, old_name, new_path, new_scope, new_name = _method_context(finding)
            status = _functional_status(finding)
            if finding.refactoring_type == "Move Method":
                change_label = (
                    "Moved and changed"
                    if status == "Functional Change Detected"
                    else "Moved"
                )
            else:
                change_label = "Renamed"
            should_render = (
                True
                if finding.refactoring_type == "Move Method"
                else _should_render_method_entry(old_name, new_name, status)
            )
            if not should_render:
                continue
            if old_scope is None and new_scope is None:
                entry = _format_compact_change_line(old_path, old_name, new_path, new_name)
                _append_file_entry(
                    old_path,
                    f"{entry} [{change_label}]",
                    _render_method_diff(finding.details, status),
                )
                continue

            if (old_scope is None) != (new_scope is None):
                entry = _format_compact_change_line(
                    old_path,
                    _scoped_symbol(old_scope, old_name),
                    new_path,
                    _scoped_symbol(new_scope, new_name),
                )
                _append_file_entry(
                    old_path,
                    f"{entry} [{change_label}]",
                    _render_method_diff(finding.details, status),
                )
                continue

            scoped_old = _scoped_symbol(old_scope, old_name)
            scoped_new = _scoped_symbol(new_scope, new_name)
            mixed_entry = _format_compact_change_line(old_path, scoped_old, new_path, scoped_new)
            _append_file_entry(
                old_path,
                f"{mixed_entry} [{change_label}]",
                _render_method_diff(finding.details, status),
            )
            continue

        if finding.refactoring_type == "Move Symbol":
            old_path, old_symbol = _split_reference(finding.original)
            new_path, new_symbol = _split_reference(finding.updated)
            status = _functional_status(finding)
            compact_ref = _format_compact_change_line(old_path, old_symbol, new_path, new_symbol)
            moved_label = (
                "Moved and changed"
                if status == "Functional Change Detected"
                else "Moved"
            )
            entry = f"{compact_ref} [{moved_label}]"
            _append_file_entry(old_path, entry, _render_method_diff(finding.details, status))
            continue

        if finding.refactoring_type == "Rename Symbol":
            old_path, old_symbol = _split_reference(finding.original)
            new_path, new_symbol = _split_reference(finding.updated)
            status = _functional_status(finding)
            compact_ref = _format_compact_change_line(old_path, old_symbol, new_path, new_symbol)
            entry = f"{compact_ref} [Renamed]"
            _append_file_entry(old_path, entry, _render_method_diff(finding.details, status))
            continue

        if finding.refactoring_type == "Add Symbol":
            new_path, new_symbol = _split_reference(finding.updated)
            entries_by_file[new_path].append((f"`{new_path}`:`{new_symbol}` [Added]", None))
            continue

        if finding.refactoring_type == "Remove Symbol":
            old_path, old_symbol = _split_reference(finding.original)
            entries_by_file[old_path].append((f"`{old_path}`:`{old_symbol}` [Removed]", None))
            continue

        status = _functional_status(finding)
        rendered_status = "Changed" if status == "Functional Change Detected" else status
        old_path, old_symbol = _split_reference(finding.original)
        new_path, new_symbol = _split_reference(finding.updated)
        _append_file_entry(
            old_path,
            _format_change_line(old_path, old_symbol, new_path, new_symbol, rendered_status),
            _render_method_diff(finding.details, status),
        )

    for file_path in sorted(entries_by_file):
        for entry, diff_block in sorted(entries_by_file[file_path], key=lambda item: item[0]):
            _append_markdown_entry(
                lines,
                entry,
                diff_block,
                bullet_prefix="- ",
                indent="  ",
            )

    return "\n".join(lines)


def _functional_status(finding: RefactoringFinding) -> str:
    return str(finding.details.get("Functional Change Status", "Unknown"))


def _render_method_diff(details: dict[str, object], status: str) -> str | None:
    if status != "Functional Change Detected":
        return None
    method_diff = details.get("Method Diff")
    if isinstance(method_diff, str) and method_diff.strip():
        return method_diff

    symbol_diff = details.get("Symbol Diff")
    if isinstance(symbol_diff, str) and symbol_diff.strip():
        return symbol_diff

    return None


def _append_markdown_entry(
    lines: list[str],
    entry: str,
    diff_block: str | None,
    *,
    bullet_prefix: str = "- ",
    indent: str,
) -> None:
    lines.append(f"{bullet_prefix}{entry}")
    if diff_block is None:
        return

    lines.append(f"{indent}```diff")
    for diff_line in diff_block.splitlines():
        lines.append(f"{indent}{diff_line}")
    lines.append(f"{indent}```")


def _should_render_method_entry(old_name: str, new_name: str, status: str) -> bool:
    if old_name != new_name:
        return True
    return status == "Functional Change Detected"


def _format_change_line(
    old_path: str,
    old_symbol: str,
    new_path: str,
    new_symbol: str,
    status: str,
) -> str:
    compact_change = _format_compact_change_line(old_path, old_symbol, new_path, new_symbol)
    return f"{compact_change} [{status}]"


def _format_compact_change_line(
    old_path: str,
    old_symbol: str,
    new_path: str,
    new_symbol: str,
) -> str:
    if old_path == new_path:
        if old_symbol == new_symbol:
            return f"`{old_path}`:`{old_symbol}`"
        return f"`{old_path}`:{{`{old_symbol}` → `{new_symbol}`}}"

    common_prefix = _common_path_prefix(old_path, new_path)
    if common_prefix == ".":
        return f"`{old_path}`:`{old_symbol}` → `{new_path}`:`{new_symbol}`"

    old_suffix = _path_suffix(old_path, common_prefix)
    new_suffix = _path_suffix(new_path, common_prefix)

    if old_symbol == new_symbol:
        return f"`{common_prefix}/`{{`{old_suffix}` → `{new_suffix}`}}:`{old_symbol}`"

    return (
        f"`{common_prefix}/`{{`{old_suffix}`:`{old_symbol}` → "
        f"`{new_suffix}`:`{new_symbol}`}}"
    )


def _scoped_symbol(scope: str | None, name: str) -> str:
    if scope is None:
        return name
    return f"{scope}.{name}"


def _method_context(
    finding: RefactoringFinding,
) -> tuple[str, str | None, str, str, str | None, str]:
    old_path, old_symbol = _split_reference(finding.original)
    new_path, new_symbol = _split_reference(finding.updated)

    old_scope, old_name = _split_scoped_symbol(old_symbol)
    new_scope, new_name = _split_scoped_symbol(new_symbol)

    detail_old_module = finding.details.get("Old Module")
    detail_new_module = finding.details.get("New Module")
    detail_old_scope = finding.details.get("Old Scope")
    detail_new_scope = finding.details.get("New Scope")

    if isinstance(detail_old_module, str) and detail_old_module:
        old_path = detail_old_module
    if isinstance(detail_new_module, str) and detail_new_module:
        new_path = detail_new_module
    if detail_old_scope is None or isinstance(detail_old_scope, str):
        old_scope = detail_old_scope
    if detail_new_scope is None or isinstance(detail_new_scope, str):
        new_scope = detail_new_scope

    return old_path, old_scope, old_name, new_path, new_scope, new_name


def _split_scoped_symbol(symbol: str) -> tuple[str | None, str]:
    if "." not in symbol:
        return None, symbol
    scope, name = symbol.split(".", maxsplit=1)
    return scope, name


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
    """Render one finding as a compact, code-fenced markdown diff."""
    old_path, old_symbol = _split_reference(original)
    new_path, new_symbol = _split_reference(updated)

    common_prefix = _common_path_prefix(old_path, new_path)

    if common_prefix == ".":
        return f"`{old_path}:{old_symbol}` → `{new_path}:{new_symbol}`"

    old_suffix = _path_suffix(old_path, common_prefix)
    new_suffix = _path_suffix(new_path, common_prefix)

    if old_symbol == new_symbol:
        return (
            f"`{common_prefix}/`"
            + "{"
            + f"`{old_suffix}` → `{new_suffix}`"
            + "}"
            + f"`:{old_symbol}`"
        )

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
