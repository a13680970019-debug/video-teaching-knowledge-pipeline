# Known defects preserved from the R2.1 execution baseline

## R21-001 — `MASKED_UNCLEAR` is not a Pilot failure condition

- Source: `pipeline/transcript_qc/authoritative_r21_segment_redecoder.py`
- Functions: `validate_episode`, `compute_pilot_gate`
- Observed behavior: 1,760 `MASKED_UNCLEAR` words are counted and reported, but do not independently force `MANUAL_AUDIO_REVIEW_REQUIRED` or fail the Pilot Gate.
- Impact: the historical `PILOT20_CODE_DERIVED_PASS=true` does not mean all uncertain words were resolved.
- Planned resolution: a later, separately reviewed gate-contract change must define the knowledge-impact threshold and its acceptance behavior.
- `migration_behavior_preserved`: `true`

This migration preserves the executed baseline and does not silently correct the defect.
