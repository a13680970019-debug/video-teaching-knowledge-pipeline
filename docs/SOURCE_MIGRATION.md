# Source migration record

Task: `VTKP-PUBLIC-REPRODUCIBLE-DEMO-V1`
Branch: `feat/public-reproducible-demo-20261013`
Base: `origin/main` @ `5dfac409c9cc8b7a7856a7df90259ddb09908c82`

## What was migrated

Two files were taken **verbatim** from an existing pushed branch of this same
repository — `origin/fix/gate-v2-1-controlled-remediation-20260817`. They were
not rewritten, reformatted or re-derived for this demo.

| Repo path | Origin | sha256 |
|---|---|---|
| `pipeline/knowledge_evidence_gate_v21.py` | `origin/fix/gate-v2-1-controlled-remediation-20260817` | `993fe3932bb914868eab015e7e38e8db322b6f80f59736a5b14dcd4592fc48fb` |
| `tests/test_knowledge_evidence_gate_v21.py` | same branch | migrated verbatim |

Integrity check performed during the migration: the module's sha256 in the
branch matches the sha256 of the same file inside that branch's own audit
snapshot at
`audit/knowledge-evidence-gate-v2-1-20260817/CHATGPT_REVIEW_PACKAGE/source/knowledge_evidence_gate_v21.py`.
Both are `993fe393…`, so the copied file is the file the audit lineage claims.

`pipeline/__init__.py` was taken from the same branch (package marker, 50 bytes).

## What was deliberately not migrated

* `pipeline/run_knowledge_evidence_gate_v21.py` — the frozen-sample runner. It
  is hard-bound to the historical 24-sample evidence freeze
  (`00_V2_FIXED_SAMPLE_SET.csv`, `13_V2_AB_PAIRS.jsonl`, `13_V2_AUDIO_ADJUDICATION.jsonl`,
  `V2_CRITICAL_UNRESOLVED.csv`, `V2_GATE_METRICS.json`). Publishing it without
  that archive would produce a non-runnable file; publishing the archive would
  export review material. Excluded.
* `pipeline/asr/authoritative_r2_first_pass.py`,
  `pipeline/transcript_qc/authoritative_r21_segment_redecoder.py` — ASR and
  segment-redecode paths; not needed for this slice.
* The whole `audit/**` tree on the feature branches — internal review evidence,
  large, and not required to reproduce the demo.

## Candidate production roots — what was actually checked

The historical project documents name two read-only candidate roots. Both were
verified to exist on this machine:

| Root | Status |
|---|---|
| `D:\视频教学采集系统` | exists; 194 Python files at depth ≤ 3 |
| `D:\司法视频图像处理知识库\12大数学体系_课程资源` | exists; contains only `字幕_转写/` (one stray file) |

Read-only scan results for `D:\视频教学采集系统` (194 `.py` files, `__pycache__`
excluded):

| Property | Files |
|---|---|
| hard-code a production path | 147 |
| touch SQLite / a state repository | 21 |
| load a model or require a GPU | 20 |
| write to a database or state store | 9 |
| make network calls | 3 |

Representative modules inspected statically (not executed):
`quality_gate_review.py` (imports `quality_state`, which binds `STATE_FILE` to
the production state), `quality_verify_deep.py`, `metadata_sanitize.py`.

**Migration decision: none of the production-root modules were migrated.**
They are all bound to the production state store, the production filesystem
layout, or ASR models. Nothing in that tree could be published or re-run in a
clean environment without dragging production data along.

## Honest provenance statement

The gate V2.1 module has **no counterpart in either production root** — a
recursive name search over both roots returned nothing. Its real lineage is the
repository's own audit/pilot workspace
(`audit/knowledge-evidence-gate-pilot-v2-20260817/`), which is already part of
this repository's pushed history.

Consequence for review: the "migration" here is *within-repository* — from a
feature branch to a new feature branch off `main`. No file was lifted out of a
private production tree and newly exposed.

## Exclusions applied

* No audio, video, subtitle corpus, database, state file, model weight or
  credential is included.
* No absolute production path appears in any published file. The adapter
  contains a guard that **refuses** to write into the production or
  knowledge-base roots, and a test asserts it.
* `.gitignore` was reviewed. The concern that a `*.ts` rule might exclude
  TypeScript sources does not apply: this `.gitignore` has no `*.ts` rule.
