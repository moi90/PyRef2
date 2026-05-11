# PyRef2

[![PyPI version](https://img.shields.io/pypi/v/pyref2.svg)](https://pypi.org/project/pyref2/)

PyRef2 is based on the core idea behind [PyRef](https://github.com/PyRef/PyRef): automatically detecting refactorings in Python code. It extends that idea with a typed Python 3.13 codebase, direct Git revision analysis, structured JSON and Markdown reporting, hierarchical change summaries, and explicit functional-change detection for both refactoring-related and standalone behavior changes.

Use it when you need a fast, review-friendly report for questions like:

- What was renamed, moved, extracted, inlined, or signature-changed between two revisions?
- Did any of those findings also change method/class behavior?
- Were there behavior changes that are not simple rename/move operations?

It is designed for CI checks, release reviews, and repository archaeology.

## Install and run in 60 seconds

Install from PyPI:

```bash
python -m pip install pyref2
```

Or with uv:

```bash
uv tool install pyref2
```

Then run:

```bash
pyref2 analyze-revisions --repo path/to/repo origin/main..HEAD --format markdown
```

What you get:

- machine-readable JSON findings (default)
- optional Markdown report grouped by change type and scope
- per-finding functional-change status
- condensed method-level code diffs when a functional change is detected

## How to read the output

- `No Functional Change` means PyRef2 did not find structural behavior signals for the compared entity.
- `Functional Change Detected` means at least one behavior signal changed and the report includes reasons.
- Markdown reports group findings into module-level changes, class-wise changes, mixed-scope method changes, and other refactorings.

## Architecture overview

PyRef2 uses a small layered pipeline so each stage stays testable and replaceable:

- Parsing layer (`core/ast_analysis.py`): converts Python source into typed entities (`ModuleEntity`, `ClassEntity`, `MethodEntity`).
- Diff layer (`core/diff_engine.py`): matches entities between revisions and produces a structural `ModuleDiff`.
- Detection layer (`core/detectors/`): runs focused heuristic detectors (rename/extract/inline/move/signature changes).
- Service layer (`service.py`): orchestrates parse → diff → detect and returns sorted findings.
- Interface layer (`cli/commands.py`): exposes `analyze-files` and emits schema-versioned JSON output.

## How functional changes are detected

PyRef2 reports functional-change status using static structural checks for move-related and non-move findings.

### Method-level checks

For method comparisons, PyRef2 marks `Functional Change Detected` when any of these differ between before/after revisions:

- `body_signature`: normalized AST statement signatures for the method body
- `params`: method parameter tuple
- `called_names`: set of called symbol names detected in the method body

If none of those differ, status is `No Functional Change`.

These method-level checks are used by:

- Move Method
- Rename Method
- Modify Method (same name, same scope, same module, but behavior changed)
- Change Method Signature
- Extract Method (assesses whether the source caller changed)
- Inline Method (assesses whether the destination caller changed)

### Class-level checks

For class moves, PyRef2 combines class-level and member-level signals:

- class bases changed
- class method-name set changed
- any contained matched method is marked `Functional Change Detected`

If none of the above is true, class status is `No Functional Change`.

For class signature changes (for example, base-class changes), PyRef2 reports `Functional Change Detected` with reasons when the class signature differs.

### Symbol-level checks

For module-level and class-level non-method symbols (variables and constants), PyRef2 detects moves, renames, and value changes:

- `Move Symbol`: symbol appears in a different scope or module (e.g., module-level to class-level, or from one module to another)
- `Rename Symbol`: symbol name changed within the same scope
- `Modify Symbol`: symbol value changed in the same location

Functional-change status for symbols is determined by:

- `value_signature`: normalized AST signature of the assignment's right-hand side
- `scope_level`: nesting context (module-level vs. class-level vs. function-scoped)

If value signature OR scope level changed, status is `Functional Change Detected`. Otherwise, `No Functional Change`.

Note: moving a symbol to a different module does NOT by itself mark it as a functional change unless the value also changed or the nesting context changed (e.g., module-level to class-level).

### Reporting behavior

- Move-related and non-move behavior findings include a functional-change status in JSON and Markdown.
- In Markdown, same-name method entries are suppressed unless status is `Functional Change Detected`.
- Class entries can include child method changes used to justify class-level status.
- When status is `Functional Change Detected`, Markdown includes a condensed unified code diff scoped to the relevant method.

### Handled symbol-move cases

PyRef2 detects and reports the following symbol-move transitions:

| Case | Example | Detected As |
|------|---------|-------------|
| Module-level rename (same file) | `DEBUG` → `VERBOSE` in `config.py` | Rename Symbol |
| Module-level move (different file) | `DEBUG` in `config_a.py` → `config_b.py` | Move Symbol |
| Module to class move | `TIMEOUT` (module) → `TIMEOUT` (class body) | Move Symbol |
| Module to function move | `COUNTER` (module) → `COUNTER` (function body) | Move Symbol |
| Class to module move | `TIMEOUT` (class body) → `TIMEOUT` (module) | Move Symbol |
| Class to function move | `SETTING` (class body) → `SETTING` (method body) | Move Symbol |
| Function to module move | `TEMP` (function body) → `TEMP` (module) | Move Symbol |
| Function to class move | `TEMP` (function body) → `TEMP` (class body) | Move Symbol |
| Same-location value change | `TIMEOUT = 30` → `TIMEOUT = 60` (same file/scope) | Modify Symbol |

### Current limitations

This is a static heuristic, not dynamic execution equivalence. It does not guarantee runtime equivalence in all cases. In particular, behavior can still change through effects not captured by the current signals (for example, external state interactions or semantics-preserving AST rewrites that alter call-name sets).

**Symbols scope**: Currently, PyRef2 only tracks module-level and class-level non-method symbols (variables and constants). Function/method-local symbols and imports are not tracked. Tuple unpacking assignments (e.g., `x, y = ...`) are also not currently supported; only simple-name targets are extracted.

## Quickstart

```bash
uv sync --extra dev
uv run pyref2 analyze-files --before path/to/old.py --after path/to/new.py
uv run pyref2 analyze-tree --before-root path/to/revision-A --after-root path/to/revision-B
uv run pyref2 analyze-revisions --repo path/to/repo origin/main..HEAD
uv run pyref2 analyze-revisions --repo path/to/repo HEAD
uv run pyref2 analyze-revisions --repo path/to/repo
uv run pyref2 analyze-revisions --format markdown --repo path/to/repo origin/main..HEAD
```

## Git revision analysis

Use `analyze-revisions` to compare repository states directly from Git without exporting trees by hand.

- Pass a standard Git double-dot range: `uv run pyref2 analyze-revisions --repo path/to/repo origin/main..HEAD`
- Pass a single commit to analyze only what that commit introduced: `uv run pyref2 analyze-revisions --repo path/to/repo HEAD`
- Omit the revision argument to analyze current working tree changes against `HEAD`: `uv run pyref2 analyze-revisions --repo path/to/repo`
- `main..feature` means: analyze the total effect between the tree at `main` and the tree at `feature`, which matches the common feature-branch review workflow.
- Add `--format markdown` to get a developer-oriented report grouped by refactoring type.

## Tree test fixtures

Whole-tree regression tests live under `tests/source_trees/` and use this layout:

- `<test-name>/revision-A/`
- `<test-name>/revision-B/`

This keeps it easy to add a new before/after source tree pair whenever a bug needs a permanent fixture.

## Documentation conventions

- Use Google-style docstrings for public Python modules, classes, and functions.
