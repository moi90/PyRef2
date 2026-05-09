from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RefactoringFinding:
    """Canonical representation of one detected refactoring."""

    refactoring_type: str
    original: str
    updated: str
    location: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "Refactoring Type": self.refactoring_type,
            "Original": self.original,
            "Updated": self.updated,
            "Location": self.location,
            "Confidence": round(self.confidence, 4),
        }
        payload.update(self.details)
        return payload
