# Data Boundaries

This repository is a control repository. It stores code, schemas, tests, audit rules, configuration templates, project status, and execution documentation only.

## External Read-Only Source Roots

```text
Production root:
D:\视频教学采集系统

Knowledge-resource root:
D:\司法视频图像处理知识库\12大数学体系_课程资源
```

These paths are external source locations. They are not repository content.

## Prohibited Repository Content

```text
complete audio files
complete video files
production databases
runtime State files
SQLite runtime files
credentials
API keys
secret tokens
large raw transcript corpora
review ZIP packages
```

## Migration Rule

Future migration from existing Codex workspaces must follow:

```text
inventory
→ select source-only files
→ scan secrets and large assets
→ commit to a feature branch
→ push
→ PR
→ ChatGPT review
→ user approval
```

Directly copying whole production or review-package directories is prohibited.
