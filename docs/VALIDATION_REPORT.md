# Validation report

Commit under test: `040ddd1bcc9083cb378ca044bd96603e90ce8673`
Branch: `feat/public-reproducible-demo-20261013`
Base: `origin/main` @ `5dfac409c9cc8b7a7856a7df90259ddb09908c82`

## Environment

| Item | Value |
|---|---|
| OS / shell | Windows 11 (10.0.19045), Git Bash (MINGW64_NT), x86_64 |
| Python | 3.13.14 (clean venv, created outside the repository) |
| Test runner | pytest 9.1.1 |
| Runtime dependencies | none (standard library only) |
| Platform scope | **Windows only for the runs recorded below.** A CI workflow that would also exercise `ubuntu-latest` (Python 3.11 + 3.13) is prepared in `.github/workflows/ci.yml` but could not be pushed — the credential lacks the `workflow` scope, so **no CI check runs exist on the PR**. Cross-platform behaviour is therefore still **not** claimed. |

Raw terminal captures: `docs/evidence/run_main.txt`, `run_hard_fail.txt`,
`run_invalid.txt`, `run_missing.txt`, `run_tests.txt`.

## Input hashes

| File | sha256 |
|---|---|
| `examples/synthetic/evidence_samples.jsonl` | `080897f19c8225f714c01138bbdd45efb4cf450fcb7a0b296fdd067d3763530a` |
| `examples/synthetic/evidence_hard_fail.jsonl` | `9b177461c92645e759797a7ce2a6f55cc3c69f9dd45ecd53a1c67e75045bed0b` |
| `examples/synthetic/invalid_missing_field.jsonl` | `86e8030ccaa375bd92cebc67ec4a695f09cfe65a46ca82c2c43d5a20f6d6b7c4` |
| `pipeline/knowledge_evidence_gate_v21.py` (before and after) | `993fe3932bb914868eab015e7e38e8db322b6f80f59736a5b14dcd4592fc48fb` |
| `pipeline/demo_gate_review.py` | `11b59d6d13c2540e68d49188be62a94913ff0cc6e25869cb323140ccb77919d6` |

## Results

| # | Check | Method | Pass criterion | Observed | Status |
|---|---|---|---|---|---|
| 1 | Basic flow | `python -m pipeline.demo_gate_review --input examples/synthetic/evidence_samples.jsonl --output outputs/main` | exit 0, non-empty contract-shaped output | exit 0; 3 files; `gate_decision=CONDITIONAL_PASS` | **PASS** |
| 2 | Input failure — missing field | run on `invalid_missing_field.jsonl` | clear error, non-zero exit, no fake success | exit 3, `missing required field 'clip_sha256'`, no output dir created | **PASS** |
| 3 | Input failure — missing file | run on a non-existent path | clear error, non-zero exit | exit 2, `input file not found`, no output dir created | **PASS** |
| 4 | Source tracing | compare exported rows to the input file | source id and cue/time locator consistent | 7/7 rows carry `sample_id`, `episode_key`, `cue_index`, `cue_start`, `cue_end` matching the input | **PASS** |
| 5 | Uncertainty preserved | deliberately ambiguous record `SYN-003` | stays flagged for review, not auto-resolved | `SIGNATURE_UNKNOWN`, `BLOCKED_CRITICAL`, `human_review_required=true` | **PASS** |
| 6 | Reproducibility | run the same input twice into two output roots | core content identical | `review_list.jsonl` and `review_list.csv` byte-identical across runs | **PASS** |
| 7 | Isolation | inspect the output root; inspect the working tree | writes confined to the output root; no production DB access | exactly 3 files under `outputs/main/`; no other file created; `outputs/` is git-ignored; adapter refuses production/knowledge-base output roots | **PASS** |
| 8 | Clean install | fresh venv outside the repo, install only pytest, run from committed content | runs without any uncommitted file | 48 tests collected and passed; demo runs with no third-party package | **PASS** |
| 9 | Source integrity | sha256 of the migrated core before and after the whole task | unchanged | `993fe393…` identical at migration time and at validation time | **PASS** |
| 10 | One-command verification | `bash scripts/verify.sh` | all checks pass, exit 0 | `ALL CHECKS PASSED`, exit 0; with `pytest` absent it stops with a clear message and exit 4 | **PASS** |

Test suite: **48 passed, 0 failed** (`docs/evidence/run_tests.txt`). This
comprises the 21 tests migrated with the core module plus 27 new demo tests.

## Observed gate summary (main sample set)

```json
{"sample_total": 7, "uncertainty_sample_count": 6, "clean_control_count": 1,
 "critical_units_total": 6, "accepted_critical_count": 3, "blocked_critical_count": 3,
 "wrongly_accepted_critical_count": 0, "critical_false_negative_count": 0,
 "extractor_critical_error_count": 0, "critical_source_binding_failure": 0,
 "gate_decision": "CONDITIONAL_PASS"}
```

These values match the hand-derived expectation in
`examples/expected/README.md`, which was written before the demo was run. The
comparison is enforced by
`tests/test_demo_gate_review.py::test_observed_review_matches_hand_derived_expectation`
and `::test_observed_gate_matches_hand_derived_expectation`.

## What this evidence does **not** support

* **No accuracy claim.** 7 synthetic records cannot support any statement about
  classification accuracy on real course data. The evidence supports only
  "the code behaves as specified on these fixtures".
* **No audio verification.** No audio was opened or listened to. `audio_state`
  and `audio_window_text` are synthetic inputs, not verified transcriptions.
* **No cross-platform claim.** Only Windows was executed.
* **No production-scale claim.** The frozen production 24-sample replay is not
  part of this demo and was not run.
* **No MLH eligibility claim.** See `docs/MLH_SUBMISSION_DRAFT.md`.

## Screenshot status

**Not completed.** The execution environment is a headless agent shell with no
GUI session, so a real terminal screenshot could not be captured. Per the task
rules, generated imagery is not acceptable as run evidence, so the real
captured terminal output is provided as text instead
(`docs/evidence/*.txt`). A human with a GUI session can reproduce the
screenshot by running the command in `docs/QUICKSTART.md` §3.
