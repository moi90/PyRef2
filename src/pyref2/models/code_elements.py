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
    source: str = ""  # Full class source code for detailed comparison

    @property
    def qualified_name(self) -> str:
        return f"{self.module_name}.{self.name}"


@dataclass(frozen=True, slots=True)
class SymbolEntity:
    """Represents a module/class/function-level assignment symbol (variable or constant)."""

    name: str
    module_name: str
    class_name: str | None  # None if module-level or function-level only
    function_name: str | None  # None if module-level or class-level only
    lineno: int
    end_lineno: int
    source: str
    kind: str  # 'variable' or 'constant'
    value_signature: str  # Normalized ast.dump of RHS for similarity matching

    @property
    def qualified_name(self) -> str:
        """Return fully qualified name for the symbol."""
        parts = [self.module_name]
        if self.class_name is not None:
            parts.append(self.class_name)
        if self.function_name is not None:
            parts.append(self.function_name)
        parts.append(self.name)
        return ".".join(parts)

    @property
    def scope_key(self) -> tuple[str, str | None, str | None]:
        """Return scope context as tuple: (module, class, function)."""
        return (self.module_name, self.class_name, self.function_name)

    @property
    def scope_level(self) -> tuple[str | None, str | None]:
        """Return only nesting level (class, function), excluding module path."""
        return (self.class_name, self.function_name)


@dataclass(frozen=True, slots=True)
class ModuleEntity:
    """Represents parsed entities from one module revision."""

    name: str
    methods: tuple[MethodEntity, ...]
    classes: tuple[ClassEntity, ...]
    symbols: tuple[SymbolEntity, ...] = field(default_factory=tuple)
