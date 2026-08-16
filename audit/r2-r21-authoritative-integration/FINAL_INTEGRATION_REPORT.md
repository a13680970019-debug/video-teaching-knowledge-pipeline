# R2/R2.1 PR #2 Remediation Report

## Status

- `TASK`: `PR2-FULL-REMEDIATION-20260816`
- `MAIN_BASE_SHA`: `5dfac409c9cc8b7a7856a7df90259ddb09908c82`
- `BRANCH`: `feature/import-authoritative-r2-r21-pipeline`
- `PR_NUMBER`: `2`
- `DO_NOT_MERGE`: `true`
- `READY_FOR_CHATGPT_REVIEW`: `true`

## Provenance terminology

The frozen R2/R2.1 evidence confirms the executed paths and entrypoints at E3, but it does not bind a source hash captured at execution time. Therefore this report does not claim an exact executed source version.

```text
EXECUTED_PATH_CONFIRMED = true
EXECUTED_SOURCE_VERSION_HASH_BOUND = false
SOURCE_VERSION_AT_EXECUTION = UNPROVEN
```

The migrated files are named and classified as `AUTHORITATIVE_CURRENT_SNAPSHOT_OF_EXECUTED_ENTRYPOINT`. Their byte-identical originals are preserved under `provenance/` with the historical source hashes. The current files add only the allowed fail-closed CLI guard and explicit path configuration.

## Authoritative sources and allowed adaptation

| Component | Historical entrypoint | Provenance snapshot SHA-256 | Current migrated SHA-256 | Allowed adaptation | Algorithm behavior |
|---|---|---|---|---|---|
| First pass ASR | `...run_r2_audio_grounded_pilot.py::run_asr_pilot` | `eff54f660ec7993a08b771f6f50f49b4330fb3c3c17c6184a76bbd142d46f468` | `0f345567a03f9348723e05eab8cf1c8a40931bbe3c504d65df4285bd6b0ce8e7` | CLI guard, explicit input/output injection | unchanged |
| Second pass QC | `...segment_redecoder.py::run_second_pass` | `333317ded1223099901559f511e0a3e5a6009da5ab18cb2c901bdaf37ddffd78` | `51e45a6ebf3aa99709cf78de825625b0c63b2da9636c754f89789226b6173bf4` | CLI guard, explicit input/output injection | unchanged |

`ALGORITHM_BEHAVIOR_CHANGES = 0`: ASR parameters, thresholds, consensus, repetition detection, `validate_episode`, and `compute_pilot_gate` were not changed. R21-001 remains present.

Static AST comparison confirms the listed consensus/repetition/validation/gate functions are unchanged; the First-Pass `run_asr_pilot` core is identical after removing only its inserted `_require_real_execution()` guard.

## Fail-closed execution contract

Both runtime modules now require all of the following before any real model boundary is reached:

```text
FAIL_CLOSED = true
--execute-real
--input-root <explicit>
--output-root <explicit>
```

Direct `run_asr_pilot` and `run_second_pass` calls also reject execution until the explicit runtime configuration is installed. No default CLI path points to the historical R2/R2.1 roots. Output roots equal to or below any of these protected roots are rejected:

```text
D:\视频教学采集系统
D:\司法视频图像处理知识库
D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-audio-grounded-20260807
D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-1-pilot-remediation-20260807
```

## Frozen data reconciliation

```text
TOTAL_WORD_ROWS = 49829
INITIAL_HIGH_RISK = 8936
R2_RESOLVED_HIGH_RISK = 3901
SECOND_PASS_REQUIRED = 5035
NON_INITIAL_HIGH_RISK = 40893
AUTO_CONFIRMED_FIRST_PASS = 44794
CONSENSUS_MATCH = 1640
SECOND_PASS_HIGHER_CONFIDENCE = 1583
TERMINOLOGY_CONTEXT_MATCH = 52
MASKED_UNCLEAR = 1760
DATA_RECONCILIATION_PASS = true
SECOND_PASS_SEGMENTS_VERIFIED = 2963/2963
P027_AUDIO_GROUNDED = true
```

## Dependency closure

```text
SOURCE_FILES_DISCOVERED = 23
DIRECT_ENTRYPOINTS = 2
AUTHORITATIVE_FILES_MIGRATED = 2
SOURCE_FILES_EXCLUDED = 21
STUB_FILES = 8
OBSOLETE_FILES = 1
UNKNOWN_FILES = 0
```

`faster_whisper` remains an external runtime dependency and is not imported by CI tests or vendored into the repository.

## Known defect preserved

`R21-001`: `MASKED_UNCLEAR=1760` is reported but is not part of the historical Pilot Gate failure condition. This PR documents and tests the historical behavior; it does not fix or reinterpret that gate.

## Tests

The original 9 tests remain. New synthetic safety coverage verifies default CLI refusal, explicit `--execute-real`, explicit output root, production/KB/historical R2/historical R2.1 output rejection, and a safe temporary root with a mocked Whisper boundary.

```text
TEST_COMMAND_LOCAL_COMPILE = py -3.14 -m compileall -q pipeline tests
TEST_COMMAND_LOCAL = py -3.14 -m pytest -q tests
TESTS_COLLECTED = 23
TESTS_PASSED = 23
TESTS_FAILED = 0
TESTS_SKIPPED = 0
```

No real model, audio, First-Pass, Second-Pass, 2963-segment rerun, Canary, Production, knowledge impact, knowledge reconstruction, or external LLM was executed.

## GitHub Actions

`.github/workflows/ci.yml` uses `windows-latest` and Python 3.11. It installs only `pytest`, runs `compileall` and the synthetic test suite, sets offline model environment flags, and contains no model/audio/production step.

## Safety evidence

```text
PRODUCTION_WRITE_COUNT = 0
REAL_ASR_EXECUTION_COUNT = 0
SECOND_PASS_REEXECUTION_COUNT = 0
CANARY_EXECUTION_COUNT = 0
STATE_WRITE_COUNT = 0
SQLITE_WRITE_COUNT = 0
V7_WRITE_COUNT = 0
AUDIO_FILES_COMMITTED = 0
VIDEO_FILES_COMMITTED = 0
PRODUCTION_VTT_FILES_COMMITTED = 0
DATABASE_FILES_COMMITTED = 0
ARCHIVE_FILES_COMMITTED = 0
MODEL_FILES_COMMITTED = 0
SECRET_FILES_COMMITTED = 0
```

PR #2 remains open and draft. This remediation is ready for ChatGPT review and must not be merged.
