# Gate V2 Acceptance Report

Decision: **FAIL**

## Primary metrics
- Sample: 24; uncertainty: 18; controls: 6
- Critical units: 15
- Critical false negatives: 0
- Critical knowledge unresolved: 8
- Extractor critical errors: 2
- Critical source-binding failures: 0
- Text-only corrections accepted: 0
- Non-critical unresolved: 1
- Raw audio unresolved rate: 0.0000 (diagnostic only)

## Decision semantics
The runner used local offline audio evidence and a conservative acceptance rule. A low-alignment or signature-mismatch result preserves the original cue and is blocked; it is not promoted as a correction. No percentage threshold was invented. The available audio-bound pool is not the full 3649-episode corpus, so this result does not authorize full-scale reconstruction.
