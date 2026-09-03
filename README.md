# SchoolHumanPet — 高校拟人桌面宠物

桌面宠物应用。基于 PyQt5，支持拖拽、投喂、聊天。

---

## 快速运行

```powershell
# 1. 复制 .env 模板
Copy-Item .env.example .env
# 2. 编辑 .env，填入你的 OpenRouter / Spark / 心知 Key
notepad .env
# 3. 安装依赖
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# 4. 启动
.\.venv\Scripts\python.exe show_pet.py
```

或直接跑打包版：`.\dist\SchoolHumanPet.exe`（桌面快捷方式 `SchoolHumanPet.lnk`）。

---

## 调用的 API 平台与方式

| 平台 | 用途 | 调用方式 | 端点 | 鉴权方式 |
|---|---|---|---|---|
| **OpenRouter** | **主聊（流式 + 工具调用）** | HTTPS POST（流式 SSE） | `https://openrouter.ai/api/v1/chat/completions` | `Authorization: Bearer <OPENROUTER_API_KEY>` |
| **OpenRouter** | 提取用户画像（轻量调用） | HTTPS POST（一次性） | 同上 | 同上 |
| **Spark 讯飞星火** | 新对话时总结用户画像 | WebSocket | `wss://sparkcube-api.xf-yun.com/v1/customize` | HMAC-SHA256 URL 签名 |
| **Seniverse 心知天气** | 问候气泡 + 天气插件 | HTTPS GET | `https://api.seniverse.com/v3/weather/now.json` | Query `?key=<WEATHER_API_KEY>` |

### 主聊 (OpenRouter)

- 实际请求体（节选）：
  ```json
  {
    "model": "openrouter/free",
    "messages": [...],
    "stream": true,
    "tools": [{
      "type": "function",
      "function": {
        "name": "lookup_school_persona",
        "description": "查询高校角色设定",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}}}
      }
    }],
    "tool_choice": "auto"
  }
  ```
- Method B 两轮：模型返回 `tool_calls` → 本地查 `高校拟人角色.json` → 第二轮带 `tool` 消息回传 → 流式回包。
- 模型默认：`openrouter/free`（可在 `customized/api_config.json` 改 `openrouter.model`）。
- 429 重试：指数退避（2s → 4s → 8s），失败转 Spark 总结。

### 总结 (Spark 讯飞星火)

- 仅 `新对话` 时触发一次。把 `chat_history` 全部 user 消息送入，让模型输出可记忆的 JSON。
- `max` 域 + `v1/customize` 端点；**不传 `functions` 参数**（否则 10006 错误）。

### 天气 (心知 seniverse)

- 端点：`https://api.seniverse.com/v3/weather/now.json?key=KEY&location=city&language=zh-Hans&unit=c`
- 返回示例：`{"results":[{"now":{"text":"阴","temperature":"29"}}]}`
- 调用时机：定时问候气泡（早安 6-11、午安 11-14、晚安 18-22）。

---

## API 密钥保护

**所有密钥只从 `.env` 读取，不再硬编码到源码里。**`.env` 已加入 `.gitignore`。

### 设置方法

1. 复制模板：
   ```powershell
   Copy-Item .env.example .env
   ```
2. 编辑 `.env`，填入你真实的 Key（参考下方变量说明）。
3. 启动程序时会自动加载。

### `.env` 变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter 平台 Key | （无） |
| `SPARK_APPID` | 讯飞应用 ID | `d0232f96` |
| `SPARK_API_KEY` | 讯飞 API Key | （无） |
| `SPARK_API_SECRET` | 讯飞 API Secret | （无） |
| `WEATHER_API_KEY` | 心知天气 Key | `SFVS0KwOgh7YIp_Gt` |

### 加载优先级

1. 环境变量（系统级 `set` / `export`）
2. `.env` 文件
3. `customized/api_config.json`（旧版兼容）

---

## 核心架构

| 层级 | 文件 | 功能 |
|---|---|---|
| 数据 | `高校拟人角色.json` | 72 所高校角色设定（三重索引：校名/人名/别名） |
| 工具 | `method_b_tool.py` | `SCHOOL_PERSONA_TOOL` 工具声明 + `lookup_persona()` 模糊匹配 |
| 系统提示 | `show_pet.py` (`load_character_info`) | 加载南大身份，明确家族成员列表 |
| AI 适配 | `customized/OpenRouterApi.py` | OpenAI 兼容格式，支持 `tools` + 流式 |
| 备用适配 | `customized/SparkApi2.py` | 讯飞星火 WebSocket 流式 |
| UI 对话 | `show_pet.py` (`ChatWorker`) | 双轮对话：第一轮带 tools → 工具调用 → 第二轮 + 结果 |

## 方法 B 两轮流程

```
用户输入 → messages + functions=SCHOOL_PERSONA_TOOL → OpenRouter
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

- 旧版：`customized/api_config.json`（仍在读取，作为 .env 兜底）
- 推荐：`.env` 文件
- 角色数据：`高校拟人角色.json`
- 历史聊天记录：`data/chat_records/chat_YYYYMMDD_HHMMSS.json`（按文件名排序，非 mtime）

## 移动端

`mobile_app.py`（Kivy）+ `buildozer.spec`。**打包安卓需在 WSL**：

```bash
# WSL 里
pip install buildozer
buildozer android debug deploy
```

## 打包桌面端

```powershell
.\.venv\Scripts\pyinstaller.exe pet.spec --clean --distpath dist
```

`pet.spec` 已包含 `pet/`、`高校拟人角色.json`、`userinfo.txt`、`customized/` 资源。

## 注意事项

- 不要把 `.env` 提交到 git（已在 `.gitignore`）
- 心知 `SFVS0KwOgh7YIp_Gt` 是个人免费额度，**严禁外传**
- OpenRouter `openrouter/free` 偶发 429，代码已自动重试
