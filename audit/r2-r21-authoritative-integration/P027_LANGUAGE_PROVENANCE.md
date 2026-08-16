# P027 language provenance

`pipeline/transcript_qc/authoritative_r21_segment_redecoder.py::run_p027_language_review` is audio-grounded.

- It decodes the referenced audio path locally.
- It evaluates START 0–90 seconds, MIDDLE 255–345 seconds, and END 510–600 seconds.
- Each window has forced-English and auto-language local decode results.
- Aggregation returns `en` when at least two auto windows are `en`, `mixed` for one, otherwise `uncertain`.
- Observed result: `START auto=nn`, `MIDDLE auto=en`, `END auto=en`, final `en`.

The P027 result was not independently added to the Pilot Gate checks; that binding gap remains documented in the integration report.
