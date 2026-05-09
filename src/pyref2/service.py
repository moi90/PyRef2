"""Application service layer for orchestrating analysis runs and output.

This is the bridge between CLI/repository adapters and the pure detection core.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyref2.core.ast_analysis import module_from_file
from pyref2.core.detectors import default_detectors
from pyref2.core.diff_engine import diff_modules
from pyref2.models.refactorings import RefactoringFinding


def analyze_files(before_path: str, after_path: str) -> list[RefactoringFinding]:
    """Run the full MVP pipeline on two Python files."""
    before_module = module_from_file(before_path)
    after_module = module_from_file(after_path)

    # One structural diff is fanned out to multiple specialized detectors.
    module_diff = diff_modules(before_module, after_module)
    findings: list[RefactoringFinding] = []

    for detector in default_detectors():
        findings.extend(detector.detect(module_diff))

    findings.sort(key=lambda item: (item.refactoring_type, item.original, item.updated))
    return findings


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
