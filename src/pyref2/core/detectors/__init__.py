"""Built-in detector registry."""

from pyref2.core.detectors.base import RefactoringDetector
from pyref2.core.detectors.method_detectors import (
    AddRemoveSymbolDetector,
    ChangeClassSignatureDetector,
    ChangeMethodSignatureDetector,
    ExtractMethodDetector,
    InlineMethodDetector,
    ModifyMethodDetector,
    ModifySymbolDetector,
    MoveMethodDetector,
    MoveSymbolDetector,
    RenameMethodDetector,
    RenameSymbolDetector,
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
        MoveSymbolDetector(),
        RenameSymbolDetector(),
        ModifySymbolDetector(),
        AddRemoveSymbolDetector(),
    ]
