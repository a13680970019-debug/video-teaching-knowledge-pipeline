# R2/R2.1 End-to-End Authoritative Source Integration

## Status

- `TASK`: `VIDEO-TEACHING-R2-R21-END-TO-END-AUTHORITATIVE-SOURCE-INTEGRATION-20260816`
- `MAIN_BASE_SHA`: `5dfac409c9cc8b7a7856a7df90259ddb09908c82`
- `BRANCH`: `feature/import-authoritative-r2-r21-pipeline`
- `DO_NOT_MERGE`: `true`
- `READY_FOR_CHATGPT_REVIEW`: `true`

## Authoritative runtime sources

| Component | Source entrypoint | Source SHA-256 | Evidence | Migrated destination | Migration result |
|---|---|---|---|---|---|
| First pass ASR | `D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-audio-grounded-20260807\00_control\run_r2_audio_grounded_pilot.py::run_asr_pilot` | `eff54f660ec7993a08b771f6f50f49b4330fb3c3c17c6184a76bbd142d46f468` | `E3_RUNTIME_DIRECT` | `pipeline/asr/authoritative_r2_first_pass.py` | exact byte copy |
| Second pass transcript QC | `D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-1-pilot-remediation-20260807\pipeline\segment_redecoder.py::run_second_pass` | `333317ded1223099901559f511e0a3e5a6009da5ab18cb2c901bdaf37ddffd78` | `E3_RUNTIME_DIRECT` | `pipeline/transcript_qc/authoritative_r21_segment_redecoder.py` | exact byte copy |

The two migrated source hashes equal their recorded originals. `ALGORITHM_BEHAVIOR_CHANGES=0`; the only adaptation is destination relocation and package initialization. The migrated modules were not run against production data or real audio during this integration.

## Data reconciliation

| Metric | Value |
|---|---:|
| `TOTAL_WORD_ROWS` | 49829 |
| `INITIAL_HIGH_RISK` | 8936 |
| `R2_RESOLVED_HIGH_RISK` | 3901 |
| `SECOND_PASS_REQUIRED` | 5035 |
| `NON_INITIAL_HIGH_RISK` | 40893 |
| `AUTO_CONFIRMED_FIRST_PASS` | 44794 |
| `CONSENSUS_MATCH` | 1640 |
| `SECOND_PASS_HIGHER_CONFIDENCE` | 1583 |
| `TERMINOLOGY_CONTEXT_MATCH` | 52 |
| `MASKED_UNCLEAR` | 1760 |

Reconciliation passed:

```text
40893 + 8936 = 49829
3901 + 5035 = 8936
1640 + 1583 + 52 + 1760 = 5035
40893 + 3901 = 44794
```

Second-pass evidence covers `2963/2963` unique required segments, with zero missing, duplicate, or failed rows in the frozen R2.1 evidence. The frozen R2/R2.1 evidence reports `P027_AUDIO_GROUNDED=true` and final language `en`.

## Dependency closure and selection

- `SOURCE_FILES_DISCOVERED=23`
- `DIRECT_ENTRYPOINTS=2`
- `RUNTIME_DEPENDENCIES_CONFIRMED=2` local authoritative entrypoints; `faster_whisper` remains an external runtime dependency and is not vendored.
- `AUTHORITATIVE_FILES_MIGRATED=2`
- `SOURCE_FILES_EXCLUDED=21`
- `STUB_FILES=8`
- `OBSOLETE_FILES=1`
- `UNKNOWN_FILES=0`

The excluded set contains unexecuted/static-only helpers, docstring-only contracts, and the superseded R2 one-line segment contract. The selection and adaptation evidence is in the CSV audit files in this directory.

## Known defect preserved

`R21-001`: the Pilot Gate reports `MASKED_UNCLEAR=1760` but does not include it in the failure condition. This is preserved byte-for-byte, documented in `docs/KNOWN_DEFECTS.md`, and regression-tested so the migration does not silently change historical behavior. A historical `PILOT_20_PASSED=true` therefore does not mean all unclear words were resolved.

## Tests and verification

- `py -3.14 -m compileall -q pipeline tests` — passed, zero compile errors.
- `py -3.14 -m pytest -q tests` — `9 passed`, `0 failed`, `0 skipped`.
- Tests use synthetic paths, synthetic VTT fixtures, mocked ffprobe duration at the boundary, consensus branches, the known gate defect, repetition post-processing, VTT cue/timestamp preservation, and import/entrypoint markers.
- No real ASR, real audio decoding, 2963-segment rerun, Canary, Production, translation, knowledge ingestion, or external LLM call was executed.

## Safety and asset controls

```text
PRODUCTION_WRITE_COUNT = 0
ASR_EXECUTION_COUNT = 0
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
FILES_OVER_10MB = 0
```

The secret and asset scan reports contain counts only and do not contain authentication output or credential values. Production roots, R2, R2.1, and the provenance-audit workspace were treated as read-only inputs; no file in those roots was modified.

## Review decision

This branch is ready for one GitHub PR review only. Do not merge until ChatGPT review explicitly approves the source provenance, preserved defect, dependency closure, tests, and safety evidence.
