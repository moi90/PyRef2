"""Built-in heuristic detectors for the PyRef2 MVP.

Each detector focuses on one refactoring family and consumes the same ModuleDiff
to keep the pipeline composable and easy to extend with future strategies.
"""

from __future__ import annotations

import difflib
import textwrap

from pyref2.core.detectors.base import RefactoringDetector
from pyref2.core.diff_engine import MatchedClass, MatchedMethod, MatchedSymbol, ModuleDiff
from pyref2.models.refactorings import RefactoringFinding

FUNCTIONAL_STATUS_NO_CHANGE = "No Functional Change"
FUNCTIONAL_STATUS_CHANGED = "Functional Change Detected"


class RenameMethodDetector(RefactoringDetector):
    name = "rename-method"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        # High confidence rename: same scope, different name, very similar body.
        moved_class_transitions = _moved_class_transitions(module_diff)
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_methods:
            if pair.before.name == pair.after.name:
                continue
            if pair.before.class_name != pair.after.class_name:
                continue
            if pair.similarity < 0.85:
                continue
            if pair.before.class_name is not None and pair.after.class_name is not None:
                owning_class_transition = (
                    pair.before.module_name,
                    pair.before.class_name,
                    pair.after.module_name,
                    pair.after.class_name,
                )
                if owning_class_transition in moved_class_transitions:
                    # Renames caused by class moves are reported under Move Class.
                    continue

            assessment = _assess_method_functional_change(pair)

            findings.append(
                RefactoringFinding(
                    refactoring_type="Rename Method",
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=pair.similarity,
                    details={
                        "Old Module": pair.before.module_name,
                        "New Module": pair.after.module_name,
                        "Old Scope": pair.before.class_name,
                        "New Scope": pair.after.class_name,
                        "Functional Change Status": assessment["status"],
                        "Functional Change Reasons": assessment["reasons"],
                        "Method Diff": assessment["method_diff"],
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
            assessment = _assess_method_functional_change(pair)
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
                        "Functional Change Status": assessment["status"],
                        "Functional Change Reasons": assessment["reasons"],
                        "Method Diff": assessment["method_diff"],
                    },
                )
            )
        return findings


class ModifyMethodDetector(RefactoringDetector):
    name = "modify-method"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_methods:
            # Only report same-name, same-scope, same-module changes here.
            if pair.before.name != pair.after.name:
                continue
            if pair.before.module_name != pair.after.module_name:
                continue
            if pair.before.class_name != pair.after.class_name:
                continue
            # Signature changes are reported by ChangeMethodSignatureDetector.
            if pair.before.params != pair.after.params:
                continue

            assessment = _assess_method_functional_change(pair)
            if assessment["status"] != FUNCTIONAL_STATUS_CHANGED:
                continue

            findings.append(
                RefactoringFinding(
                    refactoring_type="Modify Method",
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=pair.similarity,
                    details={
                        "Old Module": pair.before.module_name,
                        "New Module": pair.after.module_name,
                        "Old Scope": pair.before.class_name,
                        "New Scope": pair.after.class_name,
                        "Functional Change Status": assessment["status"],
                        "Functional Change Reasons": assessment["reasons"],
                        "Method Diff": assessment["method_diff"],
                        "Original Line": pair.before.lineno,
                        "Updated Line": pair.after.lineno,
                    },
                )
            )
        return findings


class MoveMethodDetector(RefactoringDetector):
    name = "move-method"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        moved_class_transitions = _moved_class_transitions(module_diff)

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
            if pair.before.class_name is not None and pair.after.class_name is not None:
                owning_class_transition = (
                    pair.before.module_name,
                    pair.before.class_name,
                    pair.after.module_name,
                    pair.after.class_name,
                )
                if owning_class_transition in moved_class_transitions:
                    # Methods moved by class relocation are shown under Move Class.
                    continue

            assessment = _assess_method_functional_change(pair)

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
                        "Functional Change Status": assessment["status"],
                        "Functional Change Reasons": assessment["reasons"],
                        "Method Diff": assessment["method_diff"],
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
                assessment = _assess_method_functional_change(pair)
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
                            "Functional Change Status": assessment["status"],
                            "Functional Change Reasons": assessment["reasons"],
                            "Method Diff": assessment["method_diff"],
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

                assessment = _assess_method_functional_change(pair)

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
                            "Functional Change Status": assessment["status"],
                            "Functional Change Reasons": assessment["reasons"],
                            "Method Diff": assessment["method_diff"],
                        },
                    )
                )
        return findings


