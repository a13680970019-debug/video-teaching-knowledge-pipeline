# MASKED_UNCLEAR provenance

Source: `pipeline/transcript_qc/authoritative_r21_segment_redecoder.py::decide_consensus`

Provenance snapshot SHA256: `333317ded1223099901559f511e0a3e5a6009da5ab18cb2c901bdaf37ddffd78`

Current migrated snapshot SHA256: `59d6a16615b0ee4297e10cc558e9488f7b41e64a2de6e40354545bb03cb58623`

`EXECUTED_PATH_CONFIRMED=true`; `EXECUTED_SOURCE_VERSION_HASH_BOUND=false`; `SOURCE_VERSION_AT_EXECUTION=UNPROVEN`.

The R2.1 output audit recalculated 1,760 `MASKED_UNCLEAR` rows from 5,035 required rows. The implementation preserves the historical behavior: no aligned second-pass word or unresolved ambiguity produces `final_word` shaped as `[unclear]`. A 30-row real-ledger sample is retained in the read-only provenance audit package referenced by `docs/KNOWN_DEFECTS.md`.

Relevant branches:

1. `second_word is None` → `MASKED_UNCLEAR` / `SECOND_PASS_NO_ALIGNED_WORD_MASKED`.
2. No exact consensus, higher-confidence, or terminology partial-match threshold → `MASKED_UNCLEAR` / `AMBIGUOUS_AFTER_SECOND_PASS_MASKED_NOT_GUESSED`.

This is provenance documentation, not a correction to the algorithm.
