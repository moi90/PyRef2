# Report Showcase Fixture

This fixture contains two synthetic revisions to exercise every section of the
PyRef2 markdown report.

## Layout

- revision-A/
- revision-B/

## Run

From the PyRef2 repository root:

uv run pyref2 analyze-tree \
  --before-root examples/report_showcase/revision-A \
  --after-root examples/report_showcase/revision-B \
  --format markdown

## Intended coverage

- Module-Level Function Moves/Renames: top-level function rename
- Class-Wise Changes: class moved from models.py to domain.py
- Mixed Scope Method Changes: function moved to class method with behavior change
- Symbol Moves: module-level symbol moved into class scope
- Symbol Renames: module-level symbol rename
- Added Symbols: unmatched symbol added
- Removed Symbols: unmatched symbol removed
- Other Refactorings: modify symbol and/or method signature findings
