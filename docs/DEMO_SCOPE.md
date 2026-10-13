# Demo scope — public reproducible slice

Task identifier: `VTKP-PUBLIC-REPRODUCIBLE-DEMO-V1`
Path chosen: **B — extract a verifiable core module from an existing pipeline**

## One-sentence description

A course-transcript evidence record goes in; a source-located, fail-closed
review decision comes out.

## Why this slice

The repository's production lineage is coupled to a production root, an
SQLite state store, ASR models and a large frozen evidence archive. Those
parts cannot be published or re-run publicly. One module in the same lineage
is already free of all of that:

`pipeline/knowledge_evidence_gate_v21.py` — the V2.1 knowledge-evidence
semantics. It contains no sample identifiers, no filesystem roots, no model
loading, no audio decoding, no network calls and no production writes.

This demo reuses that module **unchanged** and adds only a thin adapter.

## Input contract

A UTF-8 JSONL file, one record per line. Required fields:

| Field | Meaning |
|---|---|
| `sample_id` | stable identifier, unique within the file |
| `episode_key` | episode the cue belongs to |
| `sample_kind` | `UNCERTAINTY` or `CLEAN_CONTROL` |
| `risk_type` | declared risk class (`NUMBER`, `FORMULA`, `TERM`, …) |
| `declared_knowledge_type` | optional; falls back to `risk_type` |
| `cue_index` | cue number inside the episode |
| `cue_start` / `cue_end` | `HH:MM:SS.mmm` subtitle cue boundaries |
| `original_text` | the claim as it appears in the source transcript |
| `audio_window_text` | what the bound audio window actually says |
| `audio_state` | `AUDIO_RECOVERABLE` / `AUDIO_UNRECOVERABLE` / `AUDIO_UNKNOWN` |
| `source_binding` | JSON boolean — is the evidence bound to a source? |
| `audio_sha256` / `clip_sha256` | 64-char lowercase hex digests |
| `window_start_seconds` / `window_end_seconds` / `audio_duration_seconds` | numeric |

Optional: `synthetic`, `generator`, `module`, `collection_id`.

See `examples/synthetic/` for the fixtures used by the demo.

## Processing steps

1. **Contract validation** (`pipeline/demo_gate_review.py`) — required fields,
   timecode format, digest format, enum values, duplicate ids.
2. **Per-record assessment** (`pipeline/knowledge_evidence_gate_v21.py`) —
   source binding, temporal alignment, type inference, type-specific critical
   signature, generic extractor consistency, semantic supporting signal.
3. **Acceptance decision** — a critical unit is admitted only if source
   binding, temporal evidence, signature and extractor consistency all hold.
   Anything unresolved is quarantined, never guessed.
4. **Aggregate gate** — counts, hard-fail conditions and a gate decision
   (`PASS` / `CONDITIONAL_PASS` / `FAIL`).

## Output contract

Written only inside the caller-supplied output root:

| File | Content |
|---|---|
| `review_list.csv` | one row per record, source-located, human-readable |
| `review_list.jsonl` | the full assessment row per record |
| `gate_summary.json` | aggregate gate metrics plus run metadata |

Every row keeps `sample_id`, `episode_key`, `cue_index`, `cue_start`,
`cue_end`, the original text, the audio text, the acceptance state and the
reason. Unknown stays unknown.

## Reused vs. new

| | |
|---|---|
| **Reused unchanged** | `pipeline/knowledge_evidence_gate_v21.py` (sha256 `993fe393…`), `tests/test_knowledge_evidence_gate_v21.py` |
| **New in this demo** | `pipeline/demo_gate_review.py` (generic adapter + CLI), `tests/test_demo_gate_review.py`, `examples/**`, `docs/**`, `README.md`, `pyproject.toml` |

The adapter adds **no new decision rule**. It only validates input, maps the
flat contract onto the core's inputs, and serialises output.

## Human review position

Blocked critical units are never auto-resolved. They are exported with
`human_review_required=true` and the reason that triggered the block. A human
decides; the program does not.

## Success / failure conditions

| Condition | Behaviour |
|---|---|
| all records valid, no hard-fail condition | exit 0, `CONDITIONAL_PASS` or `PASS` |
| a hard-fail condition triggers (e.g. a critical unit loses source binding) | exit 0, `gate_decision=FAIL` — a result, not a crash |
| input file missing | exit 2, no output written |
| input violates the contract | exit 3, no output written |

## External dependencies and limits

* Python ≥ 3.11, standard library only. `pytest` is needed only to run tests.
* No network, no model, no GPU, no audio decoding, no database.
* The demo proves that **the code behaves as specified**. It does **not**
  prove classification accuracy on real data: the fixtures are synthetic and
  small, so accuracy claims are out of scope.
* The frozen production 24-sample replay
  (`pipeline/run_knowledge_evidence_gate_v21.py` on the feature branches) is
  **not** part of this demo and is not published here.
