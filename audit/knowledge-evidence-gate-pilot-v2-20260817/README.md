# Gate V2 Review Evidence

THIS DIRECTORY CONTAINS REVIEW EVIDENCE, NOT PRODUCTION KNOWLEDGE DATA.

The files under review are a text-only, path-sanitized derivative of the existing local Gate V2 execution evidence. The original V2 output was not rewritten and Gate V2 was not rerun.

## Scope

- Existing V2 execution evidence is indexed and hash-bound.
- The recorded Gate V2 result remains FAIL.
- The review copy contains no audio, video, model, database, State, SQLite, V7, production, or knowledge-base asset.
- Absolute local paths are replaced with normalized markers; source hashes and source-to-published mapping are retained.
- The package does not authorize a knowledge reconstruction canary or full-scale knowledge reconstruction.

## Review entry points

- 00_STAGE_MANIFEST.json
- V2_SAMPLE_MANIFEST.csv
- V2_AB_TRANSCRIPT_PAIRS.jsonl
- V2_AUDIO_ADJUDICATION_LOG.csv
- V2_KNOWLEDGE_A.jsonl
- V2_KNOWLEDGE_B.jsonl
- V2_KNOWLEDGE_DIFF.csv
- V2_GATE_METRICS.json
- V2_ACCEPTANCE_REPORT.json
- REVIEW_FILE_MAPPING.csv
- FILE_HASH_MANIFEST.csv

The stage-level publication package and ZIP are retained locally outside this Git branch. This branch contains the ordinary review directory only.
