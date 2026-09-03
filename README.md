# SchoolHumanPet — 高校拟人桌面宠物

桌面宠物应用。基于 PyQt5，支持拖拽、投喂、聊天。

运行时调用：**OpenRouter** (`https://openrouter.ai/api/v1/chat/completions`，模型 `deepseek/deepseek-chat-v3.1:free`)。

星火 WebSocket 适配 (`customized/SparkApi2.py`) 保留备用。

## 运行

```powershell
# 直接运行源码
python show_pet.py

# 或运行已打包的 exe（桌面快捷方式 SchoolHumanPet.lnk 指向 dist/SchoolHumanPet.exe）
.\dist\SchoolHumanPet.exe
```

## 核心架构

| 层级 | 文件 | 功能 |
|---|---|---|
| 数据 | `高校拟人角色.json` | 72 所高校角色设定（三重索引：校名/人名/别名） |
| 工具 | `method_b_tool.py` | `SCHOOL_PERSONA_TOOL` 工具声明 + `lookup_persona()` 模糊匹配 |
| 系统提示 | `show_pet.py` (`load_character_info`) | 加载南大身份，明确家族成员列表 |
| AI 适配 | `customized/OpenRouterApi.py` | OpenAI 兼容格式，支持 `tools` + 流式 |
| 备用适配 | `customized/SparkApi2.py` | 讯飞星火 WebSocket 流式（ 10006 格式问题，未被调用） |
| UI 对话 | `show_pet.py` (`ChatWorker`) | 双轮对话：第一轮带 tools → 工具调用 → 第二轮 + 结果 |

## 方法 B 两轮流程

```
用户输入 → messages + functions=SCHOOL_PERSONA_TOOL → OpenRouter DeepSeek
  ↓
API 判断需要查询 → function_call（不关闭连接）
  ↓
ChatWorker.on_tool_call() → lookup_persona(query) → 查高校拟人角色.json
  ↓
构造 second-round messages + tool_result → _do_round() → 最终回复
  ↓
UI 流式显示 + finished 时重置按钮
```

## 配置

`customized/api_config.json` 包含：
- `openrouter.api_key`：已填入 OpenRouter 凭证
- `openrouter.model`：默认 `openrouter/free`
- 星火凭证（`APPID` / `APIKey` / `APISecret` / `Spark_url` / `domain`）：保留备用

## 数据源

- 唯一权威角色数据：`高校拟人角色.json`
- 历史聊天记录：`data/chat_records/chat_YYYYMMDD_HHMMSS.json`（按文件名排序，非 mtime）
