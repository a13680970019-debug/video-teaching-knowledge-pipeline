# External Evidence and Method Notes

This report records references consulted for measurement validity, Git comparisons, and alignment diagnostics. No project media was uploaded to an external service.

## SUPPORT
- NIST TEVV: https://www.nist.gov/ai-test-evaluation-validation-and-verification-tevv
  NIST describes reliable measurements and evaluations as foundational and emphasizes context-specific strengths and limitations.
- GitHub commit comparison: https://docs.github.com/en/pull-requests/how-tos/commit-changes/comparing-commits
  The compare view is the server-side view for branch/commit ancestry and changed-file review.
- WhisperX repository and CLI: https://github.com/m-bain/whisperX
  The project exposes word-level and phoneme alignment options.

## COUNTER_EVIDENCE / LIMITATIONS
- WhisperX issue history documents alignment failure modes involving language mismatch, symbols/digits, and cases where cue-level timestamps do not prove word-level timing:
  https://github.com/m-bain/whisperX/issues/1311
  https://github.com/m-bain/whisperX/issues/1315
  https://github.com/m-bain/whisperX/issues/1220
- A valid window is therefore not treated as proof that a critical token was spoken inside the target cue. Existing fixed-24 evidence has no word/token timestamps for these rows, so the current temporal state is WINDOW_ONLY or TEMPORAL_CONFLICT.

## ALTERNATIVE
A same-language forced-alignment diagnostic may supply token timing, but it is evidence rather than an oracle. Cross-language translation is supporting evidence only and is not gold.

## STATE_OF_THE_ART NOTE
WhisperX and MFA-style forced alignment are candidates for a later controlled diagnostic. This stage intentionally does not download models, rerun ASR, or send private media to a remote API.

