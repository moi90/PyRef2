"""Application service layer for orchestrating analysis runs and output.

This is the bridge between CLI/repository adapters and the pure detection core.
"""

from __future__ import annotations

import json
from pathlib import Path

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


def write_findings(path: str, findings: list[RefactoringFinding]) -> None:
    output = findings_to_json(findings)
    Path(path).write_text(output, encoding="utf-8")
