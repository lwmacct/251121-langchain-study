# Chainlit Tool Call Demo

A LangGraph + Chainlit agent with **automatic demo mode** - the app automatically sends a preset question when the page loads.

## Features

- **🎬 Automatic Demo Mode**: Preset question auto-sends on page load
- **Tool calling**: time query and calculator
- **Multimodal support**: text and images
- **Visual tool call tracking**: See tool execution in real-time
- **Detailed debug logging**: Complete execution traces

## 🎬 Automatic Demo Mode

When you open the app, it will **automatically**:

1. Display welcome message: "🎬 自动演示模式启动"
2. Auto-send the preset question: **"你觉得人工智能 AGI在多少年后实现, 那时是几几年"**
3. Process the question through the LangGraph agent
4. Display the AI's response

This is implemented in the `@cl.on_chat_start` hook, which triggers on page load and programmatically:
- Creates a `HumanMessage` with the preset content
- Processes it through the LangGraph workflow
- Displays all tool calls and the final response

After the demo completes, you can continue chatting normally!

## How to Verify Tool Calls

Three ways to confirm if tools are being called:

### 1. Chainlit UI (Visual Steps)

In the chat interface, you'll see collapsible step panels:

```
[Tool Call: calculator]
  Calling tool `calculator`...
  Args: {'expression': '42*7'}

[Tool Result: calculator]
  Result: 42*7 = 294
```

### 2. Console Logs

The terminal shows detailed execution logs:

```bash
==================================================
🚀 Start processing request
==================================================

📋 Detected tool call (Round 1)
  🔧 Tool: calculator
  📝 Args: {'expression': '42*7'}

🔧 [Tool Call] calculator(expression='42*7')
✅ [Tool Return] Result: 42*7 = 294

==================================================
✨ Completed (1 tool call rounds)
==================================================
```

### 3. Tool Function Logs

Each tool function outputs execution details:

```bash
🔧 [Tool Call] get_current_time(timezone='UTC')
✅ [Tool Return] Current UTC time: 2025-11-22 02:30:45

🔧 [Tool Call] calculator(expression='100/4')
✅ [Tool Return] Result: 100/4 = 25.0
```

## Run the App

```bash
uv run chainlit run apps/05-chainlit-tool-call/main.py -whd --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000 in your browser. The demo will **auto-start immediately**!

## Test Cases

### Auto Demo (On Page Load)
- **Preset question**: "你觉得人工智能 AGI在多少年后实现, 那时是几几年"
- This runs automatically when you open the app

### After Demo - Continue Chatting

#### Time Query
- "What time is it now?"
- "Tell me the current time"

#### Math Calculation
- "What is 42 times 7?"
- "Calculate (10 + 5) * 3"
- "100 divided by 4"

#### Multimodal (Images)
- Upload an image (e.g., `apps/05-chainlit-tool-call/img/claude-code.png`)
- Ask: "请分析这张图片的内容"

#### Multiple Tool Calls
- "What time is it? Also calculate 100 / 4"
- "Tell me the time, then calculate 2 ** 10"

#### Normal Chat (No Tools)
- "Hello"
- "Tell me about yourself"
- "What is LangGraph?"

## Project Structure

```
apps/05-chainlit-tool-call/
├── main.py          # Chainlit app + LangGraph graph
├── tools.py         # Tool definitions (time, calculator)
├── utils.py         # Utilities (image compression)
├── pyproject.toml   # Dependencies
└── README.md        # This file
```

## Tool Call Flow

```
User Input
   ↓
LLM Analysis (need tools?)
   ↓ Yes
Call Tool (shown in UI + console)
   ↓
Tool Execution (internal logs)
   ↓
Return Result (shown in UI + console)
   ↓
LLM uses result to generate response
   ↓
Display final answer
```

## Tech Stack

- **LangChain**: Tool definitions and message handling
- **LangGraph**: Agent workflow orchestration
- **Chainlit**: Web UI and user interaction
- **OpenAI API**: LLM inference (via OpenRouter)

## Adding New Tools

In `tools.py`:

```python
@tool
def your_new_tool(param: str) -> str:
    """Tool description (LLM sees this)"""
    print(f"🔧 [Tool Call] your_new_tool(param='{param}')")

    # Your logic here
    result = do_something(param)

    print(f"✅ [Tool Return] {result}")
    return result
```

In `main.py`, import and add to tools list:

```python
from tools import get_current_time, calculator, your_new_tool

tools = [get_current_time, calculator, your_new_tool]
```

## Notes

- Console logs go to stdout - make sure you can see terminal output
- Chainlit UI steps are collapsible after message is sent
- Tool calls may happen in multiple rounds
- If no tools are called, console shows "0 tool call rounds"
