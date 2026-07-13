import sys
import os
import json
import random
import threading
from datetime import datetime

if hasattr(sys, '_MEIPASS'):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(base_dir, 'customized'))
from SparkApi2 import main as spark_api_main

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock, mainthread
from kivy.graphics import Color, Ellipse
from kivy.core.window import Window
from kivy.properties import StringProperty, ListProperty

class PetWidget(Widget):
    pet_image = StringProperty("")
    
    def __init__(self, **kwargs):
        super(PetWidget, self).__init__(**kwargs)
        self.dragging = False
        self.drag_start = (0, 0)
        self.pet_folder = os.path.join(base_dir, "pet")
        self.pet_image = os.path.join(self.pet_folder, "pet.png")
        self.size_hint = (None, None)
        self.size = (150, 150)
        
        self.image = Image(source=self.pet_image, size=self.size, allow_stretch=True)
        self.add_widget(self.image)
        
        self.bubble = Label(
            text="",
            size_hint=(None, None),
            size=(200, 80),
            pos=(self.x + self.width, self.y + self.height),
            color=(0, 0, 0, 1),
            font_size=14,
            halign='left',
            valign='middle',
            text_size=(180, None),
            opacity=0
        )
        with self.bubble.canvas.before:
            Color(1, 1, 1, 0.9)
            Ellipse(pos=self.bubble.pos, size=self.bubble.size)
        self.add_widget(self.bubble)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.dragging = True
            self.drag_start = (touch.x - self.x, touch.y - self.y)
            return True
        return super(PetWidget, self).on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if self.dragging:
            self.pos = (touch.x - self.drag_start[0], touch.y - self.drag_start[1])
            self.bubble.pos = (self.x + self.width + 10, self.y + self.height - 40)
            return True
        return super(PetWidget, self).on_touch_move(touch)
    
    def on_touch_up(self, touch):
        if self.dragging:
            self.dragging = False
            return True
        return super(PetWidget, self).on_touch_up(touch)
    
    def show_message(self, message):
        self.bubble.text = message
        self.bubble.opacity = 1
        Clock.schedule_once(self.hide_message, 3)
    
    def hide_message(self, dt):
        self.bubble.opacity = 0
    
    def change_emotion(self, emotion):
        emotions = {
            'happy': os.path.join(self.pet_folder, "happy.png"),
            'dizzy': os.path.join(self.pet_folder, "dizzy.png"),
            'hello': os.path.join(self.pet_folder, "hello.png"),
            'normal': os.path.join(self.pet_folder, "pet.png")
        }
        if emotion in emotions:
            self.image.source = emotions[emotion]

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.username = ""
        self.chat_history = []
        self.history_dir = os.path.join(base_dir, 'customized', 'chat_records')
        os.makedirs(self.history_dir, exist_ok=True)
        self.character_info = self.load_character_info()
        self.api_config = self.load_api_config()
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.chat_area = ScrollView(size_hint=(1, 0.85))
        self.chat_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.chat_box.bind(minimum_height=self.chat_box.setter('height'))
        self.chat_area.add_widget(self.chat_box)
        layout.add_widget(self.chat_area)
        
        input_layout = BoxLayout(size_hint=(1, 0.15), spacing=10)
        self.input_field = TextInput(hint_text="Type your message...", size_hint=(0.75, 1))
        self.send_button = Button(text="Send", size_hint=(0.25, 1), on_press=self.send_message)
        input_layout.add_widget(self.input_field)
        input_layout.add_widget(self.send_button)
        layout.add_widget(input_layout)
        
        self.add_widget(layout)
        
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
        info_path = os.path.join(base_dir, '高校拟人OC_1位角色_2026-07-13.json')
        bg_path = os.path.join(base_dir, '南京高校_2026-07-13.json')
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data:
                    character = data[0]
                    info = f"""你现在扮演宁瑾诚。
角色名称：{character.get('角色名称', '')}
性别：{character.get('性别', '')}
年龄：{character.get('年龄', '')}
身高：{character.get('身高', '')}
外貌：{character.get('外貌', '')}
性格：{character.get('性格', '')}
爱好：{character.get('爱好', '')}
口头禅：{character.get('口头禅', '')}
所属院校：{character.get('所属院校', '')}
身份：{character.get('身份', '')}
简介：{character.get('简介', '')}"""
                    
                    try:
                        with open(bg_path, 'r', encoding='utf-8') as bg_file:
                            bg_data = json.load(bg_file)
                            bg_text = "\n背景设定：\n"
                            for bg_char in bg_data:
                                bg_text += f"- {bg_char.get('角色名称', '')}：{bg_char.get('简介', '')}\n"
                            info += bg_text
                    except:
                        pass
                    return info
        except Exception as e:
            print(f"Failed to load character info: {e}")
        return None
    
    def load_history(self):
        try:
            files = [f for f in os.listdir(self.history_dir) if f.startswith('chat_')]
            if files:
                latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join(self.history_dir, x)))
                file_path = os.path.join(self.history_dir, latest_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.chat_history = json.load(f)
                for msg in self.chat_history:
                    self.add_message(msg["role"], msg["content"])
        except Exception as e:
            print(f"Failed to load history: {e}")
    
    def save_history(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.history_dir, f"chat_{timestamp}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def add_message(self, role, content):
        is_user = role == "user"
        bg_color = (0.2, 0.6, 1, 1) if is_user else (0.9, 0.9, 0.9, 1)
        text_color = (1, 1, 1, 1) if is_user else (0, 0, 0, 1)
        pos_hint = {'right': 1} if is_user else {'left': 1}
        
        label = Label(
            text=content,
            size_hint=(0.8, None),
            size=(self.width * 0.8, 50) if self.width > 0 else (300, 50),
            color=text_color,
            font_size=16,
            halign='left',
            valign='middle',
            text_size=(self.width * 0.75, None) if self.width > 0 else (280, None),
            padding=10,
            pos_hint=pos_hint
        )
        with label.canvas.before:
            Color(*bg_color)
            Ellipse(pos=label.pos, size=label.size)
        label.bind(texture_size=label.setter('size'))
        self.chat_box.add_widget(label)
        Clock.schedule_once(lambda dt: self.chat_area.scroll_y, 0)
    
    def send_message(self, instance):
        message = self.input_field.text.strip()
        if not message:
            return
        
        self.input_field.text = ""
        self.add_message("user", message)
        self.chat_history.append({"role": "user", "content": message})
        
        self.send_button.disabled = True
        
        threading.Thread(target=self.get_ai_response, args=(message,), daemon=True).start()
    
    def get_ai_response(self, message):
        try:
            messages = []
            if self.character_info:
                messages.append({"role": "system", "content": self.character_info})
            for msg in self.chat_history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            appid = self.api_config.get('appid', '')
            api_key = self.api_config.get('api_key', '')
            api_secret = self.api_config.get('api_secret', '')
            domain = "general"
            
            result = spark_api_main(appid, api_key, api_secret, domain, messages)
            
            if result:
                response_text = ""
                for chunk in result:
                    response_text += chunk
                
                self.on_response(response_text)
        except Exception as e:
            self.on_error(str(e))
    
    @mainthread
    def on_response(self, text):
        self.add_message("assistant", text)
        self.chat_history.append({"role": "assistant", "content": text})
        self.save_history()
        self.send_button.disabled = False
    
    @mainthread
    def on_error(self, error_msg):
        self.add_message("system", f"Error: {error_msg}")
        self.send_button.disabled = False

class PetScreen(Screen):
    def __init__(self, **kwargs):
        super(PetScreen, self).__init__(**kwargs)
        self.pet = PetWidget()
        self.pet.center = self.center
        self.add_widget(self.pet)
        
        self.chat_button = Button(
            text="Chat",
            size_hint=(0.2, 0.1),
            pos_hint={'x': 0.4, 'y': 0.05},
            on_press=self.open_chat
        )
        self.add_widget(self.chat_button)
    
    def open_chat(self, instance):
        self.manager.current = 'chat'
    
    def on_enter(self):
        self.pet.center = self.center
        self.pet.change_emotion('hello')
        self.pet.show_message("Nice to meet you!")

class PetApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(PetScreen(name='pet'))
        sm.add_widget(ChatScreen(name='chat'))
        return sm

if __name__ == '__main__':
    PetApp().run()