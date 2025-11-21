app1 - 同步调用示例
===================

概览
----
- 使用 `ChatOpenAI.invoke` 发起一次性请求，打印完整响应。
- 读取根目录 `settings.py` 配置，依赖 `OPENROUTER_API_KEY`（可选 `OPENROUTER_MODEL` 等覆盖默认值）。

运行
----
```bash
uv run apps/app1/main.py
```

提示
----
- 默认读取 `.taskfile/.env`，或直接用环境变量。
- 修改提示词或模型：编辑 `apps/app1/main.py` 中的 prompt / `settings.model`。
