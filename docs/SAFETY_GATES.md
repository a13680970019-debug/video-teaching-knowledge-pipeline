# Safety Gates

```text
PRODUCTION_GIT_INIT_ALLOWED = false
PRODUCTION_FILE_WRITE_ALLOWED = false
STATE_WRITE_ALLOWED = false
SQLITE_WRITE_ALLOWED = false
V7_WRITE_ALLOWED = false

RAW_AUDIO_GITHUB_PUSH_ALLOWED = false
RAW_VIDEO_GITHUB_PUSH_ALLOWED = false
DATABASE_GITHUB_PUSH_ALLOWED = false
SECRET_GITHUB_PUSH_ALLOWED = false

FORCE_PUSH_MAIN_ALLOWED = false
DIRECT_MAIN_DESTRUCTIVE_HISTORY_REWRITE = false
```

## Future Codex Code Modification Principle

```text
main
→ 不直接做复杂开发
→ 创建feature/fix/audit branch
→ commit
→ push
→ PR
→ ChatGPT审查
→ 用户最终批准
```
