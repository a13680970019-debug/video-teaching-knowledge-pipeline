# Gate V2.1 fixed-sample remediation summary

- Fixed sample set: **24 unique IDs**, unchanged from the frozen V2 manifest.
- V2 reported baseline: **FAIL**.
- Pre-fix replay: semantic reproduction **PASS**; byte-identical reproduction **false** because runtime timestamps/sandbox paths differed and the published audio JSONL contains 3 duplicate rows.
- Post-fix replay: **CONDITIONAL_PASS** under the new safety semantics.
- Critical units: 15; accepted audio-bound: 4; explicitly blocked/quarantined: 11.
- Hard-fail counts: false negatives 0, wrongly accepted 0, extractor errors 0, source-binding failures 0, text-only corrections 0, harmful clean-control changes 0.
- Limited canary eligible: **false**. Full-scale and Knowledge Canary remain **unauthorized**.

This stage changes generic type-specific signature, source-binding, temporal, and acceptance semantics. It does not rerun the original V2, resample, scale ASR, rewrite transcripts, or write production knowledge.
