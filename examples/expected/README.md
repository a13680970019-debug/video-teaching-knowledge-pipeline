# Expected outputs — derivation rules

These expected values were written by hand from the documented gate rules
**before** the demo was executed. They are not a copy of program output. The
observed-versus-expected comparison is recorded in
`docs/VALIDATION_REPORT.md`.

## Rules

| Ref | Rule |
|---|---|
| R1 | A critical unit (`sample_kind=UNCERTAINTY`) is admitted only if source binding, temporal evidence, type-specific signature and generic extractor consistency all hold. |
| R2 | `SOURCE_BOUND` requires `episode_key`, `cue_index`, `cue_start`, `cue_end`, `audio_sha256`, `clip_sha256` to be present **and** `source_binding=true`. |
| R3 | `TEMPORAL_VERIFIED` requires `0 <= start < end <= duration + 0.25s` and no promotional marker inside the audio window text. |
| R4 | `NUMBER_WITH_UNIT` matches only when both the number and the unit family agree (e.g. `distance_km` vs `distance_mile` is a mismatch). |
| R5 | Ambiguous numeric tokenisation (`除238 再加158`) yields `SIGNATURE_UNKNOWN`, never a guess, so the unit stays `BLOCKED_CRITICAL` and is sent to human review. |
| R6 | A cue whose end time is not strictly after its start time fails temporal alignment, so a critical unit is blocked regardless of text agreement. |
| R7 | `CLEAN_CONTROL` rows are never rewritten: the original claim is preserved and no harmful change is recorded. |
| R8 | A promotional/advertising window is treated as the wrong audio for the cue, so the unit is blocked and sent to human review. |

## Per-record derivation

| sample_id | reasoning |
|---|---|
| SYN-001 | Number `42` spoken identically; binding complete; window inside duration → R1+R2+R3 → accepted. |
| SYN-002 | Number `75` with unit `公里` on both sides → same unit family → R1+R4 → accepted. |
| SYN-003 | Source numbers `100, 50, 25` vs spoken `除238 再加158`; the operator+3-digit form is ambiguous → R5 → unknown → blocked. |
| SYN-004 | `cue_end == cue_start` violates `end > start` → R6 → blocked. |
| SYN-005 | `6 分之一` and `六分之一` both normalise to the number pair `(6, 1)` → R1+R3 → accepted, and the full cue is not rewritten. |
| SYN-007 | Clean control, temporally verified → R7 → accepted with original preserved. |
| SYN-008 | Audio window is promotional speech → R3 fails → R8 → blocked and queued for human review. |

## Aggregate derivation

* 7 records total, 1 clean control, 6 critical units.
* Accepted critical units: SYN-001, SYN-002, SYN-005 → 3.
* Blocked critical units: SYN-003, SYN-004, SYN-008 → 3.
* No hard-fail condition is triggered (no false negative, no wrong acceptance,
  no extractor type mismatch, no critical source-binding failure, no text-only
  correction, no harmful control change).
* Therefore `gate_decision = CONDITIONAL_PASS`: coverage is incomplete but
  safety is not violated, and the blocked units remain quarantined.
