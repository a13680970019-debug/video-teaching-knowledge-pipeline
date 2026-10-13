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
| P5 Validation & reproduction | **PASS** | 48 tests pass in a clean venv; 9/9 validation checks pass; see `docs/VALIDATION_REPORT.md` |
| P6 README & submission material | **PASS (screenshot pending)** | README rewritten; MLH draft written; screenshot not obtainable headless — real text captures provided instead |
| P7 Git / push / Draft PR | **BLOCKED** | Local commits exist; push blocked by missing credential |

## Acceptance status

| Key | Value |
|---|---|
| `SOURCE_DISCOVERY` | **PASS** |
| `PUBLIC_CONTENT_REVIEW` | **PASS** (scan clean; no secrets, no media, no DB, no personal absolute paths added) |
| `DEMO_REPRODUCIBILITY` | **PASS** |
| `TESTS` | **PASS** (48 passed) |
| `SOURCE_INTEGRITY` | **PASS** (migrated core sha256 `993fe393…` unchanged) |
| `DOCUMENTATION` | **PASS** |
| `REMOTE_PR` | **BLOCKED** — see below |
| `MLH_RULES_ELIGIBILITY` | **NOT_EVALUATED** — the event rulebook was not available |

No single PASS hides the BLOCKED or NOT_EVALUATED items.

## Blocker detail

`gh` is not authenticated; `GH_TOKEN` / `GITHUB_TOKEN` are unset; no credential
helper is configured for `github.com`; SSH to `github.com` is rejected
(`Permission denied (publickey)`). Therefore the branch was **not pushed** and
no Draft PR was created.

Do not paste a credential into the chat. The owner can either push from a
machine that already has GitHub access, or provide access another way.

## Resume instructions

1. `cd F:\codex-workspaces\vtkp-public-demo-20261013`
2. `git status` — expect a clean tree (only the docs commit as tip).
3. `git log --oneline -3` — expect `040ddd1` then `5dfac40`.
4. Re-run acceptance: `python -m pipeline.demo_gate_review --input examples/synthetic/evidence_samples.jsonl --output outputs/main`
5. Re-run tests: `python -m pytest -q tests`
6. Only then attempt `git push -u origin feat/public-reproducible-demo-20261013`
   and open a Draft PR against `main`.

## What was deliberately not done

Merging to `main`; submitting to MLH; changing repository visibility;
touching the production roots; re-running the frozen 24-sample replay;
re-collecting the 3649-episode corpus; running any ASR, model or paid API.

## Open question for the owner

Exactly one thing is missing that the agent cannot supply: **GitHub write
access** (or a push performed by the owner). Everything else is complete and
locally verifiable.
