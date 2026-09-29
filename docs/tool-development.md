# 工具开发指南

工具（Tool）是桌宠调用外部能力的方式：一个工具目录 = 一组可被 LLM 调用的方法。
本文讲**怎么写一个工具**；现有工具的机械清单（分组、方法、参数）见
[reference/tools.md](reference/tools.md)，工具目录的约定也是
[architecture.md](architecture.md) §11 的第 8 条红线。

想跑测试与提交，见 [../CONTRIBUTING.md](../CONTRIBUTING.md)。

## 目录结构

在 `pet/tools/` 下新建目录：

```
pet/tools/my_tool/
├── __init__.py           # 注册入口（必须）
├── core.py               # 业务实现（推荐，文件名任意）
├── config.example.json   # 私有配置模板（可选，首次加载自动复制为 config.json）
└── requirements.txt      # 私有依赖（可选，首次加载自动安装）
```

- `__init__.py` 必须定义 `TOOL_NAME`、`TOOL_DESCRIPTION`、`register()`；`TOOL_GROUP` 可选（默认 `default`）
- 业务逻辑放哪个文件都行，加载器不关心文件名
- `config.json` 含密钥，已在 `.gitignore` 中；仓库里只提交 `config.example.json`

## register() 模板

```python
from pet.tools.my_tool.core import do_something

TOOL_NAME = "my_tool"
TOOL_DESCRIPTION = "一句话描述工具用途"
TOOL_GROUP = "productivity"  # 工具分组，LLM 通过 tool_search 按需发现

def register(registry):
    registry.register(TOOL_NAME, TOOL_DESCRIPTION)

    registry.add_method(
        TOOL_NAME, "do",
        "执行某操作",
        handler=do_something,
        args={
            "target": {"type": "str", "required": True, "desc": "目标名称"},
            "mode": {"type": "str", "required": False, "default": "fast",
                     "desc": "执行模式", "enum": ["fast", "slow"]},
        },
        timeout=15.0,  # 可选：超时秒数，默认 30s
    )
```

方法的对外调用名是 `工具名__方法名`（双下划线），例如 `my_tool__do`。

## 分组与按需激活

`TOOL_GROUP` 决定工具属于哪个分组，分组是**按需激活**的单位：

- `default` 组的工具始终对模型可见（`tool_search`、`food`、`game`、`recall` 这些元工具都在这里）
- 其余分组默认不激活：模型先用 `tool_search` 的 `list_groups` / `search(keyword)` 探索，
  匹配到哪个分组就激活哪个，之后该组工具才进入它的工具列表

当前分组与各组包含的工具见 [reference/tools.md](reference/tools.md)（生成物，随代码更新，别手抄）。

## 参数定义

`args` 字典里每个参数支持：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `str` | 否 | `str` / `int` / `float` / `bool` / `list` / `dict` / `any`；缺省时 schema 按 `str` 生成，执行器不做类型校验 |
| `required` | `bool` | 否 | 是否必填，默认 `False` |
| `default` | 同 type | 否 | 默认值 |
| `desc` | `str` | 否 | 参数描述（写入 LLM function schema）；写 `description` 也认 |
| `enum` | `list` | 否 | 枚举可选值 |

执行器会按同一份 spec 校验模型传来的参数（类型、必填、枚举），不合法时返回错误给模型而不是抛异常。
参数会自动转换为 OpenAI function calling 格式，模型通过 `tool_calls` 调用。

## 返回值

```python
def do_something(target: str, mode: str = "fast") -> dict:
    return {
        "summary": "操作成功的简短描述",   # LLM 优先读取
        "data": {"result": "..."},        # 结构化数据
    }
```

| 返回类型 | LLM 看到的内容 |
|----------|----------------|
| `dict` 含 `summary` | `summary` 文本 + 其余字段的 JSON |
| `dict` 不含 `summary` | JSON 字符串 |
| `str` | 原始字符串 |
| 其他 | `str(...)` |

三个保留键会被执行器取出、不进入上面的序列化：

