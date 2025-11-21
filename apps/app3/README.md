app3 - 交互式流式问答
====================

概览
----
- 支持多轮对话，维护聊天历史，逐块流式输出回复。
- 配置来自根部 `settings.py`，需要 `OPENROUTER_API_KEY`。

运行
----
```bash
uv run apps/app3/main.py
```

用法
----
- 按提示输入问题，空行或 Ctrl+C 退出。
- 修改系统提示或模型：编辑 `main.py` 内的 `SystemMessage` / `Settings`。
