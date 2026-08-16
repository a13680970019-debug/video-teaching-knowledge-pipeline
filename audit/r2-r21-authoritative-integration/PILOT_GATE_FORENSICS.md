# Pilot Gate forensics

Executed implementation: `pipeline/transcript_qc/authoritative_r21_segment_redecoder.py::compute_pilot_gate`.

Observed behavior:

- `TARGET_ROWS=20`
- `SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED=2963/2963`
- `MASKED_UNCLEAR_WORD_COUNT=1760`
- `TRANSCRIPT_ACCEPTED_RATE=1.0`
- `PILOT_20_PASSED=true`

Known defect R21-001: the gate counts `MASKED_UNCLEAR` for reporting but does not require its count or rate to be zero. The acceptance checks test `STILL_UNRESOLVED`, mathematical unresolved items, repetition hallucination, identity, accepted rate, and zero-write fields. This behavior is intentionally preserved in the migrated byte-for-byte source and is not treated as validated correctness.
