---
title: 100-simple-chat-invoke
---

# 100-simple-chat-invoke

简单的 LangChain 聊天调用示例，演示如何使用 `invoke` 方法进行一次性 LLM 对话。

## 功能特性

- 使用 `ChatOpenAI` 连接 OpenRouter API
- 调用 Claude Sonnet 4.5 模型
- 使用 `invoke` 方法获取完整响应
- 简单的环境变量配置

## 运行方式

```bash
# 设置环境变量
export OPENROUTER_API_KEY=your-api-key

# 运行应用
uv run apps/100-simple-chat-invoke/main.py
```

## 代码说明

该示例展示了 LangChain 的最基本用法：

1. 创建 `ChatOpenAI` 实例，配置模型和 API 端点
2. 使用 `invoke()` 方法发送单个提示词
3. 接收完整的响应内容

这是学习 LangChain 的第一个示例，适合初学者了解基本的 LLM 调用流程。
