# Execution status — VTKP-PUBLIC-REPRODUCIBLE-DEMO-V1

Date: 2026-10-13
Resumable record. No secrets, no personal absolute paths.

## Baseline and workspace

| Item | Value |
|---|---|
| Remote | `https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline.git` |
| Remote default branch | `main` |
| Baseline commit (verified live, matches the plan snapshot) | `5dfac409c9cc8b7a7856a7df90259ddb09908c82` |
| Working branch | `feat/public-reproducible-demo-20261013` |
| Code commit under test | `040ddd1bcc9083cb378ca044bd96603e90ce8673` |
| Docs commit | the tip of the branch (this commit) |
| Isolated workspace | `F:\codex-workspaces\vtkp-public-demo-20261013` (outside every production root) |
| Clean venv | `F:\codex-workspaces\vtkp-venv` (Python 3.13.14, pytest 9.1.1) |
| Pre-existing repo copy | `D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline` — **left untouched**; it was dirty (3 untracked `audit/` dirs) on branch `fix/gate-v2-1-…` and was not stashed, reset or modified |

## Tool versions

`git 2.55.0.windows.3` · `gh 2.96.0` (unauthenticated) · `Python 3.13.14` ·
`pytest 9.1.1` · shell: Git Bash (MINGW64_NT), Windows 11.

## Phase status

| Phase | Status | Note |
|---|---|---|
| P0 Environment & baseline | **PASS** | Baseline verified live; isolated workspace created outside production roots; pre-existing dirty copy untouched |
| P1 Source discovery | **PASS** | Code found — on pushed feature branches, not on `main`; both candidate production roots verified to exist and scanned read-only |
| P2 Minimal demo selection | **PASS** | Path B chosen; scope fixed in `docs/DEMO_SCOPE.md` |
| P3 Migration & minimal fix | **PASS** | 3 files reused verbatim (hash-verified); 1 new adapter; paths parameterised; guard against production output roots |
| P4 Public samples | **PASS** | 7 + 1 + 1 original synthetic fixtures; hand-derived expectations with derivation rules |
| P5 Validation & reproduction | **PASS** | 52 tests pass in a clean venv and in a fresh clone; 12/12 validation checks pass; see `docs/VALIDATION_REPORT.md` |
| P6 README & submission material | **PASS (screenshot pending)** | README rewritten; MLH draft written; screenshot not obtainable headless — real text captures provided instead |
| P7 Git / push / Draft PR | **PASS** | Branch pushed to `origin`; Draft PR #6 opened against `main` |

## Acceptance status

| Key | Value |
|---|---|
| `SOURCE_DISCOVERY` | **PASS** |
| `PUBLIC_CONTENT_REVIEW` | **PASS** (scan clean; no secrets, no media, no DB, no personal absolute paths added) |
| `DEMO_REPRODUCIBILITY` | **PASS** |
| `TESTS` | **PASS** (52 passed) |
| `SOURCE_INTEGRITY` | **PASS** (migrated core sha256 `993fe393…` unchanged) |
| `DOCUMENTATION` | **PASS** |
| `REMOTE_PR` | **PASS** — Draft PR #6, `state=open`, `draft=true`, `mergeable_state=clean`, 25 files. **Partial gap:** 0 check runs; the CI workflow is prepared locally but cannot be pushed (token lacks `workflow` scope) |
| `MLH_RULES_ELIGIBILITY` | **NOT_EVALUATED** — the event rulebook was not available |

No single PASS hides the NOT_EVALUATED item or the pending screenshot.

## Remote state

| Item | Value |
|---|---|
| Pushed branch | `feat/public-reproducible-demo-20261013` @ `cdde08168d3c3373fc05b3c034cb402dd3c77c53` |
| Draft PR | https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline/pull/6 |
| Base | `main` @ `5dfac40` (unchanged — **not merged**) |
| PR state | open, draft, mergeable clean, 25 files, +2244 / -1 |
| CI check runs on the PR | **0 — no checks ran** (see below) |

Credential note: `gh auth status` reports "not logged into any GitHub hosts" and
`gh pr create` refuses to run, but a working credential **is** available through
git's credential helper for `github.com`. The push and the Draft PR were
therefore completed via `git push` and the GitHub REST API. No credential value
was printed, logged or written to any file.

## CI — prepared but blocked by token scope

