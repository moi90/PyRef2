## Anonymization Policy For External Examples

When adding regression tests or documentation examples derived from external repositories, always anonymize all identifying names.

Use neutral placeholders:
- Paths and directories: `foo`, `bar`, `pkg`, `src`, `tests`
- File names: `alpha.py`, `beta.py`, `gamma.py`
- Symbols: `helper`, `transform_item`, `old_name`, `new_name`

Do not keep concrete references to third-party projects in committed code, tests, docs, or snapshots, including:
- Organization or project names
- Domain-specific module/file names
- Real function/class names from external codebases

If an example is imported from a real case, preserve only the structural pattern (move, rename, extract, etc.), not the original identifiers.