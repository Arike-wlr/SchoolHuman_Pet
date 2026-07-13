# 高校拟人桌面宠物 · School Human Desktop Pets

一个基于 PyQt5 的桌面宠物应用，角色原型来自**南京高校拟人 OC**世界观。桌面上会住着一位高校意识体——南京大学的「宁瑾诚」，你可以拖拽他、投喂他、和他聊天，他会根据时间主动向你问好。

## 功能一览

### 桌面宠物交互

| 操作 | 效果 |
|------|------|
| **左键拖拽** | 将宠物拖到屏幕任意位置，松手后会有重力下落 + 眩晕动画 |
| **右键拖拽** | 旋转宠物（360° 随意转） |
| **右键点击**（不拖动） | 弹出右键菜单：投喂 / 聊天 |
| **左键单击** | 宠物切换为开心表情 |

### 状态系统

宠物拥有三个随时间衰减的属性：

- **心情值（Mood）**：随时间缓慢下降，饥饿时会加速下降
- **饱食度（Hunger）**：每分钟衰减，低于 30 会影响心情
- **疲劳度（Fatigue）**：随时间累积

投喂可以同时恢复饱食度和心情值。

### AI 角色对话

- 接入**讯飞星火大模型**（Spark Max），支持流式输出
- 角色人设从 JSON 配置文件动态加载，当前角色为**南京大学·宁瑾诚**
- 对话历史自动保存到 `customized/chat_records/` 目录，支持多轮对话和新建会话
- 聊天界面支持 Markdown 渲染

### 定时问候

宠物会根据当前时段（早晨 / 午间 / 晚间）随机发送问候语，每个时段有多条文案随机选择，间隔不少于 10 分钟。

## 快速开始

### 环境要求

- Python 3.10+
- Windows 操作系统（依赖 `keyboard` 库，其余平台需额外适配）

### 安装依赖

```bash
pip install PyQt5 keyboard markdown websocket-client requests
```

### 配置 API 密钥

在 `customized/api_config.json` 中填入你的讯飞星火 API 凭证：

```json
{
    "APPID": "你的 APPID",
    "APIKey": "你的 APIKey",
    "APISecret": "你的 APISecret",
    "Spark_url": "wss://sparkcube-api.xf-yun.com/v1/customize",
    "domain": "max"
}
```

> API 密钥可在 [讯飞开放平台控制台](https://console.xfyun.cn/services/custom_api) 获取。

### 运行

```bash
python main.py
```

首次运行会弹窗询问你的名字，宠物之后会用这个名字称呼你。用户名保存在 `userinfo.txt` 中，删除该文件可重新设置。

### 打包为 EXE

项目已配置 PyInstaller 打包脚本（`pet.spec`）：

```bash
pyinstaller pet.spec
```

生成的可执行文件位于 `dist/SchoolHumanPet.exe`。

## 项目结构

```
SchoolHuman_Pet/
├── main.py                         # 程序入口，处理用户名读取/首次设置
├── show_pet.py                     # 核心：桌面宠物组件 + AI聊天对话框
├── pet.spec                        # PyInstaller 打包配置
├── userinfo.txt                    # 用户名记录（首次运行自动生成）
├── 高校拟人OC_1位角色_2026-07-13.json  # 当前宠物角色设定（宁瑾诚）
├── 南京高校_2026-07-13.json          # 南京高校家族背景设定（世界观）
├── pet/                            # 宠物立绘资源
│   ├── pet.png                     # 默认待机立绘
│   ├── hello.png                   # 打招呼立绘
│   ├── happy.png                   # 开心立绘（被点击/投喂时）
│   ├── dizzy.png                   # 眩晕立绘（摔落/心情低落时）
│   └── 浙叠版.png                   # 拖拽中立绘
├── customized/                     # 讯飞星火 API 相关
│   ├── api_config.json             # API 密钥配置
│   ├── SparkApi2.py                # 星火 WebSocket 调用封装
│   ├── SparkPythondemo.py          # 官方 Demo（参考用）
│   ├── RAG-upload.py               # 知识库上传工具（可选）
│   └── chat_records/               # 聊天历史记录（自动生成）
└── dist/
    └── SchoolHumanPet.exe          # 打包产物
```

## 角色世界观

本项目基于「南京高校拟人 OC」设定，每所南京高校都有一个拟人化角色（意识体），拥有独立的姓名、外貌、性格和 backstory，角色之间存在家族关系。

**当前桌宠角色：宁瑾诚（南京大学）**

> 金色短发紫色挑染，蓝色眼睛。温柔细心但有些腹黑，是弟妹控。喜欢猫猫和甜食，对天文地理和古籍感兴趣。诞生于 1949 年，1952 年继承中央大学记忆成为南京大学意识体。

世界观中包含 20+ 位角色，涵盖南京大学、东南大学、南京师范大学、南京农业大学、南京林业大学、河海大学、南京航空航天大学、南京理工大学等南京高校，以及多所中学和院级意识体。完整设定见 `南京高校_2026-07-13.json`。

## 技术栈

- **PyQt5** — GUI 框架，无边框透明窗口 + 置顶显示
- **讯飞星火大模型** — 对话引擎，WebSocket 流式调用
- **PyInstaller** — 打包为 Windows 可执行文件
- **markdown** — 聊天消息 Markdown 渲染

## 许可证

本项目仅供学习和个人使用。角色设定（OC）版权归创作者所有。
