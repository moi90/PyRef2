from __future__ import annotations

from typing import Protocol

from pyref2.core.diff_engine import ModuleDiff
from pyref2.models.refactorings import RefactoringFinding


class RefactoringDetector(Protocol):
    """Detector contract used by all pipeline strategies."""

    name: str

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        """Return all findings for a single module diff."""
