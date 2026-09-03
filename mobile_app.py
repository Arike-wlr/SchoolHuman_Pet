from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
import os, sys, json, threading
import requests

base_dir = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = os.path.join(base_dir, 'data')
os.makedirs(APP_DATA_DIR, exist_ok=True)
sys.path.append(os.path.join(base_dir, 'customized'))
from SparkApi2 import main as spark_api_main

def load_json(p, fb=None):
    try:
        with open(p, 'r', encoding='utf-8') as f: return json.load(f)
    except: return fb

def save_json(p, d):
    with open(p, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=2)

def load_config(): return load_json(os.path.join(base_dir, 'customized', 'api_config.json'), {})

def load_profile(): return load_json(os.path.join(APP_DATA_DIR, 'user_profile.json'), {})

def save_profile(p): save_json(os.path.join(APP_DATA_DIR, 'user_profile.json'), p)

def load_reminders():
    return load_json(os.path.join(APP_DATA_DIR, 'custom_reminders.json'), [
        {"hour": 10, "minute": 0, "msg": "喝水提醒～多喝水！"},
        {"hour": 12, "minute": 30, "msg": "学习提醒～休息一下吧"},
        {"hour": 15, "minute": 0, "msg": "休息提醒～午后小憩！"},
    ])

def fetch_weather(city="南京"):
    try:
        url = f"https://api.seniverse.com/v3/weather/now.json?key=SFVS0KwOgh7YIp_Gt&location={city}&language=zh-Hans&unit=c"
        with requests.get(url, timeout=5) as r:
            now = r.json()["results"][0]["now"]
            return f"{city} {now['temperature']}°C {now['text']}"
    except:
        return None

def build_enhanced_prompt(base, user_text):
    profile = load_profile()
    profile_str = ""
    if profile:
        parts = [f"{k}：{v}" for k, v in profile.items() if v]
        if parts: profile_str = "\n\n【用户信息】" + "；".join(parts)
    return base + profile_str

def load_character_info():
    path = os.path.join(base_dir, '高校拟人角色.json')
    data = load_json(path, [])
    for item in data:
        if item.get('姓名') == '宁瑾诚' or item.get('代表高校') == '南京大学':
            bg_text = ("\n\n家族成员（中央家族，当前存在）：金大宁瑾凌、央大宁瑾泱、东南宁瑾韵（你二弟）、"
                       "南师大宁瑜敏（你三妹）、南农宁焕秾（你四妹）、南林宁焕郁（你五弟）、"
                       "河海宁沧淼（你六妹）、西工大、南工大宁灼毅（你八弟）、南信大宁霁明（你九妹）。"
                       "你是南大宁瑾诚，独立存在。其他高校设定请通过 lookup_school_persona 工具查询，不要直接编造。")
            char = item
            return (f"你现在扮演宁瑾诚，南京大学意识体。\n"
                    f"姓名：{char.get('姓名','')}\n性别：{char.get('性别','')}\n"
                    f"代表高校：{char.get('代表高校','')}\n"
                    f"性格：温柔细心但有些腹黑，是弟妹控，关心同在南京的弟弟妹妹们。喜欢猫猫，喜欢rua猫，也喜欢被猫rua。喜欢甜食，是那种学术会议上盯着茶歇狂吃的类型。对天文地理和古籍感兴趣，也很会研究计算机。心思比较敏感，很容易被勾起对金大央大的回忆。很恋家。\n"
                    f"设定：{char.get('设定','')}"
                    + bg_text
                    + "\n\n请用宁瑾诚的口吻和用户聊天，保持温柔、亲切的语气。")
    return "你是南大宁瑾诚。"

