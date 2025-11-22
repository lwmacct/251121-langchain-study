# 代码对比：同一个功能，两种实现

## 场景：用户问 "现在几点了？帮我算 2+3"

这个场景需要调用 2 个工具：`get_current_time` 和 `calculator`

---

## 03 的实现：手动循环 + 手动工具执行

### agent.py (186 行)

```python
class Agent:
    def __init__(self, tools: list[BaseTool]):
        self.llm = ChatOpenAI(...)
        self.llm_with_tools = self.llm.bind_tools(tools)  # ✅ 用了 bind_tools
        self.tools_map = {tool.name: tool for tool in tools}  # ❌ 手动映射

    def chat(self, user_input: str, history: list) -> tuple[str, list[str] | None]:
        messages = [SystemMessage(...)]
        messages.extend(history)
        messages.append(HumanMessage(content=user_input))

        tool_calls_made = []

        # ❌ 手动循环
        max_iterations = 5
        for iteration in range(max_iterations):
            try:
                # ❌ 手动调用 LLM
                response = self.llm_with_tools.invoke(messages)

                # ❌ 手动合并 valid 和 invalid tool calls（20+ 行）
                all_tool_calls = []
                if response.tool_calls:
                    all_tool_calls.extend(response.tool_calls)

                if hasattr(response, "invalid_tool_calls") and response.invalid_tool_calls:
                    for invalid_tc in response.invalid_tool_calls:
                        if invalid_tc.get("args") is None:
                            fixed_tc = {
                                "name": invalid_tc["name"],
                                "args": {},
                                "id": invalid_tc["id"],
                                "type": invalid_tc.get("type", "function"),
                            }
                            all_tool_calls.append(fixed_tc)
                            if config.debug:
                                console.print(f"⚠️  修复无参数工具调用: {invalid_tc['name']}")
                        else:
                            if config.debug:
                                console.print(f"警告: 跳过无效工具调用: {invalid_tc}")

                # ❌ 手动检查是否有工具调用
                if not all_tool_calls:
                    return response.content, tool_calls_made if tool_calls_made else None

                # ❌ 手动创建清理过的 AIMessage
                clean_response = AIMessage(
                    content=response.content,
                    tool_calls=all_tool_calls,
                    id=response.id,
                )
                messages.append(clean_response)

                # ❌ 手动执行每个工具（30+ 行）
                for tool_call in all_tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]

                    if config.debug:
                        console.print(f"→ 工具调用: {tool_name}({tool_args})")

                    # ❌ 手动查找工具
                    if tool_name in self.tools_map:
                        try:
                            tool = self.tools_map[tool_name]
                            # ❌ 手动执行工具
                            result = tool.invoke(tool_args)
                            tool_calls_made.append(tool_name)

                            if config.debug:
                                console.print(f"← 工具结果: {result}")

                            # ❌ 手动添加 ToolMessage
                            messages.append(
                                ToolMessage(
                                    content=str(result),
                                    tool_call_id=tool_id,
                                    name=tool_name,
                                )
                            )
                        except Exception as e:
                            # ❌ 手动错误处理
                            error_msg = f"工具执行错误：{e}"
                            console.print(f"[red]{error_msg}[/red]")
                            messages.append(
                                ToolMessage(
                                    content=error_msg,
                                    tool_call_id=tool_id,
                                    name=tool_name,
                                )
                            )
                    else:
                        # ❌ 手动处理未知工具
                        error_msg = f"未知工具：{tool_name}"
                        messages.append(
                            ToolMessage(
                                content=error_msg,
                                tool_call_id=tool_id,
                                name=tool_name,
                            )
                        )

                # ❌ 继续循环，让 LLM 基于工具结果生成最终回复

            except Exception as e:
                console.print(f"[red]Agent 错误：{e}[/red]")
                return f"抱歉，处理请求时出错：{e}", None

        # ❌ 达到最大迭代次数
        return "抱歉，工具调用次数过多，请简化您的问题。", tool_calls_made
```

### session.py (98 行)

```python
@dataclass
class Session:
    history: list[BaseMessage] = field(default_factory=list)
    max_history: int = 50

    def add_user_message(self, content: str) -> None:
        self.history.append(HumanMessage(content=content))
        self._trim_history()  # ❌ 手动管理

    def add_assistant_message(self, content: str) -> None:
        self.history.append(AIMessage(content=content))
        self._trim_history()  # ❌ 手动管理

    def get_history(self) -> list[BaseMessage]:
        return self.history.copy()  # ❌ 手动复制

    def _trim_history(self) -> None:
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]  # ❌ 手动修剪

    # ... 还有 render_history, get_message_count, iter_pairs 等方法
```

### main.py (主循环)

