# MLH submission draft

> Status: **draft only.** Nothing has been submitted. `MLH_RULES_ELIGIBILITY`
> is `NOT_EVALUATED` because the event rulebook was not available in this
> environment. Every unknown is marked *待提供 / 待核* rather than guessed.

## 1. Project URL

* Repository: https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline
* **Important:** `main` has **not** been updated. The default branch still
  contains only `README.md`, `.gitignore` and four documents under `docs/`.
  The demo described here lives on the branch
  `feat/public-reproducible-demo-20261013`
  (commit `040ddd1bcc9083cb378ca044bd96603e90ce8673`).
* Draft PR: https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline/pull/6
  (open, draft, mergeable clean, 25 files)
* Pending before merge: human review, then the owner's merge decision.

## 2. Description

### 中文

**问题.** 把课程音频、字幕和课程资料转成"可验证的知识结构"时，真正的风险不是漏掉内容，而是**在证据不足时把不确定的数学内容当成已确认的事实**。一个数字、单位或符号一旦被错误地"修正"，错误就会沿着知识结构往下传播。

**当前实现.** 本仓库此前只有文档，没有可运行代码。本次交付把已有的一条证据判定逻辑做成可公开、可复现的最小流程。

**工作方式.** 输入一条字幕证据记录（原始文本、绑定音频窗口的转写文本、cue 时间码、来源绑定信息、音频状态）；程序依次判定来源绑定是否成立、时间对齐是否成立、知识类型推断、类型相关的关键签名是否一致、抽取器类型是否自洽，然后给出"接受 / 隔离待审"的结论，并把结果按来源定位导出。

**本人本次完成内容.**
- 复用仓库既有分支中的 `pipeline/knowledge_evidence_gate_v21.py`（未改动，sha256 `993fe393…`）。
- 新写离线适配入口 `pipeline/demo_gate_review.py`：定义并校验输入契约、映射到核心评估、导出带来源定位的审核清单与门禁汇总，失败时非零退出。
- 新写原创合成样本、人工推导的预期输出与规则说明、27 个新测试。
- 在仓库外的干净虚拟环境中完成复现验证（48 项测试通过）。
- 撰写 README、演示范围、迁移记录、验证报告与本提交草稿。

**限制.**
- 合成样本仅 7 条，**不能**用于声称真实数据的分类准确率。
- 未打开或核对任何音频；`audio_state` 与音频窗口文本是合成输入。
- 仅在 Windows + Python 3.13 验证，不宣称跨平台。
- 生产规模的冻结 24 样本回放不在本演示范围内。
- 演示只覆盖"证据判定"这一环，不包含音频识别、不包含知识结构重建。

### English

**Problem.** When turning course audio, subtitles and course material into a
"verifiable knowledge structure", the real risk is not missing content — it is
**promoting uncertain mathematical content to confirmed fact when the evidence
is insufficient**. Once a number, unit or symbol is silently "corrected", the
error propagates through the whole structure.

**Current implementation.** Until now this repository contained documentation
only, with no runnable code. This delivery turns one existing piece of evidence
adjudication logic into a public, reproducible minimal flow.

**How it works.** One evidence record goes in (original text, transcript of the
bound audio window, cue timecodes, source-binding information, audio state).
The program checks, in order: source binding, temporal alignment, inferred
knowledge type, the type-specific critical signature, and generic extractor
consistency. It then emits an *accepted* or *quarantined for human review*
decision, exported with its source location.

**What I did.**
- Reused `pipeline/knowledge_evidence_gate_v21.py` from an existing branch of
  this repository **unchanged** (sha256 `993fe393…`).
- Wrote an offline adapter/CLI, `pipeline/demo_gate_review.py`, which defines
  and validates the input contract, maps it onto the core assessment, exports a
  source-located review list and gate summary, and fails closed with a non-zero
  exit code.
- Wrote original synthetic fixtures, hand-derived expected outputs with their
  derivation rules, and 27 new tests.
- Verified reproduction in a clean virtual environment outside the repository
  (48 tests passing).
- Wrote the README, demo scope, migration record, validation report and this
  submission draft.

**Limitations.**
- Only 7 synthetic records — this **cannot** support any accuracy claim on real
  data.
- No audio was opened or checked; `audio_state` and the audio-window text are
  synthetic inputs.