| 键 | 作用 |
|---|---|
| `__image__` | base64 图片，作为多模态内容附给模型（见下节） |
| `__image_mime__` | 图片 MIME，默认 `image/png` |
| `__context__` | 一段文本，写入桌宠上下文（`context_brief`），适合放「模型后续应当记得」的短信息 |

## 图片注入（多模态）

```python
import base64

def capture() -> dict:
    return {
        "summary": "截图完成",
        "__image__": base64.b64encode(img_bytes).decode(),
    }
```

系统会把 `__image__` 提取为多模态消息；需要模型支持视觉（用户侧由 `VISION_ENABLED` 控制截图能力，
但工具图片不受该开关影响）。

## 主动调用宠物能力

工具不只能返回文本，还能让桌宠说、动、记：

```python
from pet.tools.context import TOOL_CTX

def alert() -> dict:
    TOOL_CTX.speech("注意！", duration=3000)
    TOOL_CTX.action("bounce", kwargs={"dx": 0, "dy": -200})
    return {"summary": "已提醒"}
```

常用方法（完整清单以 `pet/tools/context.py` 为准）：

| 方法 | 作用 |
|---|---|
| `speech(text, duration=5000)` | 让桌宠说话 |
| `speech_random(texts, duration=3000)` | 随机挑一句；模型本轮已带 `aside` 时自动跳过 |
| `action(name, args, kwargs)` | 触发动作，动作名须在 `pet/action/registry.py` 注册表内 |
| `add_context(text)` | 往上下文追加一条 system 备注 |
| `note_event(kind, text)` | 上报事件，进入「最近发生了什么」章节 |
| `notify(title, message, duration)` | 系统通知 |
| `request_interact(hint, delay_ms, cooldown_ms)` | 请求一次即时交互（会占用脑线程） |
| `register_tick(name, callback)` | 注册随调度器执行的周期回调 |
| `register_alarm(timestamp_ms, callback, key=None)` | 注册一次性闹钟（只存内存，重启即丢；timer 工具能跨重启是它自己落库、启动时重新注册的） |

`note_event` 适合定时器、待办、对局这类「已经发生的事」——同类型只保留最近一次，超出保鲜窗口后不再注入：

```python
TOOL_CTX.note_event("timer", "你设的「吃药」定时器响了")
```

## aside 通用参数

每个方法都会自动附带一个可选参数 `aside`（自言自语）：模型调用工具时可以带一句台词
（如「搜搜看今天天气…」），系统会播给用户听，但**不会**作为正式回复，也**不会**传给 handler。
它是模型「言行统一」的过程性辅助，最终输出的 `Speech` 才是正式答复。

## 启用与禁用

在 `settings.json`（`pet/config.py` 的 `TOOLS_ENABLED`）中配置：

```json
"TOOLS_ENABLED": ["my_tool", "weather"]
```

`["*"]` 启用全部，`[]` 全部禁用。未启用的工具不会出现在模型可见的工具列表中；
元工具（`meta=True`）不可禁用。

## 注意事项

- **参数名严格匹配**：`add_method` 的 `args` 键名必须与 handler 的参数名一致
- **超时保护**：handler 在**单独一条线程**里执行并带 `timeout` 兜底，超时后返回错误（不用线程池）
- **异常隔离**：handler 抛异常会被捕获并转成错误信息给模型，不影响主流程
- **序列化友好**：返回的 dict 必须能被 `json.dumps(ensure_ascii=False)` 序列化
- **不要在导入期做重活**：工具被加载时就会 import，浏览器类工具应把重依赖延迟到调用时
- **跨平台**：路径、通知、系统接口都要考虑 Windows / macOS / Linux

## 写完之后

1. 跑测试：`python -m pytest`（工具相关的用例参考 `tests/test_tools_registry.py`）
2. 重新生成参考表：`python scripts/gen_docs.py`（会刷新 [reference/tools.md](reference/tools.md)）
3. 记得在新工具的文档/说明里写清副作用（会不会改用户文件、联网、开浏览器）
