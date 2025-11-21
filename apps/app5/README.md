# App5: 智能聊天应用

一个演示 LLM 意图路由与工具调用的聊天应用。

## 核心设计思想

### 1. 意图路由架构

采用 LLM 优先 + 关键词兜底的双层路由策略：

- LLM 路由（主）：通过 LLM 分析用户输入语义，返回结构化 JSON 决策
- 关键词兜底（备）：当 LLM 调用失败时，使用保守的关键词匹配作为降级方案

这种设计的优势：
- LLM 能理解语义差异（如"现在几点"vs"美国现在几点"）
- 关键词兜底确保系统在 LLM 不可用时仍能工作
- 兜底触发时显示明显警告，便于监控和调试

### 2. 四种响应类型

- time: 询问本地当前时间 -> 工具调用 get_current_time
- chat: 需要 LLM 思考的问题 -> LLM 生成回答
- summary: 要求总结对话 -> LLM 总结历史消息
- end: 结束对话 -> 工具调用 end_chat 并退出

### 3. 输入模式

支持三种输入方式：

- 管道模式：处理管道输入后退出
- 管道+交互模式（-i 参数）：处理管道输入后进入交互模式
- 纯交互模式：直接进入交互式对话

交互模式使用 prompt_toolkit 提供完整的编辑功能：
- 光标移动、历史记录
- 多行输入：Ctrl+J 换行，Enter 提交
- 空内容时 Enter 无效

### 4. 输出可观测性

所有输出都带有来源标签：

- [get_current_time] / [end_chat] - 工具调用结果
- [LLM:chat] / [LLM:summary] - LLM 生成内容

DEBUG 模式（APP5_DEBUG=1）下额外显示：
- 路由决策过程（LLM 或关键词兜底）
- 决策原因

### 5. 用户体验优化

- 双击 Ctrl+C 退出：单次按下仅清空输入，1秒内连按两次才退出
- 管道与交互分离：管道输入打印"用户: xxx"，交互输入由终端回显
- 彩色输出：使用 rich 库区分用户（绿色）和助手（蓝色）

## 技术栈

- LangChain: LLM 调用与消息管理
- OpenRouter: API 网关（支持多模型）
- rich: 终端彩色输出
- prompt_toolkit: 交互式输入编辑
- Pydantic: 数据模型定义

## 使用方式

管道模式:
  echo -e "现在几点\n结束聊天" | uv run apps/app5/main.py

管道+交互模式:
  echo "现在几点" | uv run apps/app5/main.py -i

纯交互模式:
  uv run apps/app5/main.py

DEBUG 模式（显示路由决策）:
  APP5_DEBUG=1 uv run apps/app5/main.py

## 环境变量

- OPENROUTER_API_KEY (必需): OpenRouter API 密钥
- OPENROUTER_BASE_URL (可选): API 地址，默认 openrouter.ai
- APP5_DEBUG (可选): 设为 1 启用调试输出
