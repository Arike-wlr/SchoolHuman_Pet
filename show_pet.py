from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QDesktopWidget, QMenu, QDialog, QTextEdit, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
import sys
import os
import keyboard
from PyQt5.QtGui import QTransform
from datetime import datetime
import random
import json
import markdown

# Method B 工具调用
from method_b_tool import SCHOOL_PERSONA_TOOL, lookup_persona

if hasattr(sys, '_MEIPASS'):
    base_dir = sys._MEIPASS
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    exe_dir = base_dir

APP_DATA_DIR = os.path.join(exe_dir, 'data')
os.makedirs(APP_DATA_DIR, exist_ok=True)

def migrate_old_records():
    old_history_dir = os.path.join(base_dir, 'customized', 'chat_records')
    new_history_dir = os.path.join(APP_DATA_DIR, 'chat_records')
    os.makedirs(new_history_dir, exist_ok=True)
    
    if os.path.exists(old_history_dir):
        for f in os.listdir(old_history_dir):
            if f.startswith('chat_') and f.endswith('.json'):
                old_path = os.path.join(old_history_dir, f)
                new_path = os.path.join(new_history_dir, f)
                if not os.path.exists(new_path):
                    try:
                        with open(old_path, 'r', encoding='utf-8') as src:
                            data = json.load(src)
                        with open(new_path, 'w', encoding='utf-8') as dst:
                            json.dump(data, dst, ensure_ascii=False, indent=2)
                        print(f"Migrated: {f}")
                    except Exception as e:
                        print(f"Failed to migrate {f}: {e}")

migrate_old_records()

sys.path.append(os.path.join(base_dir, 'customized'))
from SparkApi2 import main as spark_api_main
from OpenRouterApi import main as openrouter_main
from method_b_tool import SCHOOL_PERSONA_TOOL, lookup_persona


class ChatWorker(QThread):
    """两轮对话 Worker（OpenRouter / Spark 双支持）。
    第一轮：发送带 tools 的请求 → 正常回复或 function_call
    收到 function_call → 本地查询 → 第二轮 → 最终回复 emit 给 UI。"""
    response_received = pyqtSignal(str, bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, provider, messages, functions=None, lookup_fn=None, **kwargs):
        """
        provider: 'openrouter' 或 'spark'
        messages: OpenAI-style message list
        functions: tool 声明
        lookup_fn: 本地查询函数
        kwargs: provider 所需参数（openrouter→api_key/model；spark→appid/api_key/api_secret/spark_url/domain）
        """
        super().__init__()
        self.provider = provider
        self.messages = messages
        self.functions = functions
        self.lookup_fn = lookup_fn
        self.kwargs = kwargs

    def _do_round(self, messages):
        """执行一轮请求（OpenRouter）。返回 (content, tool_calls, is_final)。"""
        import requests
        api_key = self.kwargs.get('api_key')
        model = self.kwargs.get('model', 'deepseek/deepseek-chat-v3.1:free')
        tools = None
        if self.functions is not None:
            if isinstance(self.functions, dict) and "name" in self.functions:
                tools = [{"type": "function", "function": self.functions}]
            elif isinstance(self.functions, list):
                tools = [{"type": "function", "function": f} for f in self.functions]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://schoolhumanpet.app",
            "X-Title": "SchoolHumanPet"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": True
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        chunk_buf = ""
        tool_calls_buf = []   # 流式收集 tool_calls

        def emit_chunk(text, is_finished=False):
            self.response_received.emit(text, is_finished)

        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, stream=True, timeout=90
            )
        except Exception as e:
            self.error_occurred.emit(f"请求失败: {e}")
            return "", [], True

        if r.status_code != 200:
            err = r.text[:500]
            print(f"[OpenRouter] HTTP {r.status_code}: {err}")
            self.error_occurred.emit(f"API Error: {r.status_code}")
            return "", [], True

        chunk_buf = ""
        tool_calls_buf = []

        for line in r.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8', errors='ignore')
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                obj = json.loads(data_str)
            except:
                continue
            delta = obj.get("choices", [{}])[0].get("delta", {})
            chunk_text = delta.get("content") or ""
            if chunk_text:
                chunk_buf += chunk_text
                emit_chunk(chunk_text)
            for tc in (delta.get("tool_calls") or []):
                fn = tc.get("function", {})
                idx = tc.get("index", len(tool_calls_buf))
                while len(tool_calls_buf) <= idx:
                    tool_calls_buf.append({"name": "", "arguments": ""})
                if fn.get("name"):
                    tool_calls_buf[idx]["name"] += fn["name"]
                if fn.get("arguments"):
                    tool_calls_buf[idx]["arguments"] += fn["arguments"]

        # 不在此发 finished；run() 在所有轮结束后统一发
        return chunk_buf, tool_calls_buf, False

    def run(self):
        content, tool_calls, _ = self._do_round(self.messages)
        if tool_calls and self.lookup_fn:
            # 第二轮：执行工具 + 追加 tool 消息
            for tc in tool_calls:
                name = tc.get("name", "")
                raw_args = tc.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except:
                    args = {"query": raw_args}
                query = args.get("query", "")
                print(f"[ToolCall] 函数={name}, 查询={query}")
                result = self.lookup_fn(query)
                tool_msg = {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": f"call_{id(tc)}"
                }
                assistant_msg = {"role": "assistant", "content": content}
                if name:
                    raw_str = raw_args if isinstance(raw_args, str) else json.dumps(raw_args)
                    assistant_msg["tool_calls"] = [
                        {"id": f"call_{id(tc)}", "type": "function",
                         "function": {"name": name, "arguments": raw_str}}
                    ]
                followup = self.messages + [assistant_msg, tool_msg]
                self._do_round(followup)
        # 所有轮次结束，发 finished 信号（UI 统一在此重置）
        self.response_received.emit("", True)


