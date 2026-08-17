# Gate V2.1 acceptance report

## Decision

`GATE_V21 = CONDITIONAL_PASS`

This is a fixed-sample engineering decision, not authorization for the 3649-episode system. `LIMITED_CANARY_ELIGIBLE = false`, `FULL_SCALE_AUTHORIZED = false`, and `KNOWLEDGE_CANARY_AUTHORIZED = false`.

## Counts

| Metric | Value |
|---|---:|
| Fixed samples | 24 |
| Critical units | 15 |
| Accepted critical | 4 |
| Blocked critical | 11 |
| Critical false negatives | 0 |
| Wrongly accepted critical | 0 |
| Extractor critical errors | 0 |
| Critical source-binding failures | 0 |
| Text-only corrections accepted | 0 |
| Clean-control harmful changes | 0 |

The hard-fail counters are all zero. The remaining critical set is explicitly quarantined; the conservative canary eligibility flag remains false because the fixed sample covers only a limited evidence pool and still contains blocked critical cases.

## Root causes

The nine-row matrix includes the eight original critical blocked units plus one clean-control alignment control. It distinguishes taxonomy reclassification, ambiguous numeric tokenization, temporal misalignment, cross-language lexical diagnostics, expanded-window attribution, and number/unit materiality.
