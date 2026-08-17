# External Evidence V2

## 1. ASR transcript noise and downstream impact

- Claim: ASR errors can propagate into downstream systems and hallucinated speech can be induced by non-speech or adverse audio.
- Source: Careless Whisper: Speech-to-Text Hallucination Harms, https://arxiv.org/abs/2402.08021; Investigation of Whisper ASR Hallucinations Induced by Non-Speech Audio, https://arxiv.org/abs/2501.11378
- Support: These studies document hallucination and harm modes rather than treating a transcript as self-authenticating truth.
- Counter-evidence / limitation: The studies do not establish the error rate or threshold for this 3649-episode corpus.
- Applicability: Supports preserving uncertainty and using acoustic evidence plus explicit blocking.
- Project implication: Raw unresolved rate is diagnostic; critical knowledge units require source-bound evidence.

## 2. Audio plus transcript correction

- Claim: Audio-grounded and multimodal correction can improve domain transcription, but auxiliary context must be evaluated against acoustic evidence.
- Sources: ASR-EC Benchmark, EMNLP 2025 Industry Track, https://aclanthology.org/2025.emnlp-industry.110.pdf; Do Slides Help? Multi-modal Context for Automatic Transcription of Conference Talks, https://aclanthology.org/2025.emnlp-main.814/
- Support: These works study audio/text or multimodal context for domain terms and correction.
- Counter-evidence / limitation: Context can also introduce unsupported lexical substitutions; neither paper proves the current project’s model output is ground truth.
- Applicability: Supports the V2 A/B design and the no-text-only-guess rule.
- Project implication: An audio window is evidence; a correction is accepted only under conservative alignment and binding, otherwise it remains blocked.

## 3. Uncertainty-aware downstream gating

- Claim: Evidence-aware systems should retain provenance and confidence instead of silently promoting uncertain text.
- Source: Learning Fine-Grained Grounded Citations for Better Evidence-Based Generation, https://openreview.net/pdf?id=7atXKldh-r
- Support: Grounded generation research emphasizes fine-grained linkage between claims and evidence.
- Counter-evidence / limitation: Citation grounding is not a direct ASR accuracy benchmark.
- Applicability: The V2 source_binding field and human-review queue operationalize the same provenance principle.
- Project implication: BLOCKED_CRITICAL is a valid outcome; it is not converted into a guessed correction.

## 4. Representative and stratified evaluation

- Claim: Evaluation results depend on data composition and evaluation-set construction.
- Sources: Benchmark Transparency: Measuring the Impact of Data on Evaluation, https://aclanthology.org/2024.naacl-long.86/; Constructing Domain-Specific Evaluation Sets for LLM-as-a-judge, https://aclanthology.org/2024.customnlp4u-1.14/
- Support: These papers motivate documenting sampling strata and limitations.
- Counter-evidence / limitation: They do not provide a fixed sample size or a corpus-specific acceptance threshold here.
- Applicability: V2 reports module, collection, risk, language, and knowledge-type counts.
- Project implication: V2 coverage is an engineering sample contract, not a proof of the full 3649-episode error rate.

## 5. GitHub branch governance

- Claim: Protected branches and rulesets are server-side controls, distinct from a documented workflow.
- Sources: GitHub protected branches, https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches; available rules for rulesets, https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets; REST branch protection API, https://docs.github.com/en/rest/branches/branch-protection
- Support: GitHub documents pull-request, status-check, force-push, and deletion protections as repository settings.
- Counter-evidence / limitation: The current live API returned a private-plan limitation, so these controls are not verified for this repository.
- Applicability: V2 records API return evidence and does not infer enabled protection from documentation.
- Project implication: GITHUB_GOVERNANCE_READY remains false; a status-only governance branch was pushed, but no merge or main write was executed.

## State-of-art and project boundary

The external literature supports an evidence hierarchy and conservative gating, not a made-up numeric pass threshold. V2 therefore uses failure semantics: confirmed critical false negatives, accepted critical extractor errors, source-binding failures, or text-only guesses fail the gate. The current run found zero critical false negatives, two critical extractor type mismatches that were blocked, eight blocked critical sample items, and zero text-only corrections accepted. These are local run results, not external benchmark claims.
