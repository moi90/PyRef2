"""Built-in detector registry."""

from pyref2.core.detectors.base import RefactoringDetector
from pyref2.core.detectors.method_detectors import (
    ChangeClassSignatureDetector,
    ChangeMethodSignatureDetector,
    ExtractMethodDetector,
    InlineMethodDetector,
    ModifyMethodDetector,
    MoveMethodDetector,
    RenameMethodDetector,
)


def default_detectors() -> list[RefactoringDetector]:
    return [
        RenameMethodDetector(),
        ChangeMethodSignatureDetector(),
        ModifyMethodDetector(),
        MoveMethodDetector(),
        ExtractMethodDetector(),
        InlineMethodDetector(),
        ChangeClassSignatureDetector(),
    ]
