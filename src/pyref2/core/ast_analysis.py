"""Convert Python source text into stable, typed entities for diffing.

This module intentionally keeps extraction lightweight: it records structure,
signatures, and call names, but does not attempt semantic interpretation.
"""

from __future__ import annotations

import ast

from pyref2.exceptions import ParseError
from pyref2.models.code_elements import ClassEntity, MethodEntity, ModuleEntity, SymbolEntity


class _CallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.called_names: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = _call_name(node.func)
        if name is not None:
            self.called_names.add(name)
        self.generic_visit(node)


def parse_module(source: str, module_name: str) -> ModuleEntity:
    """Parse source code into a module entity.

    Raises ParseError if the source cannot be parsed.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ParseError(f"Failed to parse module '{module_name}': {exc}") from exc

    methods: list[MethodEntity] = []
    classes: list[ClassEntity] = []
    symbols: list[SymbolEntity] = []

    # Single pass over module-level nodes to collect top-level, class members, and symbols.
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_method_from_function(node, source, module_name, class_name=None))
        elif isinstance(node, ast.ClassDef):
            classes.append(_class_from_node(node, source, module_name))
            for class_item in node.body:
                if isinstance(class_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(
                        _method_from_function(class_item, source, module_name, class_name=node.name)
                    )
                elif isinstance(class_item, (ast.Assign, ast.AnnAssign)):
                    symbols.extend(
                        _symbols_from_assignment(
                            class_item,
                            source,
                            module_name,
                            class_name=node.name,
                            function_name=None,
                        )
                    )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            symbols.extend(
                _symbols_from_assignment(
                    node, source, module_name, class_name=None, function_name=None
                )
            )

    return ModuleEntity(
        name=module_name, methods=tuple(methods), classes=tuple(classes), symbols=tuple(symbols)
    )


def _class_from_node(node: ast.ClassDef, source: str, module_name: str) -> ClassEntity:
    method_names = tuple(
        item.name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    bases = tuple(_expr_to_name(base) for base in node.bases)
    
    # Extract class source code for detailed comparison
    source_lines = source.splitlines(keepends=True)
    start_line = getattr(node, "lineno", 1) - 1  # Convert to 0-based
    end_line = getattr(node, "end_lineno", getattr(node, "lineno", 1))  # Inclusive
    class_source = "".join(source_lines[start_line:end_line])
    
    return ClassEntity(
        name=node.name,
        module_name=module_name,
        bases=bases,
        lineno=getattr(node, "lineno", 1),
        end_lineno=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
        method_names=method_names,
        source=class_source,
    )


def _method_from_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
    module_name: str,
    class_name: str | None,
) -> MethodEntity:
    # The body signature is a normalized snapshot used by similarity scoring.
    params = tuple(arg.arg for arg in node.args.args)
    body_signature = tuple(_statement_signature(stmt) for stmt in node.body)

    collector = _CallCollector()
    collector.visit(node)

    return MethodEntity(
        name=node.name,
        module_name=module_name,
        class_name=class_name,
        params=params,
        lineno=getattr(node, "lineno", 1),
        end_lineno=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
        source=_source_segment(
            source,
            getattr(node, "lineno", 1),
            getattr(node, "end_lineno", getattr(node, "lineno", 1)),
        ),
        body_signature=body_signature,
        called_names=frozenset(collector.called_names),
    )


def _source_segment(source: str, lineno: int, end_lineno: int) -> str:
    lines = source.splitlines()
    start_index = max(0, lineno - 1)
    end_index = max(start_index, end_lineno)
    return "\n".join(lines[start_index:end_index]).rstrip()


def _statement_signature(stmt: ast.stmt) -> str:
    return ast.dump(stmt, annotate_fields=False, include_attributes=False)


def _expr_to_name(expr: ast.expr) -> str:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return ast.dump(expr, annotate_fields=False, include_attributes=False)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def module_from_file(path: str, module_name: str | None = None) -> ModuleEntity:
    """Load a Python file and parse it into a module entity."""
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return parse_module(source, module_name=module_name or path)


def _symbol_kind_from_name(name: str) -> str:
    """Classify a symbol as 'constant' (UPPER_CASE) or 'variable'."""
    if name.isupper() and "_" in name:
        return "constant"
    if name.isupper():
        return "constant"
    return "variable"


def _value_signature_from_expr(expr: ast.expr) -> str:
    """Normalize an expression to a signature for similarity matching."""
    return ast.dump(expr, annotate_fields=False, include_attributes=False)


def _symbols_from_assignment(
    node: ast.Assign | ast.AnnAssign,
    source: str,
    module_name: str,
    class_name: str | None,
    function_name: str | None,
) -> list[SymbolEntity]:
    """Extract symbols from an assignment node in the given scope."""
    symbols: list[SymbolEntity] = []

    # Get the RHS value and normalize it.
    if isinstance(node, ast.AnnAssign):
        if node.value is None:
            # Type annotation without assignment (e.g., x: int) is not included.
            return symbols
        value_expr = node.value
        targets = [node.target] if isinstance(node.target, ast.Name) else []
    else:  # ast.Assign
        value_expr = node.value
        targets = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append(target)
            # Note: tuple unpacking and multi-target assignments are skipped for now.

    value_signature = _value_signature_from_expr(value_expr)

    # Extract symbol names and create entities.
    for target in targets:
        if not isinstance(target, ast.Name):
            continue

        symbol_name = target.id
        kind = _symbol_kind_from_name(symbol_name)

        symbol = SymbolEntity(
            name=symbol_name,
            module_name=module_name,
            class_name=class_name,
            function_name=function_name,
            lineno=getattr(node, "lineno", 1),
            end_lineno=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            source=_source_segment(
                source,
                getattr(node, "lineno", 1),
                getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            ),
            kind=kind,
            value_signature=value_signature,
        )
        symbols.append(symbol)

    return symbols
