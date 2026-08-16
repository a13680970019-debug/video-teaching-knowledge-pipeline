# Video Teaching Knowledge Pipeline

## 项目名称

Video Teaching Knowledge Pipeline

## 核心目标

将课程音频、字幕与课程资料转化为可验证的12大数学体系知识结构。

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

以上路径仅为外部只读数据源说明，不属于Git仓库内容。

## 协作原则

后续 Codex 修改应通过 branch、commit、push、PR 进入审查链路；ChatGPT 审查 diff / commit / PR 后，再由用户最终批准。
