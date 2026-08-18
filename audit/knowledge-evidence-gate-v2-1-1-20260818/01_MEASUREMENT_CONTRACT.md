# Measurement Contract — Gate V2.1.1

## Purpose
This stage validates measurement integrity for the fixed 24-sample V2.1 set. It does not rerun ASR, Gate V2/V2.1, knowledge reconstruction, Canary, or Production.

## Metric contract
| METRIC_NAME | CLAIM | UNIT / DENOMINATOR | PREDICTION | REFERENCE TRUTH | HOW DERIVED | UNKNOWN / NOT_MEASURED |
|---|---|---:|---|---|---|---|
| critical_false_negative | A reference-positive critical mismatch was blocked rather than accepted | count / 15 | system acceptance state | independent human/objective mismatch label | compare reference-positive rows with accepted audio-bound output | null + NOT_MEASURED when no independent gold |
| wrongly_accepted_critical | An accepted critical output conflicts with independent truth | count / 15 | accepted output | independent human/objective truth | compare accepted claim/signature/unit with reference | null + NOT_MEASURED without gold |
| extractor_critical_error | System type disagrees with independently reviewed type | count / 15 | inferred type | reviewed/reference type | compare declared, inferred, and reference type | null + NOT_MEASURED without reference type |
| critical_source_binding_failure | Critical evidence records or required bytes bind to wrong/missing source | count / 15 | identity and hashes | objective record identity + recomputed bytes | cross-record identity plus AUDIO/VTT/CLIP SHA256 | UNKNOWN/PARTIAL when evidence is missing |
| text_only_correction_accepted | Accepted changed claim lacks independently verified audio/clip evidence | count / 24 | A/B delta + acceptance | objective byte-verified source evidence | claim change AND accepted AND no verified audio/clip | semantic correctness is separate |
| clean_control_harmful_change | A clean-control change causes material semantic/critical regression | count / 6 | A/B delta | independent human/objective clean truth | compare claims and adjudicate materiality | null + NOT_MEASURED without gold |

## Status rules
- VERIFIED: derivation completed with required independent/objective evidence.
- PARTIAL: only part of required evidence was available.
- NOT_MEASURED: required independent reference is absent; value is null.
- CONFLICT: evidence sources disagree.
- System output, signature matcher, extractor, ASR transcript, translation, and LLM inference are not independent gold.
- UNKNOWN is never coerced to zero.
- Zero is reported only when the specified derivation counted zero.

## Gate implication
Any hard safety metric required for an independent decision with status other than VERIFIED yields INDEPENDENT_GATE_DECISION=NOT_EVALUABLE. This is a measurement statement, not a score optimization.