```python
def main():
    agent = create_agent()  # ❌ 需要工厂函数
    session = Session()  # ❌ 需要 Session 类

    for user_input, from_pipe in input_iterator:
        # ❌ 手动添加用户消息
        session.add_user_message(user_input)

        try:
            # ❌ 手动调用 Agent（传递历史）
            reply, tool_calls = agent.chat(user_input, session.get_history()[:-1])

            # ❌ 手动添加助手消息
            session.add_assistant_message(reply)

            # ❌ 手动打印（无法实时展示工具调用）
            print_assistant(reply, tool_calls)

        except Exception as e:
            error_msg = f"处理失败：{e}"
            print_error(error_msg)
            session.add_assistant_message(f"[错误] {error_msg}")
```

**总行数：~400 行（agent.py 186 + session.py 98 + main.py 126）**

---

## 06 的实现：LangGraph 自动化

### main.py（完整实现，仅 212 行）

```python
import operator
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from rich.console import Console

import tools

# ===== 初始化 =====
console = Console()
llm = ChatOpenAI(...)

# ===== 配置工具（仅 3 行） =====
tool_list = [tools.get_current_time, tools.calculator]
tool_node = ToolNode(tool_list)  # ✅ 自动执行工具
llm_with_tools = llm.bind_tools(tool_list)

# ===== 定义状态（仅 3 行） =====
class State(TypedDict):
    messages: Annotated[Sequence[AnyMessage], operator.add]

# ===== 定义节点（仅 6 行） =====
def call_model(state: State) -> State:
    """调用 LLM（带工具）"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: State):
    """判断是否需要继续调用工具"""
    if state["messages"][-1].tool_calls:
        return "tools"  # ✅ 自动路由到工具节点
    return END

# ===== 构建图（仅 10 行） =====
graph = StateGraph(State)
graph.add_node("model", call_model)
graph.add_node("tools", tool_node)  # ✅ ToolNode 自动执行所有工具
graph.add_edge(START, "model")
graph.add_conditional_edges(
    "model",
    should_continue,
    {"tools": "tools", END: END}
)
graph.add_edge("tools", "model")  # 工具执行后返回模型
app = graph.compile()

# ===== 主循环（仅 30 行） =====
def main():
    messages = []  # ✅ 简单的列表，无需 Session 类

    while True:
        user_input = Prompt.ask("💬 You")
        if user_input.lower() in ["exit", "quit"]:
            break

        # ✅ 添加用户消息
        messages.append(HumanMessage(content=user_input))

        # ✅ 流式执行图（自动处理所有逻辑）
        for output in app.stream({"messages": messages}):
            for node_name, state in output.items():
                new_messages = state["messages"]

                # ✅ 处理模型节点输出
                if node_name == "model":
                    last_message = new_messages[-1]

                    # ✅ 实时展示工具调用
                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        for tool_call in last_message.tool_calls:
                            console.print(f"🔧 调用工具: {tool_call['name']}({tool_call['args']})")

                    # ✅ 实时展示 LLM 回复
                    if last_message.content:
                        console.print(f"🤖 Assistant: {last_message.content}")

                # ✅ 处理工具节点输出
                elif node_name == "tools":
                    for msg in new_messages:
                        if isinstance(msg, ToolMessage):
                            console.print(f"✅ 工具返回: {msg.content}")

                # ✅ 自动更新消息历史
                messages = state["messages"]
```

**总行数：212 行（包含 UI 函数和所有逻辑）**

---

## 执行流程对比

### 03 的执行流程（手动控制）

```
用户输入: "现在几点了？帮我算 2+3"
  ↓
session.add_user_message(...)  ← 手动
  ↓
agent.chat(user_input, history)  ← 进入 Agent
  ↓
  [Agent 内部 - 186 行]
  ├─ for iteration in range(5):  ← 手动循环
  │    ├─ response = llm_with_tools.invoke(...)  ← 手动调用
  │    ├─ 手动合并 valid/invalid tool_calls (20 行)
  │    ├─ if not all_tool_calls: return  ← 手动判断
  │    ├─ 手动创建 clean_response
  │    ├─ for tool_call in all_tool_calls:  ← 手动遍历
  │    │    ├─ 手动查找工具
  │    │    ├─ result = tool.invoke(...)  ← 手动执行
  │    │    ├─ 手动创建 ToolMessage
  │    │    └─ messages.append(ToolMessage(...))
  │    └─ 回到循环顶部
  └─ return reply, tool_calls_made
  ↓
session.add_assistant_message(reply)  ← 手动
  ↓
print_assistant(reply, tool_calls)  ← 一次性打印（无法看到中间过程）
```

**问题：**
- ❌ 每一步都是手动的
- ❌ 无法实时看到工具调用过程
- ❌ 代码分散在多个文件
- ❌ 100+ 行胶水代码

### 06 的执行流程（自动化）

