# Video Teaching Knowledge Pipeline

## 项目名称

Video Teaching Knowledge Pipeline

## 核心目标

将课程音频、字幕与课程资料转化为可验证的12大数学体系知识结构。

> 本段为项目原有目标描述，来自仓库初始基线（`1efa985`，2026-08-16）。它是
> **项目目标**，不是已交付能力。

---

# 本分支交付：公开可复现演示（VTKP-PUBLIC-REPRODUCIBLE-DEMO-V1）

`main` 分支此前只有文档，没有可运行代码。本分支交付其中一条**最小、可公开、
可复现**的真实流程。

## 它解决什么问题

把课程材料转成"可验证的知识结构"时，最大的风险不是漏掉内容，而是**在证据不足
时把不确定的数学内容当成已确认的事实**。一个数字、单位或符号被悄悄"修正"，
错误会沿知识结构向下传播。

本演示实现的核心纪律：**证据不足就隔离待审，绝不猜测。**

## 一句话流程

一条带来源定位的字幕证据记录进 → 一条带来源定位、失败即阻断的审核结论出。

## 当前实现边界

| 属于本演示 | 不属于本演示 |
|---|---|
| 单条证据的来源绑定 / 时间对齐 / 关键签名 / 抽取器自洽判定 | 音频识别（ASR） |
| 关键项接受或隔离的决策 | 知识结构重建、教材生成 |
| 带来源定位的审核清单导出 | 全量 3649 集处理 |
| 门禁汇总与硬失败条件 | 生产数据库 / State 读写 |

## 实际技术栈

Python ≥ 3.11，**仅标准库**（运行期零第三方依赖）。测试用 `pytest`。
没有网络调用、没有模型、没有 GPU、没有音频解码、没有数据库。

## 安装

```bash
git clone https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline.git
cd video-teaching-knowledge-pipeline
git checkout feat/public-reproducible-demo-20261013
python -m venv .venv
```

运行演示不需要安装任何依赖。只有跑测试需要：

```bash
.venv/Scripts/python -m pip install pytest
```

## 唯一演示命令

```bash
python -m pipeline.demo_gate_review \
  --input examples/synthetic/evidence_samples.jsonl \
  --output outputs/main
```

退出码 `0`，末行给出 `"gate_decision": "CONDITIONAL_PASS"`。

## 输入 / 输出示例

**输入**（`examples/synthetic/evidence_samples.jsonl` 的一行，已省略哈希）：

```json
{"sample_id": "SYN-001", "episode_key": "synthetic:demo:P001",
 "sample_kind": "UNCERTAINTY", "risk_type": "NUMBER", "declared_knowledge_type": "NUMBER",
 "cue_index": "12", "cue_start": "00:00:12.000", "cue_end": "00:00:15.500",
 "original_text": "这组数据的平均数是 42",
 "audio_window_text": "这组数据的平均数是 42",
 "audio_state": "AUDIO_RECOVERABLE", "source_binding": true,
 "window_start_seconds": 12.0, "window_end_seconds": 15.5, "audio_duration_seconds": 120.0}
```

**输出**（`outputs/main/`）：`review_list.csv`、`review_list.jsonl`、
`gate_summary.json`。

`review_list.csv` 每行都带 `sample_id`、`episode_key`、`cue_index`、
`cue_start`、`cue_end`、原始文本、音频文本、判定状态与原因。

完整输入契约见 `docs/DEMO_SCOPE.md`。

## 查看结果

```bash
cat outputs/main/review_list.csv
cat outputs/main/gate_summary.json
```

## 失败行为

```bash
# 关键项丢失来源绑定 → 门禁 FAIL（退出码仍为 0，这是业务结论不是崩溃）
python -m pipeline.demo_gate_review --input examples/synthetic/evidence_hard_fail.jsonl --output outputs/hard_fail

# 输入违反契约 → 退出码 3，不产生任何输出
python -m pipeline.demo_gate_review --input examples/synthetic/invalid_missing_field.jsonl --output outputs/invalid

# 文件不存在 → 退出码 2，不产生任何输出
python -m pipeline.demo_gate_review --input examples/synthetic/nope.jsonl --output outputs/nope
```

## 测试

```bash
python -m pytest -q tests      # 预期 52 passed
```

## 一键复现全部验证

```bash
bash scripts/verify.sh
```

编译源码 → 跑演示 → 断言两个失败退出码（3 / 2，并确认不产生输出目录）→ 跑测试，
最后输出 `ALL CHECKS PASSED`。等价于 CI 会做的事，但不需要任何 CI 服务。
缺少 `pytest` 时给出明确提示并以退出码 4 结束。

## 数据来源与合成样本声明

`examples/synthetic/` 下的全部样本均为**为本演示手写的原创合成数据**，
每条都带 `"synthetic": true`，**不是任何真实课程记录**。它们只用于验证程序
行为，**不能**用于宣称真实数据上的准确率。

`examples/expected/` 下的预期输出是**在运行演示之前**按
`examples/expected/README.md` 中列出的规则人工推导的，不是程序输出的复制。

## 限制

- 合成样本仅 7 条，不支持任何准确率结论。
- 未打开或核对任何音频；`audio_state` 与音频窗口文本是合成输入。
- 仅在 Windows + Python 3.13 验证，不宣称跨平台。
- 生产规模的冻结 24 样本回放不在本演示范围内。
- 本演示只覆盖证据判定一环。

## 未来计划

- 补齐音频核验环节（当前完全缺失）。
- 扩大样本规模并在人工标注数据上评估。
- 决定许可证（**当前未选择任何许可证**；仓库公开不等于授予开源许可）。

---

## 本仓库定位

本仓库用于保存：

- 源码
- Pipeline
- 测试
- Schema
- 配置模板
- 审计规则
- 质量门禁
- 项目状态
- 执行文档

## 本仓库不存储

- 完整音频
- 完整视频
- 生产数据库
- State
- SQLite运行数据
- 凭据
- API Key
- 秘密信息
- 大规模原始字幕资产

## 外部只读数据源说明

Production root:

```text
D:\视频教学采集系统
```

Knowledge-resource root:

```text
D:\司法视频图像处理知识库\12大数学体系_课程资源
```

以上路径仅为外部只读数据源说明，不属于Git仓库内容。本演示未从上述路径迁移
任何文件，也未向其写入任何内容；`pipeline/demo_gate_review.py` 内置拒绝写入
这些根的保护。详见 `docs/SOURCE_MIGRATION.md`。

## 协作原则

后续 Codex 修改应通过 branch、commit、push、PR 进入审查链路；ChatGPT 审查 diff / commit / PR 后，再由用户最终批准。
