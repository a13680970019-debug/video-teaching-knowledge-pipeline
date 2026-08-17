# Current Status

## Confirmed Current Status

### Historical R2 epoch contract

The historical totals are kept separate from current Gate V2 metrics:

INITIAL_HIGH_RISK_WORDS = 8936
R2_RESOLVED = 3901
SECOND_PASS_REQUIRED_WORDS = 5035
MASKED_UNCLEAR = 1760

The value 5035 is the Second-Pass-required count, not the initial high-risk total. This is a governance/documentation correction only; it does not change ASR, consensus, threshold, repetition, validate_episode, or compute_pilot_gate behavior.

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
