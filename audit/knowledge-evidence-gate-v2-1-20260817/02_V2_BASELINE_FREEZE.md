# V2 immutable baseline freeze

The frozen set is `00_v2_baseline_freeze/00_V2_FIXED_SAMPLE_SET.csv`.

- `FIXED_SAMPLE_COUNT = 24`
- `UNIQUE_SAMPLE_IDS = 24`
- `FIXED_SAMPLE_MANIFEST_SHA256 = e1b4107a2e4d12a0c760f73d0e90a5b32011d9af9f6291b84652161637e96931`
- V2 metrics SHA-bound in `00_V2_BASELINE_HASH_MANIFEST.csv`.
- Original V2 directory was read-only and not overwritten.

## Reproduction result

`04_BASELINE_REPRODUCTION_SUMMARY.json` records:

- semantic reproduction: **true**
- byte-identical reproduction: **false**
- metric differences: **0**
- data drift rows: **1** (the published audio JSONL has 27 rows for 24 fixed IDs, with duplicate rows for three controls)
- environment drift rows: **2** (runtime timestamps/sandbox paths)

The historical V2 execution-time source hash was not recorded. Therefore the current source is labelled `AUTHORITATIVE_CURRENT_SNAPSHOT`; exact historical source-version reproduction is unproven.