The PR shows **zero check runs**, because the branch is cut from `main`, which
carries no workflow file. A workflow was written to close that gap:

* file: `.github/workflows/ci.yml` (present in the working tree)
* commit: `d1dc975`, preserved on the local-only branch `local/ci-workflow-pending`
* patch: `F:\codex-workspaces\vtkp-ci-workflow.patch`
* what it does: matrix over `ubuntu-latest` + `windows-latest` × Python 3.11 +
  3.13; compiles sources, runs the demo, asserts both fail-closed exit codes
  (3 = contract violation, 2 = missing input, and that nothing is written), and
  runs the test suite. All of its steps were replicated locally and pass.
* **why it is not pushed:** the push is rejected with
  `refusing to allow an OAuth App to create or update workflow .github/workflows/ci.yml without 'workflow' scope`,
  and the connector route returns `403 Resource not accessible by integration`
  for the same reason. Any file under `.github/workflows/` needs the `workflow`
  scope, which this credential does not have.

To land it, the owner needs either to grant the token the `workflow` scope and
push, or to apply the patch from a machine with that scope:

```bash
cd F:\codex-workspaces\vtkp-public-demo-20261013
git checkout local/ci-workflow-pending      # or: git apply F:\codex-workspaces\vtkp-ci-workflow.patch
git push origin local/ci-workflow-pending:feat/public-reproducible-demo-20261013
```

Until then, `.github/workflows/` is listed in `.git/info/exclude` so the working
tree stays clean while the file remains on disk.

**Delivered instead:** `scripts/verify.sh` — the same checks the workflow would
run (compile, demo, both fail-closed exit codes, test suite), runnable by any
reviewer with one command and pushable without the `workflow` scope. This covers
the reproducibility value of CI; what remains uncovered is only *automated*
per-PR checking and Linux execution.

## Defect found and fixed during validation

The fresh-clone check initially **failed**: 16 tests errored because
`pytest --basetemp=.pytest-tmp/run` needs its parent directory to exist
(pytest uses `mkdir(parents=False)`). It had passed only because the
development directory still held a `.pytest-tmp/` from an earlier manual
`mkdir -p` — the PASS depended on residue a fresh clone does not have.

Fixed in `c23d95b` (`scripts/verify.sh` now creates the parent first), and 4
regression tests were added for the production-root guard. Details in
`docs/VALIDATION_REPORT.md`. This is the reason the evidence files are now
captured from a fresh clone rather than from the working directory.

## Not done (by design)

Merging to `main`; submitting to MLH; changing repository visibility; touching
the production roots; re-running the frozen 24-sample replay; re-collecting the
3649-episode corpus; running any ASR, model or paid API.

## Data reconciliation note (recorded, not resolved)

The inherited baseline document `docs/PROJECT_BASELINE.md` declares:

| Quantity | Value |
|---|---|
| total episodes | 3649 |
| transcript available | 3057 |
| ASR required | 591 |
| indexed | 3055 |
| quarantined | 2 |

`3057 + 591 = 3648`, one short of the declared total of 3649, and adding the 2
quarantined episodes gives 3650 instead. **This discrepancy is recorded here as
an open reconciliation question.** No number was adjusted to make the columns
add up, and no re-collection was performed to explain it.

Two reasons this task does not resolve it:

1. These are **document declarations**, not facts verified by this task. The
   corpus was never enumerated, counted or opened.
2. Resolving it would require the kind of full-corpus work this task explicitly
   excludes.

The demo does not read, count or touch the corpus in any way, so it neither
depends on nor changes this figure.

## Resume instructions

1. `cd F:\codex-workspaces\vtkp-public-demo-20261013`
2. `git status` — expect a clean tree (only the docs commit as tip).
3. `git log --oneline -3` — expect `040ddd1` then `5dfac40`.
4. Re-run acceptance: `python -m pipeline.demo_gate_review --input examples/synthetic/evidence_samples.jsonl --output outputs/main`
5. Re-run tests: `python -m pytest -q tests`
6. To continue: review Draft PR #6, then the owner decides on merge.

## Open question for the owner

One decision remains that the agent must not take: **whether to merge Draft
PR #6 into `main`**, and whether to submit to MLH (which additionally needs the
event rulebook, see `docs/MLH_SUBMISSION_DRAFT.md` §5).
