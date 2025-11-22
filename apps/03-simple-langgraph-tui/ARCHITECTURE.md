# 架构说明文档

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    06-tui-tool-call                         │
│                                                             │
│  ┌─────────────┐      ┌──────────────┐    ┌─────────────┐ │
│  │   Rich UI   │ ───> │  LangGraph   │───>│   Tools     │ │
│  │  (Terminal) │ <─── │   (Graph)    │<───│  (Actions)  │ │
│  └─────────────┘      └──────────────┘    └─────────────┘ │
│       ↑                      ↑                    ↑        │
│       │                      │                    │        │
│   用户交互              状态管理              工具执行      │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 执行流程

### 1. LangGraph 图结构（简洁版）

```
     START
       │
       ↓
   ┌────────┐
   │ model  │  ← 调用 LLM（带工具绑定）
   └────────┘
       │
       ↓
  [条件判断]
    ╱    ╲
   ↙      ↘
tools    END
  │
  │ 工具执行
  │
  ↓
model
  │
  ↓
 ...
```

### 2. 消息流转

```python
# 用户输入
User: "现在几点了？"
  ↓
# 1. 添加到消息历史
messages.append(HumanMessage("现在几点了？"))
  ↓
# 2. 调用 model 节点
llm_with_tools.invoke(messages)
  ↓
# 3. LLM 决定调用工具
AIMessage(tool_calls=[{"name": "get_current_time", ...}])
  ↓
# 4. 路由到 tools 节点
tool_node.invoke([get_current_time(...)])
  ↓
# 5. 返回工具结果
ToolMessage(content="当前 UTC 时间是: 2025-11-22 03:30:45")
  ↓
# 6. 回到 model 节点
llm_with_tools.invoke(messages + [tool_result])
  ↓
# 7. LLM 生成最终回复
AIMessage(content="现在是 2025年11月22日 03:30:45（UTC时间）")
  ↓
# 8. END
```

## 📊 三种实现方式对比

### 方式 1: 03-interactive-chat-trich（复杂）

```python
# 缺点：代码分散，手动管理状态
agent/
  ├── agent.py       # Agent 类
  ├── session.py     # Session 状态管理
  ├── ui.py          # UI 层
  └── config.py      # 配置

# 主循环
for user_input in input_iterator:
    session.add_user_message(user_input)
    reply, tool_calls = agent.chat(user_input, session.get_history())
    session.add_assistant_message(reply)
    print_assistant(reply, tool_calls)
```

**问题：**
- ❌ 代码分散在多个文件
- ❌ 需要手动管理 Session 状态
- ❌ Agent 类封装过度
- ❌ 维护成本高

---

### 方式 2: 05-chainlit-tool-call（简单 Web）

```python
# 优点：简洁清晰，LangGraph 自动管理状态
# 核心代码
graph = StateGraph(State)
graph.add_node("model", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "model")
graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "model")
app = graph.compile()

# 使用
async def on_message(message):
    for output in app.stream({"messages": [message]}):
        # 自动处理工具调用
        ...
```

**优点：**
- ✅ 代码集中在单个文件
- ✅ LangGraph 自动管理状态
- ✅ 自动路由（model → tools → model）
- ✅ Web 界面功能丰富

---

### 方式 3: 06-tui-tool-call（简单 TUI）✨

```python
# 继承方式 2 的优点，改用终端界面
# 核心代码（与 05 完全相同）
graph = StateGraph(State)
graph.add_node("model", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "model")
graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "model")
app = graph.compile()

# 使用（终端界面）
for output in app.stream({"messages": messages}):
    for node_name, state in output.items():
        if node_name == "model":
            print_assistant(...)
        elif node_name == "tools":
            print_tool_result(...)
```

**优点：**
- ✅ 代码集中在单个文件
- ✅ LangGraph 自动管理状态
- ✅ 自动路由（model → tools → model）
- ✅ 轻量级终端界面
- ✅ 易于集成到 CLI 工具

---

## 🎯 核心简化点

### 1. 状态管理自动化

**之前（03）:**
```python
session = Session()
session.add_user_message(input)
session.add_assistant_message(reply)
history = session.get_history()
```

**现在（06）:**
```python
# LangGraph 自动管理，只需维护一个列表
messages = []
messages.append(HumanMessage(input))
# LangGraph 自动添加 AIMessage 和 ToolMessage
```

### 2. 工具路由自动化

**之前（03）:**
```python
# 手动判断意图
intent = llm.invoke("判断意图...")
if intent == "time":
    result = get_current_time()
elif intent == "calc":
    result = calculator()
```

**现在（06）:**
```python
# LangGraph 自动路由
def should_continue(state):
    if state["messages"][-1].tool_calls:
        return "tools"  # 自动调用工具
    return END
```

### 3. 工具调用自动化

**之前（03）:**
```python
# 手动解析工具参数
if tool_name == "get_current_time":
    result = get_current_time(timezone=args["timezone"])
```

**现在（06）:**
```python
# ToolNode 自动执行
tool_node = ToolNode(tools)
# 自动解析参数并执行
```

## 📈 代码量对比

| 项目 | 文件数 | 核心代码行数 | 复杂度 |
|------|--------|--------------|--------|
| 03-interactive | 5 个文件 | ~300 行 | ⭐⭐⭐ |
| 05-chainlit | 3 个文件 | ~200 行 | ⭐ |
| 06-tui | 2 个文件 | ~150 行 | ⭐ |

## 🎓 关键学习点

### 1. LangGraph 的威力

- **自动状态管理**: 不需要手动维护 Session
- **自动工具路由**: 通过条件边自动决定下一步
- **自动工具执行**: ToolNode 自动解析参数并执行

### 2. bind_tools 的魔法

```python
# 简单的一行代码，让 LLM 知道可用工具
llm_with_tools = llm.bind_tools([get_current_time, calculator])

# LLM 返回时会自动包含 tool_calls
response = llm_with_tools.invoke(messages)
# response.tool_calls = [{"name": "get_current_time", "args": {...}}]
```

### 3. 流式执行的优势

```python
# 实时展示执行过程
for output in app.stream({"messages": messages}):
    # 每个节点执行完成后立即返回结果
    # 用户可以实时看到工具调用过程
    ...
```

## 🚀 最佳实践

1. **使用 LangGraph + ToolNode**: 自动化工具调用
2. **使用 bind_tools**: 让 LLM 自己决定是否调用工具
3. **使用 stream()**: 实时展示执行过程
4. **保持简洁**: 不要过度封装，单文件实现即可

## 📝 总结

| 特性 | 03-interactive | 05-chainlit | 06-tui |
|------|----------------|-------------|--------|
| 工具调用 | 手动路由 | 自动（LangGraph） | 自动（LangGraph） |
| 状态管理 | 手动（Session） | 自动（LangGraph） | 自动（LangGraph） |
| 代码复杂度 | 高 | 低 | 低 |
| 界面 | 终端 | Web | 终端 |
| 依赖 | 多 | 中等 | 少 |
| 推荐场景 | ❌ 不推荐 | ✅ Web 应用 | ✅ CLI 工具 |

**结论:** 06-tui-tool-call 是终端应用的最佳实践，继承了 05-chainlit 的简洁架构，但更轻量级！
