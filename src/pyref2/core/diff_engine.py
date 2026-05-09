"""Compute structural diffs between two parsed module revisions.

Matching uses a two-stage strategy: preserve obvious identity pairs first,
then match remaining entities by similarity to support rename/move detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from pyref2.models.code_elements import ClassEntity, MethodEntity, ModuleEntity


@dataclass(frozen=True, slots=True)
class MatchedMethod:
    before: MethodEntity
    after: MethodEntity
    similarity: float


@dataclass(frozen=True, slots=True)
class MatchedClass:
    before: ClassEntity
    after: ClassEntity
    similarity: float


@dataclass(frozen=True, slots=True)
class ModuleDiff:
    matched_methods: tuple[MatchedMethod, ...]
    added_methods: tuple[MethodEntity, ...]
    removed_methods: tuple[MethodEntity, ...]
    matched_classes: tuple[MatchedClass, ...]
    added_classes: tuple[ClassEntity, ...]
    removed_classes: tuple[ClassEntity, ...]


def diff_modules(before: ModuleEntity, after: ModuleEntity) -> ModuleDiff:
    """Return matched/added/removed entities for methods and classes."""
    matched_methods, added_methods, removed_methods = _match_methods(before.methods, after.methods)
    matched_classes, added_classes, removed_classes = _match_classes(before.classes, after.classes)

    return ModuleDiff(
        matched_methods=matched_methods,
        added_methods=added_methods,
        removed_methods=removed_methods,
        matched_classes=matched_classes,
        added_classes=added_classes,
        removed_classes=removed_classes,
    )


def _match_methods(
    before_methods: tuple[MethodEntity, ...],
    after_methods: tuple[MethodEntity, ...],
) -> tuple[tuple[MatchedMethod, ...], tuple[MethodEntity, ...], tuple[MethodEntity, ...]]:
    matched: list[MatchedMethod] = []
    used_before: set[int] = set()
    used_after: set[int] = set()

    # First pass: preserve stable identities by method name and scope.
    for before_index, old_method in enumerate(before_methods):
        for after_index, new_method in enumerate(after_methods):
            if after_index in used_after:
                continue
            if old_method.name != new_method.name:
                continue
            if old_method.class_name != new_method.class_name:
                continue

            score = method_similarity(old_method, new_method)
            if score < 0.3:
                continue

            used_before.add(before_index)
            used_after.add(after_index)
            matched.append(
                MatchedMethod(
                    before=old_method,
                    after=new_method,
                    similarity=score,
                )
            )
            break

    for before_index, old_method in enumerate(before_methods):
        if before_index in used_before:
            continue

        best_index = -1
        best_score = 0.0

        # Second pass: find best candidate even if identity changed (rename/move).
        for idx, new_method in enumerate(after_methods):
            if idx in used_after:
                continue
            score = method_similarity(old_method, new_method)
            if score > best_score:
                best_score = score
                best_index = idx

        if best_index >= 0 and best_score >= 0.6:
            used_before.add(before_index)
            used_after.add(best_index)
            matched.append(
                MatchedMethod(
                    before=old_method,
                    after=after_methods[best_index],
                    similarity=best_score,
                )
            )

    removed = tuple(method for idx, method in enumerate(before_methods) if idx not in used_before)
    added = tuple(
        method
        for idx, method in enumerate(after_methods)
        if idx not in used_after
    )

    return tuple(matched), added, removed


def _match_classes(
    before_classes: tuple[ClassEntity, ...],
    after_classes: tuple[ClassEntity, ...],
) -> tuple[tuple[MatchedClass, ...], tuple[ClassEntity, ...], tuple[ClassEntity, ...]]:
    matched: list[MatchedClass] = []
    used_after: set[int] = set()

    for old_class in before_classes:
        best_index = -1
        best_score = 0.0

        for idx, new_class in enumerate(after_classes):
            if idx in used_after:
                continue
            score = class_similarity(old_class, new_class)
            if score > best_score:
                best_score = score
                best_index = idx

        if best_index >= 0 and best_score >= 0.5:
            used_after.add(best_index)
            matched.append(
                MatchedClass(
                    before=old_class,
                    after=after_classes[best_index],
                    similarity=best_score,
                )
            )

    removed = tuple(
        class_entity
        for class_entity in before_classes
        if all(pair.before != class_entity for pair in matched)
    )
    added = tuple(
        class_entity
        for idx, class_entity in enumerate(after_classes)
        if idx not in used_after
    )

    return tuple(matched), added, removed


def method_similarity(old: MethodEntity, new: MethodEntity) -> float:
    """Heuristic similarity score aligned with RefDiff-style weighting ideas."""
    body_old = "\n".join(old.body_signature)
    body_new = "\n".join(new.body_signature)
    body_ratio = SequenceMatcher(None, body_old, body_new).ratio()

    params_ratio = SequenceMatcher(None, " ".join(old.params), " ".join(new.params)).ratio()
    scope_bonus = 0.1 if old.class_name == new.class_name else 0.0
    name_bonus = 0.1 if old.name == new.name else 0.0

    return min(1.0, 0.75 * body_ratio + 0.15 * params_ratio + scope_bonus + name_bonus)


def class_similarity(old: ClassEntity, new: ClassEntity) -> float:
    methods_old = " ".join(old.method_names)
    methods_new = " ".join(new.method_names)
    method_ratio = SequenceMatcher(None, methods_old, methods_new).ratio()

    bases_old = " ".join(old.bases)
    bases_new = " ".join(new.bases)
    bases_ratio = SequenceMatcher(None, bases_old, bases_new).ratio()

    name_bonus = 0.2 if old.name == new.name else 0.0
    return min(1.0, 0.65 * method_ratio + 0.15 * bases_ratio + name_bonus)
