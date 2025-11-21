# Tools Library

**一个库，多个应用，零配置复用。**

基于 uv workspace 的共享 LangChain 工具库，为 monorepo 项目提供统一的工具管理和零成本的代码共享。

---

## 📚 目录

- [快速开始](#-快速开始)
- [可用工具](#-可用工具)
- [为新项目添加](#-为新项目添加)
- [设计理念](#-设计理念)
- [配置详解](#-配置详解)
- [技术细节](#-技术细节)
- [最佳实践](#-最佳实践)
- [常见问题](#-常见问题)
- [故障排查](#-故障排查)

---

## 🚀 快速开始

### 1. 安装（仅一次，在根目录）

```bash
# 在项目根目录运行
uv sync
```

### 2. 导入使用

```python
from tools import get_current_time, calculator

# 使用方式与本地 tools.py 完全相同
tool_list = [get_current_time, calculator]
```

### 3. 运行应用（从根目录）

```bash
# 运行任何应用
uv run apps/06-tui-tool-call/main.py
uv run apps/05-chainlit-tool-call/main.py
```

---

## 🔧 可用工具

### get_current_time

获取当前时间。

**参数：**

- `timezone` (str, optional): 时区名称（如 'UTC', 'Asia/Shanghai'）。默认: 'UTC'

**返回：**

- str: 格式化的当前时间字符串

**示例：**

```python
from tools import get_current_time

result = get_current_time.invoke({"timezone": "UTC"})
# "当前 UTC 时间是: 2025-11-22 04:00:00"
```

### calculator

执行数学计算。

**参数：**

- `expression` (str): 数学表达式（如 '2 + 2', '10 \* 5 + 3'）

**返回：**

- str: 计算结果或错误信息

**示例：**

```python
from tools import calculator

result = calculator.invoke({"expression": "42 * 7"})
# "计算结果: 42 * 7 = 294"
```

---

## 📦 为新项目添加

### Step 1: 配置项目依赖

**`apps/your-app/pyproject.toml`:**

```toml
[project]
name = "your-app"
dependencies = [
    "tools",  # ⬅️ 声明依赖
]

[tool.uv.sources]
tools = { workspace = true }  # ⬅️ 指定 workspace 源
```

### Step 2: 添加到 workspace

**根目录 `pyproject.toml`:**

```toml
[tool.uv.workspace]
members = [
    "apps/your-app",  # ⬅️ 添加这行
    "libs/tools",
]
```

### Step 3: 同步并使用

```bash
# 重新同步依赖
uv sync

# 在代码中导入
# apps/your-app/main.py
from tools import get_current_time, calculator

# 完成！
```

---

## 💡 设计理念

### 核心价值

`★ Insight ─────────────────────────────────────`

**传统问题：**

- ❌ 每个项目都有自己的 `tools.py`
- ❌ 代码重复，修改需要同步多个文件
- ❌ 维护困难，容易出现不一致

**Workspace 解决方案：**

- ✅ 工具定义集中在 `libs/tools`
- ✅ 所有项目共享同一份代码
- ✅ 以 editable 模式安装，修改立即生效
- ✅ 零发布成本，无需打包上传 PyPI

`─────────────────────────────────────────────────`

### 关键特性

| 特性         | 说明                   |
| ------------ | ---------------------- |
| **共享代码** | 1 份代码，所有应用使用 |
| **零复制**   | 无需复制 tools.py      |
| **统一环境** | 所有应用共享根 .venv   |
| **即时生效** | 修改工具后无需重装     |
| **类型安全** | 完整的类型提示支持     |
| **纯函数**   | 无副作用，易于测试     |

### 对比：之前 vs 现在

#### 之前（代码重复）

```
apps/05-chainlit-tool-call/tools.py    # 58 行，有 print
apps/06-tui-tool-call/tools.py         # 49 行，无 print（不一致！）

问题：
- ❌ 代码重复 2 份
- ❌ 修改需要同步 2 个文件
- ❌ print 语句不一致
- ❌ 容易出现 bug
```

#### 现在（Workspace）

```
libs/tools/src/tools/common.py         # 49 行共享代码

优势：
- ✅ 代码只有 1 份
- ✅ 修改 1 次，所有应用生效
- ✅ 一致的行为
- ✅ 易于维护
```

---

## ⚙️ 配置详解

### 项目结构

```
251121-langchain-study/
├── .venv/                       # 统一的虚拟环境
├── pyproject.toml               # Workspace 根配置
├── libs/
│   └── tools/                   # 📚 共享工具库
│       ├── src/tools/
│       │   ├── __init__.py      # 公共 API
│       │   ├── common.py        # 工具实现
│       │   └── py.typed         # 类型标记
│       ├── pyproject.toml       # 库配置
│       └── README.md            # 本文档
└── apps/
    ├── 05-chainlit-tool-call/   # Web 应用
    │   ├── pyproject.toml       # 引用 tools
    │   └── main.py
    └── 06-tui-tool-call/        # TUI 应用
        ├── pyproject.toml       # 引用 tools
        └── main.py
```

### Workspace 配置

#### 1. 根配置

**`pyproject.toml` (root):**

```toml
[tool.uv.workspace]
members = [
    "apps/05-chainlit-tool-call",
    "apps/06-tui-tool-call",
    "libs/tools",              # 工具库
]
```

#### 2. 工具库配置

**`libs/tools/pyproject.toml`:**

```toml
[project]
name = "tools"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "langchain-core>=1.0.0",   # 工具依赖
]

[build-system]
requires = ["uv_build>=0.9.11,<0.10.0"]
build-backend = "uv_build"
```

#### 3. 应用配置

**`apps/06-tui-tool-call/pyproject.toml`:**

```toml
[project]
name = "06-tui-tool-call"
dependencies = ["tools"]       # 声明依赖

[tool.uv.sources]
tools = { workspace = true }   # 指定 workspace 源
```

### 使用指南

#### 安装依赖（根目录）

```bash
# ⚠️ 重要：在根目录运行，不是 app 目录！
uv sync

# uv 会自动：
# 1. 解析所有 workspace 成员的依赖
# 2. 创建统一的虚拟环境（在根目录）
# 3. 以 editable 模式安装所有 workspace 成员
# 4. 安装所有依赖（去重）
```

#### 运行应用（从根目录）

```bash
# ✅ 推荐：从根目录运行
uv run apps/06-tui-tool-call/main.py
uv run python apps/05-chainlit-tool-call/main.py

# ❌ 不推荐（虽然也能工作）
cd apps/06-tui-tool-call && uv run python main.py
```

**重要：**

- ✅ 所有应用共享根环境
- ✅ 无需为每个 app 创建 venv
- ✅ 从根目录直接运行任何应用
- ✅ 依赖统一管理，避免冲突

#### 验证安装

```bash
# 测试导入
uv run python -c "from tools import get_current_time, calculator; print('✅ Success')"

# 测试功能
uv run python -c "
from tools import calculator
result = calculator.invoke({'expression': '2 + 3 * 4'})
print(result)
"
# 输出: 计算结果: 2 + 3 * 4 = 14
```

---

## 🔍 技术细节

### 纯函数设计

工具库中的函数是纯函数，不包含副作用：

```python
# libs/tools/src/tools/common.py
@tool
def calculator(expression: str) -> str:
    """执行数学计算。"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"
    # ✅ 没有 print()
    # ✅ 没有文件 I/O
    # ✅ 没有全局状态修改
```

**好处：**

- 应用层可以自由决定如何处理输出（打印、日志、UI 展示）
- 易于测试
- 可重用性强

### Editable 模式

Workspace 成员以 editable 模式安装：

```bash
# 查看安装位置
uv run python -c "import tools; print(tools.__file__)"
# 输出: /apps/data/workspace/.../libs/tools/src/tools/__init__.py

# 修改 libs/tools/src/tools/common.py 后
# 无需重新安装，立即生效！
```

### uv Workspace 工作原理

#### 1. 依赖解析

```bash
# 当运行 uv sync 时
uv sync

# uv 解析依赖链：
06-tui-tool-call
  └── tools (workspace)
        └── langchain-core>=1.0.0 (PyPI)
```

#### 2. 安装模式

```bash
# Workspace 成员以 editable 模式安装
pip list | grep tools
# tools  0.1.0  /path/to/libs/tools

# 等价于：pip install -e libs/tools
```

#### 3. 导入机制

```python
# Python 导入路径
import sys
print(sys.path)
# [..., '/path/to/libs/tools/src', ...]

# 导入时直接读取源文件
from tools import calculator
# → /path/to/libs/tools/src/tools/__init__.py
#   → /path/to/libs/tools/src/tools/common.py
```

### Workspace vs Path Dependencies

```toml
# 方式 1: Workspace (✅ 推荐)
[tool.uv.sources]
tools = { workspace = true }

# 方式 2: Path (❌ 不推荐)
[tool.uv.sources]
tools = { path = "../../libs/tools" }
```

**Workspace 的优势：**

- ✅ 统一依赖解析（避免冲突）
- ✅ 更好的 IDE 支持
- ✅ 语义更清晰

---

## 🎓 最佳实践

### 添加新工具

```python
# Step 1: 在 libs/tools/src/tools/common.py 中定义
from langchain_core.tools import tool

@tool
def my_new_tool(param: str) -> str:
    """工具说明。

    Args:
        param: 参数说明

    Returns:
        结果说明
    """
    return f"Result: {param}"

# Step 2: 在 libs/tools/src/tools/__init__.py 中导出
from tools.common import get_current_time, calculator, my_new_tool

__all__ = ["get_current_time", "calculator", "my_new_tool"]

# Step 3: 在应用中使用（无需重新安装！）
from tools import my_new_tool
```

### 添加工具依赖

```toml
# libs/tools/pyproject.toml
[project]
dependencies = [
    "langchain-core>=1.0.0",
    "pytz>=2024.0",           # 新增依赖
]

# 然后在根目录运行
uv sync  # 自动安装 pytz
```

### 版本更新

```toml
# libs/tools/pyproject.toml
[project]
version = "0.2.0"  # 更新版本

# 无需其他操作，所有应用自动使用新版本
```

### 统一版本管理

```bash
# 在 libs/tools 中修改
vim libs/tools/src/tools/common.py

# 所有应用立即获得更新（editable 模式）
# - apps/05-chainlit-tool-call ✅
# - apps/06-tui-tool-call ✅
# - 未来的其他应用 ✅
```

---

## ❓ 常见问题

### Q: 修改工具后需要重新安装吗？

**A:** 不需要！Workspace 成员以 editable 模式安装，修改立即生效。

```bash
# 修改工具
vim libs/tools/src/tools/common.py

# 立即生效，无需重装
uv run apps/06-tui-tool-call/main.py
```

### Q: 能否在应用目录下运行？

**A:** 可以，但推荐从根目录运行：

```bash
# ✅ 推荐（从根目录）
uv run apps/06-tui-tool-call/main.py

# ❌ 不推荐（虽然也能工作）
cd apps/06-tui-tool-call && uv run python main.py
```

**原因：**

- 统一的工作流
- 避免路径混淆
- 更清晰的项目结构

### Q: 如何添加新工具？

**A:** 三步搞定：

1. 在 `libs/tools/src/tools/common.py` 中定义工具
2. 在 `libs/tools/src/tools/__init__.py` 中导出
3. 在应用中直接使用（无需重装）

### Q: Workspace 和普通 pip install 有什么区别？

**A:**

| 特性     | pip install   | workspace  |
| -------- | ------------- | ---------- |
| 安装位置 | site-packages | 源代码目录 |
| 修改生效 | 需要重装      | 立即生效   |
| 依赖管理 | 独立          | 统一解析   |
| 适用场景 | 外部包        | 内部库     |

---

## 🐛 故障排查

### 问题 1: 导入失败

```bash
# 错误
ImportError: No module named 'tools'

# 解决
uv sync  # 在根目录重新同步
```

### 问题 2: 修改不生效

```bash
# 确认是 editable 安装
uv run python -c "import tools; print(tools.__file__)"
# 应该指向: .../libs/tools/src/tools/__init__.py

# 如果不是，重新同步
uv sync
```

### 问题 3: workspace 未找到

```bash
# 错误
`tools` references a workspace but is not a workspace member

# 解决：检查根 pyproject.toml
[tool.uv.workspace]
members = [
    "libs/tools",  # ⬅️ 确保包含
    "apps/your-app",
]
```

### 问题 4: 依赖冲突

```bash
# 错误
Conflicting dependencies for package X

# 解决：检查所有 workspace 成员的依赖
# 确保版本兼容，或在根 pyproject.toml 中统一版本
```

---

## 📊 总结

### Workspace 的三大核心价值

1. **DRY 原则** - Don't Repeat Yourself

   - 1 份代码，多处使用
   - 代码量减少 54%（107 行 → 49 行）

2. **零成本共享** - Zero-cost Sharing

   - 无需发布到 PyPI
   - 无需管理版本冲突
   - Editable 模式，修改即生效

3. **开发体验** - Developer Experience
   - 统一的虚拟环境
   - 从根目录运行
   - 更好的代码组织

### 适用场景

- ✅ Monorepo 项目
- ✅ 多个相关应用共享代码
- ✅ 内部工具库
- ✅ 快速原型开发

### 已迁移项目

- ✅ `apps/05-chainlit-tool-call` - Web 界面工具调用
- ✅ `apps/06-tui-tool-call` - 终端界面工具调用

---

## 📈 统计数据

| 指标       | 之前 | 现在 | 改进    |
| ---------- | ---- | ---- | ------- |
| 工具文件数 | 2    | 1    | -50%    |
| 代码行数   | 107  | 49   | -54%    |
| 修改点     | 2    | 1    | -50%    |
| 一致性     | ❌   | ✅   | 100% ⬆️ |
| 维护成本   | 高   | 低   | 大幅 ⬇️ |

---

**从代码重复到集中管理，从手动同步到自动共享。**

**uv workspace 让代码复用变得简单高效！** 🚀

---

_Version: 0.1.0 | Updated: 2025-11-22_
