"""Built-in heuristic detectors for the PyRef2 MVP.

Each detector focuses on one refactoring family and consumes the same ModuleDiff
to keep the pipeline composable and easy to extend with future strategies.
"""

from __future__ import annotations

from pyref2.core.detectors.base import RefactoringDetector
from pyref2.core.diff_engine import MatchedClass, MatchedMethod, ModuleDiff
from pyref2.models.refactorings import RefactoringFinding


class RenameMethodDetector(RefactoringDetector):
    name = "rename-method"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        # High confidence rename: same scope, different name, very similar body.
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_methods:
            if pair.before.name == pair.after.name:
                continue
            if pair.before.class_name != pair.after.class_name:
                continue
            if pair.similarity < 0.85:
                continue

            findings.append(
                RefactoringFinding(
                    refactoring_type="Rename Method",
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=pair.similarity,
                    details={
                        "Original Line": pair.before.lineno,
                        "Updated Line": pair.after.lineno,
                    },
                )
            )
        return findings


class ChangeMethodSignatureDetector(RefactoringDetector):
    name = "change-method-signature"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_methods:
            if pair.before.params == pair.after.params:
                continue

            param_type = _param_change_type(pair)
            findings.append(
                RefactoringFinding(
                    refactoring_type=param_type,
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=max(0.55, pair.similarity),
                    details={
                        "Old Params": list(pair.before.params),
                        "New Params": list(pair.after.params),
                        "Original Line": pair.before.lineno,
                        "Updated Line": pair.after.lineno,
                    },
                )
            )
        return findings


class MoveMethodDetector(RefactoringDetector):
    name = "move-method"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_methods:
            same_scope = (
                pair.before.class_name == pair.after.class_name
                and pair.before.module_name == pair.after.module_name
            )
            if same_scope:
                continue
            if pair.before.name != pair.after.name:
                continue
            if pair.similarity < 0.8:
                continue

            findings.append(
                RefactoringFinding(
                    refactoring_type="Move Method",
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=pair.similarity,
                    details={
                        "Old Module": pair.before.module_name,
                        "New Module": pair.after.module_name,
                        "Old Scope": pair.before.class_name,
                        "New Scope": pair.after.class_name,
                    },
                )
            )
        return findings


class ExtractMethodDetector(RefactoringDetector):
    name = "extract-method"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        # Extraction signal: newly added helper now called by a previously matched method.
        findings: list[RefactoringFinding] = []
        for added_method in module_diff.added_methods:
            for pair in module_diff.matched_methods:
                if added_method.name not in pair.after.called_names:
                    continue
                if added_method.name in pair.before.called_names:
                    continue
                if len(added_method.body_signature) < 2:
                    continue

                confidence = min(0.95, 0.55 + 0.04 * len(added_method.body_signature))
                findings.append(
                    RefactoringFinding(
                        refactoring_type="Extract Method",
                        original=pair.before.qualified_name,
                        updated=added_method.qualified_name,
                        location=pair.after.module_name,
                        confidence=confidence,
                        details={
                            "Source Line": pair.before.lineno,
                            "Extracted Line": added_method.lineno,
                        },
                    )
                )
        return findings


class InlineMethodDetector(RefactoringDetector):
    name = "inline-method"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        # Inline signal: removed callee was called before and is no longer called after.
        findings: list[RefactoringFinding] = []
        for removed_method in module_diff.removed_methods:
            for pair in module_diff.matched_methods:
                if removed_method.name not in pair.before.called_names:
                    continue
                if removed_method.name in pair.after.called_names:
                    continue

                findings.append(
                    RefactoringFinding(
                        refactoring_type="Inline Method",
                        original=removed_method.qualified_name,
                        updated=pair.after.qualified_name,
                        location=pair.after.module_name,
                        confidence=max(0.6, pair.similarity),
                        details={
                            "Removed Line": removed_method.lineno,
                            "Destination Line": pair.after.lineno,
                        },
                    )
                )
        return findings


class ChangeClassSignatureDetector(RefactoringDetector):
    name = "change-class-signature"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_classes:
            findings.extend(_class_move_findings(pair))
            findings.extend(_class_rename_findings(pair))
            findings.extend(_class_base_change_findings(pair))
        return findings


def _class_move_findings(pair: MatchedClass) -> list[RefactoringFinding]:
    if pair.before.module_name == pair.after.module_name:
        return []
    if pair.before.name != pair.after.name:
        return []
    if pair.similarity < 0.65:
        return []

    return [
        RefactoringFinding(
            refactoring_type="Move Class",
            original=pair.before.qualified_name,
            updated=pair.after.qualified_name,
            location=pair.after.module_name,
            confidence=pair.similarity,
            details={
                "Old Module": pair.before.module_name,
                "New Module": pair.after.module_name,
                "Original Line": pair.before.lineno,
                "Updated Line": pair.after.lineno,
            },
        )
    ]


def _class_rename_findings(pair: MatchedClass) -> list[RefactoringFinding]:
    if pair.before.name == pair.after.name:
        return []
    if pair.similarity < 0.65:
        return []

    return [
        RefactoringFinding(
            refactoring_type="Rename Class",
            original=pair.before.qualified_name,
            updated=pair.after.qualified_name,
            location=pair.after.module_name,
            confidence=pair.similarity,
            details={"Original Line": pair.before.lineno, "Updated Line": pair.after.lineno},
        )
    ]


def _class_base_change_findings(pair: MatchedClass) -> list[RefactoringFinding]:
    if pair.before.bases == pair.after.bases:
        return []
    return [
        RefactoringFinding(
            refactoring_type="Change Class Signature",
            original=pair.before.qualified_name,
            updated=pair.after.qualified_name,
            location=pair.after.module_name,
            confidence=max(0.55, pair.similarity),
            details={"Old Bases": list(pair.before.bases), "New Bases": list(pair.after.bases)},
        )
    ]


def _param_change_type(pair: MatchedMethod) -> str:
    before = pair.before.params
    after = pair.after.params

    if len(after) > len(before):
        if before == after[: len(before)]:
            return "Add Parameter"
        return "Change Method Signature"

    if len(after) < len(before):
        if after == before[: len(after)]:
            return "Remove Parameter"
        return "Change Method Signature"

    if set(before) != set(after):
        return "Change Method Signature"

    return "Rename Parameter"
