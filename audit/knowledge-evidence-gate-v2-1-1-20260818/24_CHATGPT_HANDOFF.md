# Handoff to ChatGPT

## Current conclusion
The fixed V2.1 pipeline reported CONDITIONAL_PASS, but this independent measurement-integrity run reports NOT_EVALUABLE. The reason is missing independent gold for 15 critical units and six changed clean-control claims, not a zero score.

## Frozen identity
- fixed sample count: 24
- unique sample count: 24
- fixed sample SHA256: e1b4107a2e4d12a0c760f73d0e90a5b32011d9af9f6291b84652161637e96931
- historical V2/V2.1 evidence: not modified
- V2.1 rerun: false
- ASR/knowledge/Canary/Production: 0

## Independently derived evidence
- cross-record binding: 24/24 verified
- required bytes: 72/72 verified (AUDIO/VTT/CLIP across 24 samples)
- critical source-binding failures: 0, VERIFIED
- text-only accepted corrections: 0, VERIFIED
- temporal critical evidence: 14 WINDOW_ONLY, 1 TEMPORAL_CONFLICT, 0 TOKEN_TIME_VERIFIED
- critical false negative: null, NOT_MEASURED
- wrongly accepted critical: null, NOT_MEASURED
- extractor critical error: null, NOT_MEASURED
- clean-control harmful change: null, NOT_MEASURED

## Required human review
All 15 critical units remain NOT_REVIEWED. The narrow-question packet is 03_HUMAN_GOLD_REQUIRED.csv. No human gold was fabricated.

## Governance
PR #2 and PR #4 remain open and unmerged. PR #4 is a historical stacked artifact. A clean branch from current main is the only candidate for an independent measurement-integrity PR. No merge authorization is granted.

## Decision
FULL_MEASUREMENT_INTEGRITY=false
INDEPENDENT_GATE_DECISION=NOT_EVALUABLE
KNOWLEDGE_CANARY_AUTHORIZED=false


## Publication outcome
- clean branch: fix/gate-v2-1-1-measurement-integrity-20260818
- clean head after workflow fix: d0678d2a75a15540966b6233a52ff2850d68dd3a
- clean PR: #5 (https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline/pull/5)
- PR2 commits present in clean branch: false
- PR2 files present in clean branch: false
- PR4 unchanged, open, unmerged
- GitHub Actions: SUCCESS, run 32091088981

