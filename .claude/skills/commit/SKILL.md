---
name: commit
description: Run checks then commit changes. Use when committing code to the ox project.
---

Run all checks before committing. **All must pass.**

## Workflow

1. Run checks:

```bash
make check
```

This runs lint, format check, type check, and tests.

2. If checks fail, fix the issues:
   - `uv run ruff check --fix src/ tests/` for auto-fixable lint issues
   - `uv run ruff format src/ tests/` for formatting
   - Fix type errors and test failures manually
   - Re-run `make check` until clean

3. Review changes:

```bash
git status
git diff
```

4. Stage and commit:

```bash
git add <files>
git commit -m "Short description of the change"
```

## Commit Message Style

- Imperative mood: "Add feature" not "Added feature"
- First line under 72 characters
- Prefix with context when helpful: `Fix`, `Add`, `Update`, `Remove`

## What Not to Commit

- `.ox/metrics/` output (gitignored)
- Virtual environments
- Secrets or credentials

## Quick Reference

```bash
make check && git add <files> && git commit -m "message"
```
