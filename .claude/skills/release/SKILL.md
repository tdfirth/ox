---
name: release
description: Cut a new release of ox. Bumps version, runs checks, commits, tags, and creates a GitHub release which triggers PyPI publish.
argument-hint: "[version]"
---

Cut a release for ox. The argument is the new version (e.g. `0.2.0`).

## Workflow

1. **Validate the version argument.** It must be valid semver (e.g. `0.2.0`). Confirm it's newer than the current version in `pyproject.toml`.

2. **Run all checks:**

```bash
make check
```

All must pass before proceeding.

3. **Bump the version** in `pyproject.toml`:

Update the `version = "..."` line under `[project]` to the new version.

4. **Commit the version bump:**

```bash
git add pyproject.toml
git commit -m "Release v<version>"
```

5. **Push to remote:**

```bash
git push
```

6. **Wait for CI to pass.** Check with:

```bash
gh run list --limit 1
gh run watch
```

Do not proceed if CI fails — fix issues first.

7. **Create the GitHub release:**

```bash
gh release create v<version> --generate-notes --title "v<version>"
```

This triggers the `publish.yml` workflow which builds and publishes to PyPI.

8. **Verify the publish workflow started:**

```bash
gh run list --workflow=publish.yml --limit 1
```

## Important

- Always run `make check` before releasing
- Always wait for CI to pass after pushing the version bump
- The GitHub release triggers PyPI publish via trusted publishing — no tokens needed
- Use `--generate-notes` to auto-generate release notes from commits since the last release
