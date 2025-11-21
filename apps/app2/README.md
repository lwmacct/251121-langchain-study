app2 - 流式输出示例
===================

概览
----
- 演示 `ChatOpenAI.stream`，逐块打印模型回复。
- 使用根部 `settings.py`，需要 `OPENROUTER_API_KEY`。

运行
----
```bash
uv run apps/app2/main.py
```

提示
----
- 默认 prompt 在 `main.py` 中，可按需调整。
- 支持从 `.taskfile/.env` 或环境变量读取配置。
