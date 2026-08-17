# Type taxonomy findings

## Findings

1. Indexed labels such as a spoken `A1 B2` pattern are not ordinary NUMBER values. They are represented as `INDEXED_SYMBOL` when the letter/index relationship is evidenced; extra context remains partial/blocked rather than being forced into a numeric match.
2. Letter/digit notation such as an interval-like `B ... A.0` is handled as `SYMBOL_LETTER`/indexed notation, not forced through the ordinary-number path.
3. Fractions are evaluated by a fraction signature independently from noncritical filler text. A matching fraction does not authorize a full cue rewrite.
4. Number-plus-unit values use a `NUMBER_WITH_UNIT` signature. Equal numerals with different unit families remain a critical mismatch.
5. Named titles/term phrases are classified generically as `NAMED_TITLE_OR_TERM` when the context supports that interpretation; no sample-specific branch exists.

## Taxonomy change proposal

The historical V2 labels remain unchanged for provenance. The V2.1 engine adds an explicit inferred type and records whether the old label was reclassified. This is a post-execution semantic proposal, not a mutation of the V2 target taxonomy.
