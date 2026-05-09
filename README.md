# PyRef2

PyRef2 is the Python 3.13 successor to PyRef.

The project detects source-code refactorings across revisions with a typed, testable architecture inspired by modern refactoring research patterns.

## Current status

- Python 3.13-ready package scaffold
- Typed core models for modules, classes, methods, and findings
- AST extraction and revision differencing
- MVP detector set for method and class signature changes
- CLI commands for local file comparisons

## Architecture overview

PyRef2 uses a small layered pipeline so each stage stays testable and replaceable:

- Parsing layer (`core/ast_analysis.py`): converts Python source into typed entities (`ModuleEntity`, `ClassEntity`, `MethodEntity`).
- Diff layer (`core/diff_engine.py`): matches entities between revisions and produces a structural `ModuleDiff`.
- Detection layer (`core/detectors/`): runs focused heuristic detectors (rename/extract/inline/move/signature changes).
- Service layer (`service.py`): orchestrates parse → diff → detect and returns sorted findings.
- Interface layer (`cli/commands.py`): exposes `analyze-files` and emits schema-versioned JSON output.

## Quickstart

```bash
uv sync --extra dev
uv run pyref2 analyze-files --before path/to/old.py --after path/to/new.py
```