class ChatDialog(QDialog):
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Pet Chat")
        self.setMinimumSize(500, 400)

        self.api_config = self.load_api_config()
        self.history_dir = os.path.join(APP_DATA_DIR, 'chat_records')
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = self.get_latest_history_file()
        self.character_info = self.load_character_info()

        self.layout = QVBoxLayout(self)

        self.button_layout = QHBoxLayout()
        self.new_conv_button = QPushButton("New Conversation", self)
        self.new_conv_button.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 6px 15px;
                font: bold 12px Arial;
            }
            QPushButton:hover {
                background-color: #ee5a5a;
            }
        """)
        self.new_conv_button.clicked.connect(self.new_conversation)
        self.button_layout.addWidget(self.new_conv_button)
        self.button_layout.addStretch()
        self.layout.addLayout(self.button_layout)

        self.chat_area = QTextEdit(self)
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 2px solid #0078D7;
                border-radius: 10px;
                padding: 10px;
                font: 20px Arial;
            }
        """)
        self.layout.addWidget(self.chat_area)

        self.input_layout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Type a message...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 2px solid #0078D7;
                border-radius: 5px;
                padding: 8px;
                font: 14px Arial;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        self.input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send", self)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font: bold 14px Arial;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.send_button)

        self.layout.addLayout(self.input_layout)

        self.chat_history = []
        self.is_first_response = False
        self.history_html = ""
        self.load_history()

    def load_api_config(self):
        config_path = os.path.join(base_dir, 'customized', 'api_config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load API config: {e}")
            return None

    def load_character_info(self):
        """从主数据文件查找南大角色（宁瑾诚 / 南京大学），不再依赖旧版拆分的 OC/家族 JSON。"""
        info_path = os.path.join(base_dir, '高校拟人角色.json')
        try:
            with open(info_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            if not data:
                return ""

            # 显式查找南大：按"姓名=宁瑾诚" 或"代表高校=南京大学"
            char = None
            for item in data:
                if item.get('姓名') == '宁瑾诚':
                    char = item
                    break
            if char is None:
                for item in data:
                    if item.get('代表高校') == '南京大学':
                        char = item
                        break
            if char is None:
                print("Character not found: 宁瑾诚 / 南京大学")
                return ""

            # 收集家族成员（南大之外"存在状态=存在"的所有高校）
            family_members = []
            for member in data:
                if member is char:
                    continue
                if member.get('存在状态') == '存在':
                    family_members.append(f"{member.get('姓名','')}（{member.get('代表高校','')}）")

            character_text = f"""你现在扮演宁瑾诚，南京大学意识体。
姓名：{char.get('姓名','')}
性别：{char.get('性别','')}
身高：{char.get('身高','')}
生日：{char.get('生日','')}
代表高校：{char.get('代表高校','')}
地区：{char.get('地区','')}
外貌：{char.get('外貌','')}
性格：温柔细心但有些腹黑，是弟妹控，关心同在南京的弟弟妹妹们。喜欢猫猫，喜欢rua猫，也喜欢被猫rua。喜欢甜食，是那种学术会议上盯着茶歇狂吃的类型。对天文地理和古籍感兴趣，也很会研究计算机。心思比较敏感，很容易被勾起对金大央大的回忆。很恋家。
设定：{char.get('设定','')}"""

            bg_text = f"\n\n家族成员（当前存在）：{'、'.join(family_members)}\n\n注意：当用户提到其他高校时，请调用 lookup_school_persona 工具查询该角色设定，再以南大的口吻回应。"

            return character_text + bg_text + "\n\n请用宁瑾诚的口吻和用户聊天，保持温柔、亲切的语气。"
        except Exception as e:
            print(f"Failed to load character info: {e}")
            return ""

    def get_latest_history_file(self):
        try:
            files = [f for f in os.listdir(self.history_dir) if f.endswith('.json')]
            print(f"DEBUG: Found {len(files)} files: {files}")
            if not files:
                print("DEBUG: No files found, creating new")
                return self.create_new_history_file()
            latest_file = None
            latest_mtime = 0
            for f in files:
                file_path = os.path.join(self.history_dir, f)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_file = f
            if not latest_file:
                print("DEBUG: No valid file found, creating new")
                return self.create_new_history_file()
            file_path = os.path.join(self.history_dir, latest_file)
            print(f"DEBUG: Latest file: {latest_file}, mtime: {latest_mtime}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f"DEBUG: Valid JSON, returning {file_path}")
                        return file_path
                    else:
                        print(f"DEBUG: Not a list, creating new")
            except Exception as e:
                print(f"DEBUG: Failed to load JSON: {e}, creating new")
            return self.create_new_history_file()
        except Exception as e:
            print(f"Failed to get latest history file: {e}")
            return self.create_new_history_file()

    def create_new_history_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.history_dir, f"chat_{timestamp}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return file_path

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.chat_history = json.load(f)
                for msg in self.chat_history:
                    is_user = (msg["role"] == "user")
                    self.append_message(self.username if is_user else "Pet", msg["content"], is_user)
        except Exception as e:
            print(f"Failed to load chat history: {e}")
            self.chat_history = []

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save chat history: {e}")

    def new_conversation(self):
        self.history_file = self.create_new_history_file()
        self.chat_history = []
        self.save_history()
        self.chat_area.clear()
        self.append_message("System", "New conversation started.", is_user=False)

    def closeEvent(self, event):
        self.save_history()
        event.accept()

    # 主角色数据库文件（你存放70+角色的实际文件）
    MASTER_ROLES_FILE = os.path.join(base_dir, "高校拟人角色.json")

    _roles_index_cache = None  # 类级缓存，索引只构建一次

    @classmethod
    def get_roles_index(cls):
        """从主 JSON 构建：{代表高校: 角色信息}, {姓名: 角色信息}, {别名/昵称: 角色信息} 三重索引。"""
        if cls._roles_index_cache is not None:
            return cls._roles_index_cache
        if not os.path.exists(cls.MASTER_ROLES_FILE):
            return {"by_school": {}, "by_name": {}, "by_alias": {}}
        try:
            # 尝试多种编码 (utf-8-sig → utf-8 → gb18030 → gbk)，容忍坏字符
            data = None
            for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
                try:
                    with open(cls.MASTER_ROLES_FILE, 'r', encoding=enc, errors='ignore') as f:
                        content = f.read()
                    data = json.loads(content)
                    break
                except Exception:
                    continue
            if data is None:
                raise ValueError("Unable to parse master roles JSON with any supported encoding")
            index = {"by_school": {}, "by_name": {}, "by_alias": {}}
            for item in data:
                school = item.get("代表高校", "")
                name = item.get("姓名", "")
                alias = item.get("别名", "")
                if school:
                    index["by_school"][school] = item
                if name:
                    index["by_name"][name] = item
                # 别名/昵称可能多个，逗号或顿号分隔
                if alias:
                    for a in alias.replace("，", ",").split(","):
                        a = a.strip()
                        if a:
                            index["by_alias"][a] = item
            cls._roles_index_cache = index
            return index
        except Exception as e:
            print(f"Failed to load master roles: {e}")
            return {"by_school": {}, "by_name": {}, "by_alias": {}}

    def detect_mentioned_personas(self, text):
        """三层匹配：简称/全称/人名/别名/昵称。返回 (角色信息, 命中方式) 列表。"""
        idx = self.get_roles_index()
        hits = []
        # 防御：如果索引加载失败，返回空列表
        if not isinstance(idx, dict) or "by_school" not in idx:
            return hits
        seen_ids = set()

        def add_hit(item, way):
            # 用 id() 避免重复添加同一角色
            if id(item) in seen_ids:
                return
            seen_ids.add(id(item))
            hits.append((item, way))

        # 1) 学校名匹配（简称 + 全称）
        for school, item in idx["by_school"].items():
            if school in text:
                add_hit(item, f"校名:{school}")
            # 简称匹配：取 "南京XX大学" 中 "XX" 部分
            short = school.replace("南京", "").replace("大学", "").replace("学院", "")
            if short and short in text and len(short) >= 2:
                add_hit(item, f"简称:{short}")

        # 2) 人名匹配
        for name, item in idx["by_name"].items():
            if name and name in text:
                add_hit(item, f"人名:{name}")

        # 3) 别名/昵称匹配
        for alias, item in idx["by_alias"].items():
            if alias and alias in text:
                add_hit(item, f"别名:{alias}")

        return hits

    def build_enhanced_system_prompt(self, base_prompt, user_text):
        """在基础设定上附加用户提到的角色数据。"""
        hits = self.detect_mentioned_personas(user_text)
        if not hits:
            return base_prompt

        extra = "\n\n【本轮参考信息】用户提到了以下角色（你仍以宁瑾诚/南大身份回应）：\n\n"
        for item, way in hits:
            school = item.get("代表高校", "?")
            name = item.get("姓名", "?")
            extra += f"--- {school}（{name}）| 匹配方式: {way} ---\n"
            setting = item.get("设定", "")
            # 截取关键摘要，避免 token 爆炸
            snippet = setting[:400] + ("..." if len(setting) > 400 else "")
            extra += f"设定摘要：{snippet}\n\n"
        return base_prompt + extra

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.append_message(self.username, text, is_user=True)
        self.chat_history.append({"role": "user", "content": text})
        self.save_history()
        self.input_field.clear()
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        self.new_conv_button.setEnabled(False)
        self.is_first_response = True

        if not self.api_config:
            self.append_message("System", "API configuration not found!", is_user=False)
            self.send_button.setEnabled(True)
            self.input_field.setEnabled(True)
            return

        messages = []

        if self.character_info:
            # 动态增强 system prompt
            enhanced_prompt = self.build_enhanced_system_prompt(self.character_info, text)
            messages.append({
                "role": "system",
                "content": enhanced_prompt
            })

        for msg in self.chat_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # 使用 OpenRouter（如果配置存在且有效），否则回退到星火
        openrouter_cfg = self.api_config.get("openrouter") if self.api_config else None
        if openrouter_cfg and openrouter_cfg.get("api_key"):
            self.worker = ChatWorker(
                provider="openrouter",
                messages=messages,
                functions=SCHOOL_PERSONA_TOOL,
                lookup_fn=lookup_persona,
                api_key=openrouter_cfg["api_key"],
                model=openrouter_cfg.get("model", "deepseek/deepseek-chat-v3.1:free")
            )
        else:
            self.worker = ChatWorker(
                provider="spark",
                messages=messages,
                functions=SCHOOL_PERSONA_TOOL,
                lookup_fn=lookup_persona,
                api_key=self.api_config.get("APIKey"),
                api_secret=self.api_config.get("APISecret"),
                spark_url=self.api_config.get("Spark_url"),
                domain=self.api_config.get("domain")
            )
        self.worker.response_received.connect(self.on_response)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def append_message(self, sender, content, is_user=False):
        color = "#0078D7" if is_user else "#2ECC71"
        prefix = "You" if is_user else "Pet"
        html_content = markdown.markdown(content)
        msg_html = f'<b><span style="color:{color}">{prefix}:</span></b><br>{html_content}'
        self.history_html += msg_html + "<br>"
        self.chat_area.append(msg_html)

    def on_response(self, content, finished):
        if not content and not finished:
            return
        if self.is_first_response:
            self.current_response = content
            self.chat_area.insertHtml(f'<b><span style="color:#2ECC71">Pet:</span></b><br>')
            self.chat_area.insertHtml(markdown.markdown(content))
            self.is_first_response = False
        else:
            self.current_response += content
            # 直接 append 当前 chunk，避免重渲染整个历史（防跳动）
            self.chat_area.insertHtml(markdown.markdown(content))
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())
        if finished:
            # 完成态：只更新历史缓存
            self.history_html += f'<b><span style="color:#2ECC71">Pet:</span></b><br>{markdown.markdown(self.current_response)}<br>'
            self.chat_history.append({"role": "assistant", "content": self.current_response})
            self.save_history()
            self.send_button.setEnabled(True)
            self.input_field.setEnabled(True)
            self.new_conv_button.setEnabled(True)
            self.input_field.setFocus()

    def on_error(self, error_msg):
        self.append_message("System", f"Error: {error_msg}", is_user=False)
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.new_conv_button.setEnabled(True)

    def on_worker_finished(self):
        pass


class DesktopPet(QWidget):
    def __init__(self, username):
        super().__init__()
        if hasattr(sys, '_MEIPASS'):
            self.base_dir = sys._MEIPASS
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.pet_folder = os.path.join(self.base_dir, "pet")
        self.pet_init = os.path.join(self.pet_folder, "pet.png")
        self.SIZE = 500
        self.username = username
        self.initUI()

        self.dragging = False
        self.is_dragging = False
        self.drag_threshold = 5
        self.drag_pos = QPoint(0, 0)
        self.rotation_angle = 0
        self.middle_dragging = False
        self.middle_drag_start = QPoint(0, 0)
        self.dizzy_path = os.path.join(self.pet_folder, "dizzy.png")
        self.happy_path = os.path.join(self.pet_folder, "happy.png")

        self.mood = 100
        self.hunger = 100
        self.fatigue = 0
        self.stat_timer = QTimer(self)
        self.stat_timer.timeout.connect(self.decay_stats)
        self.stat_timer.start(60000)

        self.gravity = 2500.0
        self.velocity_y = 0.0
        self.falling = False
        self.ground_y = 0

        self.last_greet_time = 0
        self.greet_timer = QTimer(self)
        self.greet_timer.timeout.connect(self.check_time_greet)
        self.greet_timer.start(60000)

        self.right_dragged = False

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        pixmap = QPixmap(self.pet_init)

        scaled_pixmap = pixmap.scaled(self.SIZE, self.SIZE, Qt.KeepAspectRatio)
        self.label.setPixmap(scaled_pixmap)

        self.resize(scaled_pixmap.width(), scaled_pixmap.height())
        screen = QDesktopWidget().screenGeometry()
        x = screen.width() - scaled_pixmap.width() - 100
        y = screen.height() - scaled_pixmap.height() - 100
        self.move(x, y)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)

        self.bubble = BubbleDialog(self)
        self.bubble.hide()

        self.setMouseTracking(True)

    def load_pet_image(self, path):
        if not os.path.exists(path):
            print(f"Error: Image file not found at {path}")
            return False

        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Error: Failed to load image at {path}")
            return False

        scaled_pixmap = pixmap.scaled(self.SIZE, self.SIZE, Qt.KeepAspectRatio)
        self.label.setPixmap(scaled_pixmap)
        self.label.repaint()
        self.update()
        return True

    def greet(self):
        hello_path = os.path.join(self.pet_folder, "hello.png")
        if self.load_pet_image(hello_path):
            self.bubble.setText(f"""Nice to meet you,\n{self.username}!""")
            self.bubble.move_to(self.pos())
            self.bubble.show()
            QTimer.singleShot(3000, self.reset_pet)
            QTimer.singleShot(3000, self.bubble.hide)
        else:
            print(f"Failed to load image at {hello_path}")

    def reset_pet(self):
        if self.falling:
            return
        self.load_pet_image(self.pet_init)

    def animate(self):
        if self.falling:
            dt = 0.1
            self.velocity_y += self.gravity * dt
            new_y = self.y() + self.velocity_y * dt
            if new_y >= self.ground_y:
                new_y = self.ground_y
                self.falling = False
                self.velocity_y = 0.0
                if os.path.exists(self.dizzy_path):
                    self.load_pet_image(self.dizzy_path)
                self.mood = max(0, self.mood - 5)
                QTimer.singleShot(1500, self.reset_pet)
            self.move(self.x(), int(new_y))
            self.bubble.move_to(self.pos())

    def start_fall(self):
        screen = QDesktopWidget().availableGeometry()
        self.ground_y = screen.bottom() - self.height() + 1
        if self.y() < self.ground_y - 5:
            self.velocity_y = 0.0
            self.falling = True
        else:
            if os.path.exists(self.dizzy_path):
                self.load_pet_image(self.dizzy_path)
            QTimer.singleShot(1500, self.reset_pet)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_pos = event.globalPos() - self.pos()
            self.drag_start_pos = event.pos()
            if os.path.exists(self.happy_path):
                self.load_pet_image(self.happy_path)
            event.accept()

        elif event.button() == Qt.RightButton:
            self.middle_dragging = True
            self.middle_drag_start = event.globalPos()
            self.right_drag_start_pos = event.pos()
            self.right_dragged = False
            event.accept()

    def mouseMoveEvent(self, event):
        dragged = os.path.join(self.pet_folder, "浙叠版.png")

        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            self.bubble.move_to(self.pos())

            move_distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if move_distance > self.drag_threshold:
                self.is_dragging = True
                if os.path.exists(dragged):
                    self.load_pet_image(dragged)
            event.accept()

        elif self.middle_dragging and event.buttons() == Qt.RightButton:
            delta = event.globalPos() - self.middle_drag_start
            if (event.pos() - self.right_drag_start_pos).manhattanLength() > self.drag_threshold:
                self.right_dragged = True
            self.rotation_angle += delta.x() * 0.5
            self.middle_drag_start = event.globalPos()
            self.update_rotation()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_dragging:
                self.dragging = False
                self.is_dragging = False
                self.drag_pos = None
                self.start_fall()
            else:
                QTimer.singleShot(1500, self.reset_pet)
        elif event.button() == Qt.RightButton:
            was_dragging = self.middle_dragging
            dragged = self.right_dragged
            self.middle_dragging = False
            if was_dragging and not dragged:
                self.show_context_menu(event.globalPos())

    def decay_stats(self):
        self.mood = max(0, self.mood - 1)
        self.hunger = max(0, self.hunger - 2)
        self.fatigue = min(100, self.fatigue + 1)
        if self.hunger < 30:
            self.mood = max(0, self.mood - 1)
        if self.mood < 20 and not self.falling and not self.dragging:
            if os.path.exists(self.dizzy_path):
                self.load_pet_image(self.dizzy_path)

    def feed(self):
        self.hunger = min(100, self.hunger + 30)
        self.mood = min(100, self.mood + 20)
        if os.path.exists(self.happy_path):
            self.load_pet_image(self.happy_path)
        self.bubble.setText("Yummy!")
        self.bubble.move_to(self.pos())
        self.bubble.show()
        QTimer.singleShot(2000, self.reset_pet)
        QTimer.singleShot(3000, self.bubble.hide)

    def open_chat(self):
        if hasattr(self, 'chat_dialog') and self.chat_dialog.isVisible():
            self.chat_dialog.raise_()
            self.chat_dialog.activateWindow()
        else:
            self.chat_dialog = ChatDialog(self, self.username)
            self.chat_dialog.show()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        feed_action = menu.addAction("Feed")
        chat_action = menu.addAction("Chat")
        action = menu.exec_(pos)
        if action == feed_action:
            self.feed()
        elif action == chat_action:
            self.open_chat()

    def check_time_greet(self):
        now = datetime.now()
        hour = now.hour

        greetings = {
            "morning": [
                f"Good morning,\n{self.username}!",
                f"Morning,\n{self.username}!",
                f"Time to wake up,\n{self.username}!",
                f"Rise and shine,\n{self.username}!",
                f"Start your day,\n{self.username}!",
                f"Good day,\n{self.username}!",
            ],
            "noon": [
                f"Lunch time,\n{self.username}!",
                f"Eat well,\n{self.username}!",
                f"Have a good meal,\n{self.username}!",
                f"Time for lunch,\n{self.username}!",
                f"Bon appétit,\n{self.username}!",
            ],
            "evening": [
                f"Good evening,\n{self.username}!",
                f"Long day,\n{self.username}!",
                f"Relax,\n{self.username}!",
                f"Evening,\n{self.username}!",
                f"Wind down,\n{self.username}!",
                f"Good night soon,\n{self.username}!",
            ],
        }

        if 6 <= hour < 11:
            period = "morning"
        elif 11 <= hour < 14:
            period = "noon"
        elif 18 <= hour < 22:
            period = "evening"
        else:
            return

        elapsed = now.timestamp() - self.last_greet_time
        if elapsed >= 600:
            self.last_greet_time = now.timestamp()
            msg = random.choice(greetings[period])
            self.bubble.setText(msg)
            self.bubble.move_to(self.pos())
            self.bubble.show()
            QTimer.singleShot(3000, self.bubble.hide)

    def update_rotation(self):
        pixmap = QPixmap(self.pet_init)
        if pixmap.isNull():
            print(f"Error: Failed to load image at {self.pet_init}")
            return

        transform = QTransform().rotate(self.rotation_angle)
        rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)

        scaled_pixmap = rotated_pixmap.scaled(self.SIZE, self.SIZE, Qt.KeepAspectRatio)
        self.label.setPixmap(scaled_pixmap)
        self.label.repaint()


class BubbleDialog(QLabel):
    def __init__(self, parent=None, text="Hello!"):
        super().__init__(parent)
        self.setText(text)
        self.setStyleSheet("""
            background-color: white;
            border: 5px solid #0078D7;
            border-radius: 10px;
            padding: 10px;
            margin: 15px;
            font: bold 36px;
        """)
        self.setAlignment(Qt.AlignCenter)
        self.adjustSize()
        self.adjustSize()
        self.resize(self.width() + 200, self.height() + 50)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

    def move_to(self, pos: QPoint):
        self.move(pos.x() + 50, pos.y() - self.height())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet("Arike")
    pet.show()
    pet.greet()
    sys.exit(app.exec_())