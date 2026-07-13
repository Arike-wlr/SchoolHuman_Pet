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
import sys
import markdown
sys.path.append(os.path.join(os.path.dirname(__file__), 'customized'))
from SparkApi2 import main as spark_api_main


class ChatWorker(QThread):
    response_received = pyqtSignal(str, bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, appid, api_key, api_secret, spark_url, domain, question):
        super().__init__()
        self.appid = appid
        self.api_key = api_key
        self.api_secret = api_secret
        self.spark_url = spark_url
        self.domain = domain
        self.question = question

    def on_response(self, content, finished):
        self.response_received.emit(content, finished)

    def run(self):
        try:
            spark_api_main(
                appid=self.appid,
                api_key=self.api_key,
                api_secret=self.api_secret,
                Spark_url=self.spark_url,
                domain=self.domain,
                question=self.question,
                on_response=self.on_response
            )
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatDialog(QDialog):
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Pet Chat")
        self.setMinimumSize(500, 400)

        self.api_config = self.load_api_config()
        self.history_dir = os.path.join(os.path.dirname(__file__), 'customized', 'chat_records')
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = self.get_latest_history_file()

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
        self.load_history()

    def load_api_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'customized', 'api_config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load API config: {e}")
            return None

    def get_latest_history_file(self):
        try:
            files = [f for f in os.listdir(self.history_dir) if f.endswith('.json')]
            if not files:
                return self.create_new_history_file()
            files.sort(reverse=True)
            return os.path.join(self.history_dir, files[0])
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
        self.is_first_response = True

        if not self.api_config:
            self.append_message("System", "API configuration not found!", is_user=False)
            self.send_button.setEnabled(True)
            self.input_field.setEnabled(True)
            return

        history_text = ""
        for msg in self.chat_history[:-1]:
            role_prefix = "User: " if msg["role"] == "user" else "Pet: "
            history_text += role_prefix + msg["content"] + "\n"

        full_question = history_text + f"User: {text}"

        question = [
            {
                "type": "text",
                "text": full_question
            }
        ]

        self.worker = ChatWorker(
            appid=self.api_config["APPID"],
            api_key=self.api_config["APIKey"],
            api_secret=self.api_config["APISecret"],
            spark_url=self.api_config["Spark_url"],
            domain=self.api_config["domain"],
            question=question
        )
        self.worker.response_received.connect(self.on_response)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def append_message(self, sender, content, is_user=False):
        color = "#0078D7" if is_user else "#2ECC71"
        prefix = "You" if is_user else "Pet"
        html_content = markdown.markdown(content)
        self.chat_area.append(f'<b><span style="color:{color}">{prefix}:</span></b><br>{html_content}')

    def on_response(self, content, finished):
        if self.is_first_response:
            self.current_response = content
            html_content = markdown.markdown(content)
            self.chat_area.insertHtml(f'<b><span style="color:#2ECC71">Pet:</span></b><br>{html_content}')
            self.is_first_response = False
        else:
            self.current_response += content
            html_content = markdown.markdown(self.current_response)
            cursor = self.chat_area.textCursor()
            cursor.select(cursor.Document)
            cursor.removeSelectedText()
            self.chat_area.insertHtml(f'<b><span style="color:#2ECC71">Pet:</span></b><br>{html_content}')
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())
        if finished:
            self.chat_history.append({"role": "assistant", "content": self.current_response})
            self.save_history()
            self.send_button.setEnabled(True)
            self.input_field.setEnabled(True)
            self.input_field.setFocus()

    def on_error(self, error_msg):
        self.append_message("System", f"Error: {error_msg}", is_user=False)
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)

    def on_worker_finished(self):
        pass


class DesktopPet(QWidget):
    def __init__(self, username):
        super().__init__()
        self.pet_folder = "pet"
        self.pet_init = f"{self.pet_folder}/pet.png"
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
        self.dizzy_path = f"{self.pet_folder}/dizzy.png"
        self.happy_path = f"{self.pet_folder}/happy.png"

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
        hello_path = f"{self.pet_folder}/hello.png"
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
        dragged = f"{self.pet_folder}/浙叠版.png"

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