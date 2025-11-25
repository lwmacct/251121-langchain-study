---
title: 101-simple-chat-stream
---

# 101-simple-chat-stream

简单的 LangChain 聊天流式输出示例，演示如何使用 `stream` 方法实现实时流式响应。

## 功能特性

- 使用 `ChatOpenAI` 连接 OpenRouter API
- 调用 Claude Sonnet 4.5 模型
- 使用 `stream` 方法获取流式响应
- 实时输出 LLM 生成的内容

## 运行方式

```bash
# 设置环境变量
export OPENROUTER_API_KEY=your-api-key

# 运行应用
uv run apps/101-simple-chat-stream/main.py
```

## 代码说明

该示例展示了 LangChain 的流式输出功能：

1. 创建 `ChatOpenAI` 实例，配置模型和 API 端点
2. 使用 `stream()` 方法发送提示词
3. 遍历响应流，实时打印每个 chunk 的内容
4. 通过 `flush=True` 确保内容立即显示

## 与 invoke 的区别

- **invoke**: 等待完整响应后一次性返回，适合短文本
- **stream**: 实时流式返回内容，适合长文本生成，提供更好的用户体验

这是 LangChain 的第二个基础示例，展示了流式处理的重要性。
