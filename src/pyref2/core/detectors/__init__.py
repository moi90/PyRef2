"""Built-in detector registry."""

from pyref2.core.detectors.base import RefactoringDetector
from pyref2.core.detectors.method_detectors import (
    ChangeClassSignatureDetector,
    ChangeMethodSignatureDetector,
    ExtractMethodDetector,
    InlineMethodDetector,
    MoveMethodDetector,
    RenameMethodDetector,
)


def default_detectors() -> list[RefactoringDetector]:
    return [
        RenameMethodDetector(),
        ChangeMethodSignatureDetector(),
        MoveMethodDetector(),
        ExtractMethodDetector(),
        InlineMethodDetector(),
        ChangeClassSignatureDetector(),
    ]
