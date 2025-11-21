app4 - 流式输出 + 工具调用
===========================

概览
----
- 交互式多轮对话，先自动决定是否调用工具，再流式输出最终回答。
- 内置工具：
  - `calc(expression)`: 使用受限 `math` 命名空间计算表达式。
  - `now()`: 返回当前 UTC 时间（ISO 格式）。
- 使用根部 `settings.py` 读取配置，要求 `OPENROUTER_API_KEY`。

运行
----
```bash
uv run apps/app4/main.py
```

用法
----
- 输入问题，空行或 Ctrl+C 退出。
- 需要计算/报时时直接自然语言描述（如“12*(3+4)/sqrt(7)” 或 “现在几点”），模型会自动决定调用工具。
- 支持管道输入：`echo -e "现在几点\n12+7" | uv run apps/app4/main.py` 会按行处理多轮。
- DEBUG：`APP4_DEBUG=1` 时打印工具调用/错误，便于排查。

修改
----
- 调整提示或模型：修改 `SystemMessage` 或 `Settings`。
- 添加新工具：在 `main.py` 中新增 `@tool` 函数并加入 `bind_tools` 列表。