- Verified on Windows + Python 3.13 only; no cross-platform claim.
- The frozen production 24-sample replay is out of scope.
- The demo covers evidence adjudication only — not audio recognition, not
  knowledge-structure reconstruction.

## 3. Technology tags (with the file that justifies each)

| Tag | Justification file |
|---|---|
| `python` | `pipeline/demo_gate_review.py`, `pyproject.toml` (`requires-python = ">=3.11"`) |
| `cli` | `pipeline/demo_gate_review.py` — `argparse` entry point, `python -m` runnable |
| `pytest` | `tests/`, `pyproject.toml` (`[project.optional-dependencies] test`) |
| `jsonl` / `csv` | `examples/synthetic/*.jsonl`, `pipeline/demo_gate_review.py` writers |
| `text-processing` | `pipeline/knowledge_evidence_gate_v21.py` |

GitHub is a hosting tool, not a technology stack, so it is not listed as a tag.

## 4. Real execution evidence

**Screenshot: not completed.** The environment is a headless agent shell with
no GUI session; a real terminal screenshot could not be taken, and generated
imagery must not be passed off as run evidence. The real captured terminal
output is delivered as text instead:

| Path | Purpose | Command | Evidence |
|---|---|---|---|
| `docs/evidence/run_main.txt` | main flow + environment + commit | `python -m pipeline.demo_gate_review --input examples/synthetic/evidence_samples.jsonl --output outputs/main` | exit 0, `CONDITIONAL_PASS` |
| `docs/evidence/run_hard_fail.txt` | fail-closed gate | `... --input examples/synthetic/evidence_hard_fail.jsonl --output outputs/hard_fail` | exit 0, `FAIL` |
| `docs/evidence/run_invalid.txt` | contract violation | `... --input examples/synthetic/invalid_missing_field.jsonl --output outputs/invalid` | exit 3, nothing written |
| `docs/evidence/run_missing.txt` | missing input | `... --input examples/synthetic/does_not_exist.jsonl --output outputs/nope` | exit 2, nothing written |
| `docs/evidence/run_tests.txt` | test suite | `python -m pytest -q tests` | 48 passed |
| `scripts/verify.sh` | one-command reproduction of every check above | `bash scripts/verify.sh` | `ALL CHECKS PASSED`, exit 0 |

## 5. Rule checklist

The event rulebook was not available in this environment. Nothing below is
invented.

| Item | Value |
|---|---|
| Event name | *待提供* |
| Original rule URL | *待提供* |
| Submission time window | *待核* |
| Are existing projects allowed? | *待核* |
| AI usage disclosure requirement | *待核* — for transparency: this work used an AI coding agent; the human owner directed the task and must review before submission |
| Open-source requirement | *待核* — no licence has been chosen for this repository; the owner must decide (see §7) |
| Demo requirement | *待核* |
| Team / eligibility requirements | *待核* |

## 6. Remote status

`REMOTE_PR = PASS`. The branch `feat/public-reproducible-demo-20261013` was
pushed to `origin` at `0a9489d…` and Draft PR #6 was opened against `main`:

https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline/pull/6

Note: `gh auth status` reports no logged-in host and `gh pr create` refuses to
run, but a working credential is available through git's credential helper for
`github.com`. The push used `git push`; the Draft PR was created through the
GitHub REST API. No credential value was printed or stored in any file.

`main` is **not** updated by this PR — the default branch still has no code.

**CI gap:** the PR currently has **0 check runs**. A CI workflow
(`.github/workflows/ci.yml`, Linux + Windows, Python 3.11 + 3.13) is prepared
and its steps were replicated locally, but it cannot be pushed: any file under
`.github/workflows/` requires the token's `workflow` scope, which this
credential does not have (`403 Resource not accessible by integration`). The
patch is kept at `F:\codex-workspaces\vtkp-ci-workflow.patch` for the owner to
apply.

## 7. Open decisions for the owner

1. Licence: none has been selected. This repository is public but that does not
   by itself grant an open-source licence.
2. Whether to merge the demo into `main` after review.
3. Whether the MLH event permits an existing project, and how AI assistance
   must be disclosed.
4. Whether to also publish the frozen 24-sample replay (currently excluded —
   it needs the historical evidence archive).