```
用户输入: "现在几点了？帮我算 2+3"
  ↓
messages.append(HumanMessage(...))
  ↓
app.stream({"messages": messages})  ← 一次调用
  ↓
  [LangGraph 自动执行]
  START
    ↓
  model 节点 ✅
    ├─ LLM 决定调用 get_current_time
    ├─ 返回 AIMessage(tool_calls=[...])
    └─ 实时打印: "🔧 调用工具: get_current_time(...)"
    ↓
  should_continue() → "tools"  ✅
    ↓
  tools 节点 ✅
    ├─ ToolNode 自动执行 get_current_time
    ├─ 返回 ToolMessage("当前时间是...")
    └─ 实时打印: "✅ 工具返回: 当前时间是..."
    ↓
  model 节点 ✅
    ├─ LLM 决定调用 calculator
    ├─ 返回 AIMessage(tool_calls=[...])
    └─ 实时打印: "🔧 调用工具: calculator(...)"
    ↓
  should_continue() → "tools"  ✅
    ↓
  tools 节点 ✅
    ├─ ToolNode 自动执行 calculator
    ├─ 返回 ToolMessage("计算结果: 2+3=5")
    └─ 实时打印: "✅ 工具返回: 计算结果: 2+3=5"
    ↓
  model 节点 ✅
    ├─ LLM 生成最终回复
    ├─ 返回 AIMessage("现在是... 2+3=5")
    └─ 实时打印: "🤖 Assistant: 现在是... 2+3=5"
    ↓
  should_continue() → END  ✅
  ↓
自动更新 messages（包含所有 AI/Tool 消息）
```

**优势：**
- ✅ 一次调用，LangGraph 自动执行
- ✅ 实时展示每个节点的输出
- ✅ 所有逻辑在一个文件中
- ✅ 仅 30 行主循环代码

---

## 代码量对比（同一功能）

| 组件 | 03 代码量 | 06 代码量 | 减少 |
|------|-----------|-----------|------|
| **工具调用逻辑** | 100+ 行（agent.py:78-178） | 1 行（`ToolNode(tools)`） | 99% ⬇️ |
| **状态管理** | 98 行（session.py） | 0 行（用列表） | 100% ⬇️ |
| **路由逻辑** | 分散在循环中 | 3 行（`should_continue`） | 明确化 ✅ |
| **错误处理** | 20+ 行 | 0 行（ToolNode 自动） | 100% ⬇️ |
| **主循环** | 126 行 | 30 行 | 76% ⬇️ |
| **总计** | ~400 行 | ~50 行（不含 UI） | 87% ⬇️ |

---

## 关键差异总结

| 维度 | 03-interactive | 06-tui |
|------|----------------|--------|
| **架构思维** | 面向对象 + 手动控制 | 图执行 + 声明式 |
| **工具执行** | `for tool_call in ...: tool.invoke(...)` | `ToolNode(tools)` |
| **状态管理** | `Session` 类（98 行） | `messages` 列表 |
| **路由决策** | `if not all_tool_calls: return` | `should_continue()` 条件边 |
| **循环控制** | `for iteration in range(5)` | LangGraph 自动 |
| **错误处理** | 20+ 行修复代码 | ToolNode 自动 |
| **实时展示** | ❌ 无（一次性返回） | ✅ 有（流式执行） |
| **可维护性** | ❌ 低（代码分散） | ✅ 高（代码集中） |

---

## 💡 核心洞察

### 03 的问题：**有 bind_tools，无 LangGraph**

```python
# 03 的方式
llm_with_tools = llm.bind_tools(tools)  # ✅ 这一步是对的

# 但接下来全是手动的...
for iteration in range(max_iterations):  # ❌ 手动循环
    response = llm_with_tools.invoke(...)  # ❌ 手动调用
    for tool_call in response.tool_calls:  # ❌ 手动遍历
        result = self.tools_map[tool_name].invoke(tool_args)  # ❌ 手动执行
        messages.append(ToolMessage(...))  # ❌ 手动添加
```

### 06 的革新：**bind_tools + LangGraph = 自动化**

```python
# 06 的方式
llm_with_tools = llm.bind_tools(tools)  # ✅ 声明工具
tool_node = ToolNode(tools)  # ✅ 自动执行器
graph.add_node("model", ...)  # ✅ 声明节点
graph.add_node("tools", tool_node)  # ✅ 声明节点
graph.add_conditional_edges(...)  # ✅ 声明路由

# 使用
app.stream({"messages": messages})  # ✅ 一行搞定！
```

---

## 🎯 结论

**03 落后的根本原因：没有利用 LangGraph 的自动化能力**

- 虽然用了 `bind_tools`，但还在用命令式编程（手动循环、手动调用、手动管理）
- LangGraph 提供了声明式编程模型（定义图结构，自动执行）
- 代码从 ~400 行减少到 ~50 行，减少 87%
- 维护性、可读性、用户体验全面提升

**从 03 到 06 不是改进，是范式转变！** 🚀