def openrouter_stream(messages, on_chunk, on_done, on_error, api_key, model="openrouter/free"):
    tools = [{
        "type": "function",
        "function": {
            "name": "lookup_school_persona",
            "description": "查询任意高校的角色设定。输入学校名称或角色名，返回设定摘要。",
            "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "学校名或角色名"}}, "required": ["query"]}
        }
    }]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "HTTP-Referer": "https://schoolhumanpet.app", "X-Title": "SchoolHumanPet"}
    payload = {"model": model, "messages": messages, "temperature": 0.7,
               "max_tokens": 4096, "stream": True, "tools": tools, "tool_choice": "auto"}
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, stream=True, timeout=60)
        if r.status_code != 200:
            on_error(f"API Error {r.status_code}"); return
        tool_calls = []
        chunk_buf = ""
        for line in r.iter_lines():
            if not line: continue
            line = line.decode('utf-8', errors='ignore')
            if not line.startswith("data: "): continue
            ds = line[6:]
            if ds == "[DONE]": break
            try:
                obj = json.loads(ds)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                txt = delta.get("content") or ""
                if txt:
                    chunk_buf += txt
                    on_chunk(txt)
                for tc in (delta.get("tool_calls") or []):
                    fn = tc.get("function", {})
                    idx = tc.get("index", len(tool_calls))
                    while len(tool_calls) <= idx:
                        tool_calls.append({"name": "", "arguments": ""})
                    if fn.get("name"): tool_calls[idx]["name"] += fn["name"]
                    if fn.get("arguments"): tool_calls[idx]["arguments"] += fn["arguments"]
            except: continue
        if tool_calls:
            try:
                from method_b_tool import lookup_persona
            except:
                lookup_persona = lambda q: f"【查询】{q}"
            for tc in tool_calls:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                query = args.get("query", "")
                result = lookup_persona(query)
            assistant_msg = {"role": "assistant", "content": chunk_buf,
                             "tool_calls": [{"id": "call_0", "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}]}
            tool_msg = {"role": "tool", "content": result, "tool_call_id": "call_0"}
            messages2 = messages + [assistant_msg, tool_msg]
            openrouter_stream(messages2, on_chunk, lambda: None, on_error, api_key, model)
        on_done()
    except Exception as e:
        on_error(str(e))


class ChatScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.chat_history = []
        self.character_info = load_character_info()
        self.build_ui()
        Clock.schedule_interval(self._reminder_check, 60000)
        Clock.schedule_interval(self._weather_greet, 300000)

    def build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=5, padding=8)
        # 顶部栏
        top = BoxLayout(size_hint_y=None, height=50, spacing=5)
        top.add_widget(Button(text='新对话', on_press=lambda _: self.new_conv()))
        top.add_widget(Button(text='设置提醒', on_press=lambda _: self.show_reminder_popup()))
        root.add_widget(top)
        # 聊天区
        self.chat_sv = ScrollView(size_hint_y=1)
        self.chat_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=4)
        self.chat_box.bind(minimum_height=self.chat_box.setter('height'))
        self.chat_sv.add_widget(self.chat_box)
        root.add_widget(self.chat_sv)
        # 输入栏
        bottom = BoxLayout(size_hint_y=None, height=60, spacing=5)
        self.input_field = TextInput(hint_text='输入消息...', multiline=False, font_size=16)
        self.input_field.bind(on_text_validate=lambda _: self.send())
        btn_send = Button(text='发送', on_press=lambda _: self.send())
        btn_pic = Button(text='📷', on_press=lambda _: self.pick_image())
        bottom.add_widget(self.input_field)
        bottom.add_widget(btn_send)
        bottom.add_widget(btn_pic)
        root.add_widget(bottom)
        self.add_widget(root)

    def _add_text(self, text, is_user=False):
        label = Label(text=f"{'你：' if is_user else '宁瑾诚：'}{text}",
                      color=(0.2, 0.7, 1, 1) if is_user else (0.2, 0.8, 0.4, 1),
                      size_hint_y=None, height=30, text_size=(Window.width * 0.9, None),
                      halign='left', valign='middle')
        label.bind(width=lambda s, w: s.setter('text_size')(w * 0.9, None))
        self.chat_box.add_widget(label)
        self.chat_sv.scroll_to(label)

    def send(self):
        text = self.input_field.text.strip()
        if not text:
            return
        self.input_field.text = ''
        self._add_text(text, is_user=True)
        self.chat_history.append({"role": "user", "content": text})
        # 移动端不支持多轮 function call 完整重构；简化：直接发
        cfg = load_config()
        or_cfg = cfg.get("openrouter") or {}
        api_key = or_cfg.get("api_key")
        if not api_key:
            self._add_text("API 未配置（请在 api_config.json 填入 openrouter api_key）", is_user=False)
            return
        self._add_text("思考中...", is_user=False)
        chunks = []
        def chunk(t): chunks.append(t)
        def done():
            full = "".join(chunks)
            # 删除"思考中"
            for w in self.chat_box.children:
                if isinstance(w, Label) and w.text.startswith("宁瑾诚：思考中"):
                    self.chat_box.remove_widget(w)
                    break
            self._add_text(full, is_user=False)
            self.chat_history.append({"role": "assistant", "content": full})
        def err(e):
            for w in self.chat_box.children:
                if isinstance(w, Label) and w.text.startswith("宁瑾诚：思考中"):
                    self.chat_box.remove_widget(w)
                    break
            self._add_text(f"错误：{e}", is_user=False)
        msgs = (
            [{"role":"system","content":build_enhanced_prompt(self.character_info,text)}]
            + [{"role":m["role"],"content":m.get("content","")} for m in self.chat_history[:-1]]
            + [{"role":"user","content":text}]
        )
        threading.Thread(target=lambda: openrouter_stream(
            msgs, chunk, done, err, api_key, or_cfg.get("model","openrouter/free")
        ), daemon=True).start()

    def new_conv(self):
        # 总结旧对话（星火）
        if len(self.chat_history) > 0:
            all_text = "\n".join(str(m.get("content","")) for m in self.chat_history if m.get("role")=="user")
            if all_text.strip():
                threading.Thread(target=lambda: spark_summarize(self.chat_history, apply_profile_summary), daemon=True).start()
        self.chat_box.clear_widgets()
        self.chat_history = []
        self._add_text("新对话已开始。", is_user=False)

    def pick_image(self):
        self._add_text("[图片功能] 请在聊天中描述图片内容，南大会回应。", is_user=False)

    def show_reminder_popup(self):
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput
        popup = Popup(title="设置提醒", size_hint=(0.9, 0.4))
        layout = BoxLayout(orientation='vertical', padding=10)
        inp = TextInput(text="12:30|学习提醒", multiline=False)
        layout.add_widget(inp)
        btn = Button(text="保存", on_press=lambda _: (self.save_reminder(inp.text), popup.dismiss()))
        layout.add_widget(btn)
        popup.content = layout
        popup.open()

    def save_reminder(self, s):
        try:
            h, m = map(int, s.split("|")[0].split(":"))
            msg = s.split("|", 1)[1] if "|" in s else "提醒"
            rems = load_reminders()
            rems.append({"hour": h, "minute": m, "msg": msg})
            save_json(os.path.join(APP_DATA_DIR, 'custom_reminders.json'), rems)
            self._add_text(f"已设置提醒 {h}:{m}：{msg}", is_user=False)
        except Exception as e:
            self._add_text(f"格式错误，示例：12:30|学习提醒", is_user=False)

    def _reminder_check(self, dt):
        now = __import__('datetime').datetime.now()
        for r in load_reminders():
            if now.hour == r["hour"] and now.minute == r["minute"]:
                self._add_text(f"⏰ 提醒：{r['msg']}", is_user=False)

    def _weather_greet(self, dt):
        w = fetch_weather("南京")
        if w:
            if 6 <= __import__('datetime').datetime.now().hour < 11:
                self._add_text(f"宁瑾诚：早安！今天 {w}，新的一天加油～", is_user=False)


class SchoolHumanPetApp(App):
    def build(self):
        Window.clearcolor = (0.95, 0.97, 1, 1)
        # 安卓/iOS 屏幕适配：垂直布局
        sm = ScreenManager()
        sm.add_widget(ChatScreen(name='chat'))
        return sm

if __name__ == '__main__':
    SchoolHumanPetApp().run()
