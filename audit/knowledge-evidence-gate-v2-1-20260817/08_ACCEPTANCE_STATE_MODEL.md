# V2.1 acceptance state model

The engine keeps these axes independent:

- `audio_state`: `AUDIO_RECOVERABLE`, `AUDIO_UNRECOVERABLE`, `AUDIO_UNKNOWN`
- `source_binding`: `SOURCE_BOUND`, `SOURCE_BINDING_FAILED`
- `temporal_state`: `TEMPORAL_VERIFIED`, `TEMPORAL_FAILED`, `TEMPORAL_UNKNOWN`
- lexical overlap: diagnostic only; cross-language low overlap is not a temporal failure
- `semantic_alignment_state`: supporting signal only; no LLM-only critical acceptance
- `critical_signature_state`: `SIGNATURE_MATCH`, `SIGNATURE_MISMATCH`, `SIGNATURE_PARTIAL`, `SIGNATURE_NOT_APPLICABLE`, `SIGNATURE_UNKNOWN`
- `extractor_state`: `EXTRACTOR_CONSISTENT`, `EXTRACTOR_TYPE_MISMATCH`, `EXTRACTOR_UNKNOWN`
- `knowledge_acceptance`: `ACCEPTED_AUDIO_BOUND`, `PRESERVED_ORIGINAL`, `BLOCKED_CRITICAL`, `BLOCKED_NONCRITICAL`, `HUMAN_REVIEW_REQUIRED`

A blocked critical unit is a valid safety outcome only when it is source-bound, reason-coded, and excluded from downstream admission. Coverage and safety are reported separately.
