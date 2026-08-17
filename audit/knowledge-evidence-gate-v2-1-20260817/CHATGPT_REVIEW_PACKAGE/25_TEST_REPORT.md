# Test report

Canonical test scope is the repository `tests/` directory, matching CI.

- `python -m compileall -q pipeline tests`: **PASS**
- `python -m pytest -q tests`: **49 passed, 0 failed, 0 skipped**
- Collection: **49**

The repository also contains historical, untracked audit snapshots with their own test files. They are not part of the CI test path; unrestricted pytest collection of those snapshots is intentionally excluded from the canonical command because those snapshots depend on their original local package layout.