class ChangeClassSignatureDetector(RefactoringDetector):
    name = "change-class-signature"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_classes:
            findings.extend(_class_move_findings(pair, module_diff.matched_methods))
            findings.extend(_class_rename_findings(pair))
            findings.extend(_class_base_change_findings(pair))
        return findings


def _class_move_findings(
    pair: MatchedClass,
    matched_methods: tuple[MatchedMethod, ...],
) -> list[RefactoringFinding]:
    if pair.before.module_name == pair.after.module_name:
        return []
    if pair.before.name != pair.after.name:
        return []
    if pair.similarity < 0.65:
        return []

    method_changes: list[dict[str, object]] = []
    for method_pair in matched_methods:
        if method_pair.before.class_name != pair.before.name:
            continue
        if method_pair.after.class_name != pair.after.name:
            continue
        if method_pair.before.module_name != pair.before.module_name:
            continue
        if method_pair.after.module_name != pair.after.module_name:
            continue

        assessment = _assess_method_functional_change(method_pair)
        if method_pair.before.name == method_pair.after.name:
            kind = "Move Method"
        else:
            kind = "Rename Method"

        method_changes.append(
            {
                "Kind": kind,
                "Original": method_pair.before.name,
                "Updated": method_pair.after.name,
                "Functional Change Status": assessment["status"],
                "Functional Change Reasons": assessment["reasons"],
                "Method Diff": assessment["method_diff"],
            }
        )

    class_reasons: list[str] = []
    if pair.before.bases != pair.after.bases:
        class_reasons.append("class bases changed")
    if pair.before.method_names != pair.after.method_names:
        class_reasons.append("class method set changed")
    if any(
        method_change["Functional Change Status"] == FUNCTIONAL_STATUS_CHANGED
        for method_change in method_changes
    ):
        class_reasons.append("contained methods changed behavior")

    functional_status = (
        FUNCTIONAL_STATUS_CHANGED if class_reasons else FUNCTIONAL_STATUS_NO_CHANGE
    )

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
                "Functional Change Status": functional_status,
                "Functional Change Reasons": class_reasons,
                "Method Changes": method_changes,
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

    reasons = ["class bases changed"]
    return [
        RefactoringFinding(
            refactoring_type="Change Class Signature",
            original=pair.before.qualified_name,
            updated=pair.after.qualified_name,
            location=pair.after.module_name,
            confidence=max(0.55, pair.similarity),
            details={
                "Old Bases": list(pair.before.bases),
                "New Bases": list(pair.after.bases),
                "Functional Change Status": FUNCTIONAL_STATUS_CHANGED,
                "Functional Change Reasons": reasons,
            },
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


def _moved_class_transitions(module_diff: ModuleDiff) -> set[tuple[str, str, str, str]]:
    return {
        (pair.before.module_name, pair.before.name, pair.after.module_name, pair.after.name)
        for pair in module_diff.matched_classes
        if pair.before.module_name != pair.after.module_name
        and pair.before.name == pair.after.name
        and pair.similarity >= 0.65
    }


class MoveSymbolDetector(RefactoringDetector):
    name = "move-symbol"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        """Detect symbol moves across scopes (module/class/function)."""
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_symbols:
            # Move: scope key changed (different module, class, or function context)
            same_location = (
                pair.before.scope_key == pair.after.scope_key
                and pair.before.module_name == pair.after.module_name
            )
            if same_location:
                continue
            if pair.before.name != pair.after.name:
                continue
            if pair.similarity < 0.75:
                continue

            assessment = _assess_symbol_functional_change(pair)
            old_scope_str = _format_scope_description(
                pair.before.module_name, pair.before.class_name, pair.before.function_name
            )
            new_scope_str = _format_scope_description(
                pair.after.module_name, pair.after.class_name, pair.after.function_name
            )

            findings.append(
                RefactoringFinding(
                    refactoring_type="Move Symbol",
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=pair.similarity,
                    details={
                        "Old Module": pair.before.module_name,
                        "New Module": pair.after.module_name,
                        "Old Scope": old_scope_str,
                        "New Scope": new_scope_str,
                        "Symbol Kind": pair.before.kind,
                        "Functional Change Status": assessment["status"],
                        "Functional Change Reasons": assessment["reasons"],
                        "Symbol Diff": assessment["symbol_diff"],
                        "Original Line": pair.before.lineno,
                        "Updated Line": pair.after.lineno,
                    },
                )
            )
        return findings


class RenameSymbolDetector(RefactoringDetector):
    name = "rename-symbol"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        """Detect symbol renames within the same scope."""
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_symbols:
            # Rename: same scope, different name
            if pair.before.name == pair.after.name:
                continue
            if pair.before.scope_key != pair.after.scope_key:
                continue
            if pair.before.module_name != pair.after.module_name:
                continue
            if pair.similarity < 0.75:
                continue

            assessment = _assess_symbol_functional_change(pair)
            scope_str = _format_scope_description(
                pair.before.module_name, pair.before.class_name, pair.before.function_name
            )

            findings.append(
                RefactoringFinding(
                    refactoring_type="Rename Symbol",
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=pair.similarity,
                    details={
                        "Module": pair.before.module_name,
                        "Scope": scope_str,
                        "Symbol Kind": pair.before.kind,
                        "Functional Change Status": assessment["status"],
                        "Functional Change Reasons": assessment["reasons"],
                        "Symbol Diff": assessment["symbol_diff"],
                        "Original Line": pair.before.lineno,
                        "Updated Line": pair.after.lineno,
                    },
                )
            )
        return findings


class ModifySymbolDetector(RefactoringDetector):
    name = "modify-symbol"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        """Detect symbol value changes in the same location."""
        findings: list[RefactoringFinding] = []
        for pair in module_diff.matched_symbols:
            # Modify: same name, same scope, different value
            if pair.before.name != pair.after.name:
                continue
            if pair.before.scope_key != pair.after.scope_key:
                continue
            if pair.before.module_name != pair.after.module_name:
                continue

            assessment = _assess_symbol_functional_change(pair)
            if assessment["status"] != FUNCTIONAL_STATUS_CHANGED:
                continue

            scope_str = _format_scope_description(
                pair.before.module_name, pair.before.class_name, pair.before.function_name
            )

            findings.append(
                RefactoringFinding(
                    refactoring_type="Modify Symbol",
                    original=pair.before.qualified_name,
                    updated=pair.after.qualified_name,
                    location=pair.after.module_name,
                    confidence=pair.similarity,
                    details={
                        "Module": pair.before.module_name,
                        "Scope": scope_str,
                        "Symbol Kind": pair.before.kind,
                        "Functional Change Status": assessment["status"],
                        "Functional Change Reasons": assessment["reasons"],
                        "Symbol Diff": assessment["symbol_diff"],
                        "Original Line": pair.before.lineno,
                        "Updated Line": pair.after.lineno,
                    },
                )
            )
        return findings


class AddRemoveSymbolDetector(RefactoringDetector):
    name = "add-remove-symbol"

    def detect(self, module_diff: ModuleDiff) -> list[RefactoringFinding]:
        """Report unmatched symbol additions/removals for conservative matching mode."""
        findings: list[RefactoringFinding] = []

        for removed_symbol in module_diff.removed_symbols:
            removed_scope = _format_scope_description(
                removed_symbol.module_name,
                removed_symbol.class_name,
                removed_symbol.function_name,
            )
            findings.append(
                RefactoringFinding(
                    refactoring_type="Remove Symbol",
                    original=removed_symbol.qualified_name,
                    updated="<none>",
                    location=removed_symbol.module_name,
                    confidence=1.0,
                    details={
                        "Module": removed_symbol.module_name,
                        "Scope": removed_scope,
                        "Symbol Kind": removed_symbol.kind,
                        "Original Line": removed_symbol.lineno,
                    },
                )
            )

        for added_symbol in module_diff.added_symbols:
            added_scope = _format_scope_description(
                added_symbol.module_name,
                added_symbol.class_name,
                added_symbol.function_name,
            )
            findings.append(
                RefactoringFinding(
                    refactoring_type="Add Symbol",
                    original="<none>",
                    updated=added_symbol.qualified_name,
                    location=added_symbol.module_name,
                    confidence=1.0,
                    details={
                        "Module": added_symbol.module_name,
                        "Scope": added_scope,
                        "Symbol Kind": added_symbol.kind,
                        "Updated Line": added_symbol.lineno,
                    },
                )
            )

        return findings


def _format_scope_description(
    module_name: str, class_name: str | None, function_name: str | None
) -> str:
    """Format a scope description for display."""
    if class_name is not None and function_name is not None:
        return f"{module_name}:{class_name}.{function_name}"
    if class_name is not None:
        return f"{module_name}:{class_name}"
    if function_name is not None:
        return f"{module_name}:{function_name}"
    return module_name


def _assess_symbol_functional_change(
    pair: MatchedSymbol,
) -> dict[str, object]:
    """Assess whether a symbol change is functional.
    
    Only the actual value/signature change counts as functional change.
    Scope level changes (e.g., moving from module to class) are structural,
    not functional, and are already captured in the "Move Symbol" finding.
    """
    reasons: list[str] = []

    # Value signature changed (content change)
    if pair.before.value_signature != pair.after.value_signature:
        reasons.append("symbol value changed")

    status = FUNCTIONAL_STATUS_CHANGED if reasons else FUNCTIONAL_STATUS_NO_CHANGE
    symbol_diff = _build_symbol_diff(pair, status) if reasons else None

    return {
        "status": status,
        "reasons": reasons,
        "symbol_diff": symbol_diff,
    }


def _build_symbol_diff(pair: MatchedSymbol, status: str) -> str | None:
    """Build a condensed diff showing before/after symbol source."""
    if status != FUNCTIONAL_STATUS_CHANGED:
        return None

    before_source = textwrap.dedent(pair.before.source).strip("\n")
    after_source = textwrap.dedent(pair.after.source).strip("\n")

    before_loc = f"{pair.before.module_name}:{pair.before.lineno}"
    after_loc = f"{pair.after.module_name}:{pair.after.lineno}"
    lines = [
        f"@@ {before_loc} -> {after_loc} @@",
    ]

    for source_line in before_source.splitlines() or [""]:
        lines.append(f"- {source_line}")
    for source_line in after_source.splitlines() or [""]:
        lines.append(f"+ {source_line}")

    return "\n".join(lines)


def _assess_method_functional_change(pair: MatchedMethod) -> dict[str, object]:
    reasons: list[str] = []
    if pair.before.body_signature != pair.after.body_signature:
        reasons.append("method body changed")
    if pair.before.params != pair.after.params:
        reasons.append("method parameters changed")
    if pair.before.called_names != pair.after.called_names:
        reasons.append("called symbols changed")

    status = FUNCTIONAL_STATUS_CHANGED if reasons else FUNCTIONAL_STATUS_NO_CHANGE
    method_diff: str | None = None
    if status == FUNCTIONAL_STATUS_CHANGED:
        method_diff = _build_condensed_method_diff(
            _normalize_method_source_for_diff(pair.before.source),
            _normalize_method_source_for_diff(pair.after.source),
        )
    return {
        "status": status,
        "reasons": reasons,
        "method_diff": method_diff,
    }


def _normalize_method_source_for_diff(source: str) -> str:
    """Normalize leading indentation so scope moves don't create noisy diffs."""
    return textwrap.dedent(source)


def _build_condensed_method_diff(
    before_source: str,
    after_source: str,
    *,
    context_lines: int = 1,
    max_lines: int = 24,
) -> str | None:
    diff_lines = list(
        difflib.unified_diff(
            before_source.splitlines(),
            after_source.splitlines(),
            lineterm="",
            n=context_lines,
        )
    )
    if not diff_lines:
        return None

    # Skip file header lines so only method-scoped hunks are shown.
    if len(diff_lines) >= 2 and diff_lines[0].startswith("---") and diff_lines[1].startswith("+++"):
        diff_lines = diff_lines[2:]

    if len(diff_lines) > max_lines:
        kept = max_lines - 1
        diff_lines = diff_lines[:kept] + ["... (diff truncated)"]

    return "\n".join(diff_lines)
