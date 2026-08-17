# CURRENT_STATUS Reconciliation

The live main branch document was re-read. Its labels Initial high-risk words = 5035 and Consensus/resolved candidates = 3275 are not the authoritative historical metric contract.

## Superseded labels

- Initial high-risk words = 5035 is a label collision: 5035 is SECOND_PASS_REQUIRED_WORDS, not INITIAL_HIGH_RISK_WORDS.
- Authoritative historical epoch: INITIAL_HIGH_RISK_WORDS=8936, R2_RESOLVED=3901, SECOND_PASS_REQUIRED_WORDS=5035, MASKED_UNCLEAR=1760.
- Current evidence epoch: 3649-key ledger with 3022 usable, 2 remediation, 75 version conflicts, 535 original ASR runnable, 89 verified completed, 446 current remaining.
- V1 knowledge gate was FAIL; current V2 result is read from 25_GATE_V2_ACCEPTANCE_REPORT.json and is FAIL because two critical extractor type mismatches were caught and eight critical sample items remain blocked.

A governance-only status correction is prepared separately and does not alter PR2 or main directly.

## Live document excerpt

# Current Status

## Confirmed Current Status

```text
R2 real-audio First Pass = completed
R2.1 Second-Pass segments = 2963 / 2963

Initial high-risk words = 5035
Consensus/resolved candidates = 3275
Masked unclear = 1760

Canary 50 = NOT STARTED
Production 130 = NOT STARTED
```

## Next Required Work

下一阶段不是重新运行First Pass。

当前需要：
对1760个Masked Unclear进行知识影响分类，识别真正影响：

- 数学术语
- 数字
- 公式
- 定义
- 条件
- 结论
- 符号

的Critical风险。

本 bootstrap 任务不执行该分类。
