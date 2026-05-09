from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MethodEntity:
    """Represents a top-level or class method in a module revision."""

    name: str
    module_name: str
    class_name: str | None
    params: tuple[str, ...]
    lineno: int
    end_lineno: int
    source: str
    body_signature: tuple[str, ...]
    called_names: frozenset[str] = field(default_factory=frozenset)

    @property
    def qualified_name(self) -> str:
        if self.class_name is None:
            return f"{self.module_name}.{self.name}"
        return f"{self.module_name}.{self.class_name}.{self.name}"


@dataclass(frozen=True, slots=True)
class ClassEntity:
    """Represents a class declaration in a module revision."""

    name: str
    module_name: str
    bases: tuple[str, ...]
    lineno: int
    end_lineno: int
    method_names: tuple[str, ...]

    @property
    def qualified_name(self) -> str:
        return f"{self.module_name}.{self.name}"


@dataclass(frozen=True, slots=True)
class ModuleEntity:
    """Represents parsed entities from one module revision."""

    name: str
    methods: tuple[MethodEntity, ...]
    classes: tuple[ClassEntity, ...]
