# 10 Unresolved Audio Cases — V2 Root Cause Report

All 10 cases were re-read from V1 I03_UNRESOLVED_AUDIO_CASES.csv. The historical E-root audio paths and hashes remain in the V1 package, but the current E root is absent and the current D audio target root is absent. Therefore current local acoustic windows cannot be created. This is recorded as root_cause=UNKNOWN with root_cause_detail=CURRENT_AUDIO_SOURCE_MISSING, not as an inferred noise/model cause.

- Cases: 10
- Current audio window evidence available: 0/10
- AUDIO_UNRESOLVED: 10/10
- Human review required: 10/10
- Filler-like target candidates: 10 (candidate only; not audio-confirmed)

The missing-source condition is not used to declare an acoustic or knowledge result. A future run with a verified current audio binding must adjudicate these exact keys and timestamps.
