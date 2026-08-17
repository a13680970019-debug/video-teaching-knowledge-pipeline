# Uncertainty Taxonomy V2

Two independent axes are retained:

1. Audio state: AUDIO_RECOVERABLE, AUDIO_PARTIAL, AUDIO_UNRECOVERABLE; operational AUDIO_UNRESOLVED is used where evidence is missing.
2. Knowledge impact: NO_KNOWLEDGE_IMPACT, POSSIBLE_KNOWLEDGE_IMPACT, CRITICAL_KNOWLEDGE_IMPACT.

Critical knowledge types: TERM, NUMBER, FORMULA, SYMBOL, DEFINITION, CONDITION, CONCLUSION, DERIVATION. An audio-unresolved filler candidate is not automatically accepted as harmless; only cue/context plus identical deterministic extraction can make it a non-critical candidate, while missing current audio remains unresolved and human-reviewable.
