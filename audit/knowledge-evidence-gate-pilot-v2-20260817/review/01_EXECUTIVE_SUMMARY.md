# Knowledge Evidence Gate Pilot V2 — Executive Summary

## Result

- TASK_COMPLETED = true
- KNOWLEDGE_EVIDENCE_GATE_V2 = FAIL
- KNOWLEDGE_RECONSTRUCTION_CANARY_AUTHORIZED = false
- LIMITED_SCOPE_CANARY_AUTHORIZED = false
- DO_NOT_SCALE = true

## Local evidence

- V1 was re-read without modification. Actual V1 file count is 53 while the task summary said 52; this is recorded as CONFLICT.
- The 3649-key evidence ledger and historical contract were reverified.
- Current local audio-bound pool: 226 MP3+same-directory VTT bindings; this is not the full corpus.
- V2 sample: 24 rows = 18 targeted critical/uncertainty cues + 6 controls, covering six modules with current bindings.
- Local offline large-v3 clip ASR: 27 / 27 rows completed with AUDIO_RECOVERABLE.
- Ten historical V1 unresolved cases remain AUDIO_UNRESOLVED because their current source audio is missing; no guessed acoustic fact was recorded.

## Gate metrics

- Critical false negatives: 0
- Critical knowledge unresolved/blocked: 8
- Extractor critical errors: 2
- Critical source-binding failures: 0
- Text-only corrections accepted: 0
- Raw audio unresolved rate: 0.0000, diagnostic only

The gate is FAIL because two critical extractor type mismatches were detected and blocked. The package does not authorize a full-scale or limited-scope knowledge canary.

## Governance

PR #2 remains open and unmerged at the reviewed head. CI success is limited to compile/tests. Main branch protection/rulesets are not verifiable under the current private-repository plan. A governance-only status branch was pushed; no PR was created and no merge was performed.
