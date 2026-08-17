# Current Status

## Historical R2/R2.1 epoch — frozen contract

These values are historical evidence and are not interchangeable with current ledger counts:

- TOTAL_WORD_ROWS = 49829
- INITIAL_HIGH_RISK_WORDS = 8936
- R2_RESOLVED = 3901
- SECOND_PASS_REQUIRED_WORDS = 5035
- MASKED_UNCLEAR = 1760
- Historical identity: 3901 + 5035 = 8936

## Current evidence ledger epoch

Re-read from the current local evidence package:

- TOTAL_EPISODES = 3649
- TRANSCRIPT_USABLE = 3022
- TRANSCRIPT_NEEDS_REMEDIATION = 2
- TRANSCRIPT_VERSION_CONFLICT = 75
- ASR_RUNNABLE_AUDIO = 535
- VERIFIED_COMPLETED_ASR = 89
- CURRENT_REMAINING_ASR = 446

## Knowledge-evidence gate epoch

- V1 knowledge-evidence pilot = FAIL; its raw unresolved audio rate was diagnostic and its sample was not corpus-representative.
- V2 pilot = FAIL in the isolated package audit/knowledge-evidence-gate-pilot-v2-20260817.
- V2 sample = 24 local audio-bound samples: 18 targeted critical/uncertainty cues and 6 controls across the six modules with current local MP3+VTT bindings.
- V2 critical false negatives = 0.
- V2 extractor critical errors = 2; both were blocked rather than accepted.
- V2 critical unresolved/blocked = 8.
- V2 text-only corrections accepted = 0.
- Full-scale knowledge reconstruction = NOT AUTHORIZED.
- Canary 50 = NOT STARTED.
- Production 130 = NOT STARTED.
- PR #2 merge = NOT EXECUTED.

## Governance note

Main-branch protection and rulesets remain unavailable under the current private-repository plan; the live API returned the plan limitation response. A governance-only branch carries this status correction. It does not change PR #2, main, production files, State, SQLite, V7, or the knowledge base.

## Next review

ChatGPT and the user review the V2 gate failure, the two extractor critical errors, the eight blocked critical items, and the governance branch before any later canary decision.

