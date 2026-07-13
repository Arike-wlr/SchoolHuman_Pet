# 简单示例：使用PyQt5创建基础窗口
from PyQt5.QtWidgets import QApplication, QLabel, QWidget,QDesktopWidget, QMenu
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QPoint
import sys
import os
import keyboard
from PyQt5.QtGui import QTransform
from datetime import datetime
import random
class DesktopPet(QWidget):
    def __init__(self,username):
        super().__init__()
        self.pet_folder = "pet"  # 存储宠物文件夹名
        self.pet_init = f"{self.pet_folder}/pet.png" # 初始形态的图片
        self.SIZE=500  # 初始形态的图片大小
        self.username=username
        self.initUI()

        self.dragging=False
        self.is_dragging=False # 用于区分点击和拖动
        self.drag_threshold = 5  # 拖动阈值（像素）
        self.drag_pos=QPoint(0, 0)
        self.rotation_angle = 0
        self.middle_dragging = False
        self.middle_drag_start = QPoint(0, 0)
        self.dizzy_path=f"{self.pet_folder}/dizzy.png"
        self.happy_path=f"{self.pet_folder}/happy.png"

        # ===== 状态值系统 =====
        self.mood = 100      # 心情值（0-100）
        self.hunger = 100    # 饱食度（0-100）
        self.fatigue = 0     # 疲劳度（0-100，越低越好）
        self.stat_timer = QTimer(self)
        self.stat_timer.timeout.connect(self.decay_stats)
        self.stat_timer.start(60000)  # 每分钟衰减一次

        # ===== 重力掉落 =====
        self.gravity = 2500.0   # 像素/秒²
        self.velocity_y = 0.0
        self.falling = False
        self.ground_y = 0

        # ===== 分时段问候 =====
        self.last_greet_time = 0  # 上次弹出问候的时间戳
        self.greet_timer = QTimer(self)
        self.greet_timer.timeout.connect(self.check_time_greet)
        self.greet_timer.start(60000)  # 每分钟检查一次时段

        # 右键点击/拖动区分
        self.right_dragged = False

    def initUI(self):
        # 设置无边框和置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 加载宠物图像
        self.label = QLabel(self)
        pixmap = QPixmap(self.pet_init)

        scaled_pixmap = pixmap.scaled(self.SIZE, self.SIZE, Qt.KeepAspectRatio)  # 宽度和高度设为500px，保持比例
        self.label.setPixmap(scaled_pixmap)

        # 设置初始位置，让他/她在屏幕右下角显示
        self.resize(scaled_pixmap.width(), scaled_pixmap.height())
        screen = QDesktopWidget().screenGeometry()
        x = screen.width() - scaled_pixmap.width() - 100
        y = screen.height() - scaled_pixmap.height() - 100
        self.move(x, y)

        # 定时器用于动画
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)  # 每100毫秒触发一次

        #对话框，用于听校拟们讲废话
        self.bubble = BubbleDialog(self)  # 初始化对话框(关键：parent=self
        self.bubble.hide()  # 默认隐藏

        self.setMouseTracking(True)  # 在 initUI 中添加以确保鼠标事件能被正确捕获

    def load_pet_image(self,path):
        if not os.path.exists(path):
            print(f"Error: Image file not found at {path}")
            return False

        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Error: Failed to load image at {path}")
            return False

        scaled_pixmap = pixmap.scaled(self.SIZE, self.SIZE, Qt.KeepAspectRatio)  # 宽度和高度设为200px，保持比例
        self.label.setPixmap(scaled_pixmap)
        self.label.repaint()
        self.update()
        return True

    def greet(self):
        #打招呼
        hello_path = f"{self.pet_folder}/hello.png"
        if self.load_pet_image(hello_path):
            self.bubble.setText(f"""Nice to meet you,\n{self.username}!""")  # 更新文本
            self.bubble.move_to(self.pos())  # 移动到宠物旁边
            self.bubble.show()
            QTimer.singleShot(3000, self.reset_pet)
            QTimer.singleShot(3000, self.bubble.hide)
        else:
            print(f"Failed to load image at {hello_path}")

    def reset_pet(self):
        #恢复默认初始形态；下落过程中不复位
        if self.falling:
            return
        self.load_pet_image(self.pet_init)

    def animate(self):
        if self.falling:
            dt = 0.1  # 100ms 一帧
            self.velocity_y += self.gravity * dt
            new_y = self.y() + self.velocity_y * dt
            if new_y >= self.ground_y:
                new_y = self.ground_y
                self.falling = False
                self.velocity_y = 0.0
                # 落地晕眩（无 dizzy 图则直接复位）
                if os.path.exists(self.dizzy_path):
                    self.load_pet_image(self.dizzy_path)
                self.mood = max(0, self.mood - 5)  # 摔一下掉心情
                QTimer.singleShot(1500, self.reset_pet)
            self.move(self.x(), int(new_y))
            self.bubble.move_to(self.pos())

    def start_fall(self):
        """松手后开始重力下落；若已在底部则直接晕眩。"""
        screen = QDesktopWidget().availableGeometry()
        self.ground_y = screen.bottom() - self.height() + 1
        if self.y() < self.ground_y - 5:
            self.velocity_y = 0.0
            self.falling = True
        else:
            # 没有下落空间，沿用原来的晕眩表现
            if os.path.exists(self.dizzy_path):
                self.load_pet_image(self.dizzy_path)
            QTimer.singleShot(1500, self.reset_pet)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging=True
            self.drag_pos=event.globalPos() - self.pos()
            self.drag_start_pos = event.pos()  # 记录按下时的位置
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
        dragged=f"{self.pet_folder}/浙叠版.png"

        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            self.bubble.move_to(self.pos())

            move_distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if move_distance > self.drag_threshold:
                self.is_dragging = True  # 标记为拖动
                if os.path.exists(dragged):
                    self.load_pet_image(dragged)  # 切换为拖动状态
            event.accept()

        elif self.middle_dragging and event.buttons() == Qt.RightButton:
            delta = event.globalPos() - self.middle_drag_start
            if (event.pos() - self.right_drag_start_pos).manhattanLength() > self.drag_threshold:
                self.right_dragged = True  # 标记为右键拖动（旋转），不弹菜单
            self.rotation_angle += delta.x() * 0.5  # 控制旋转速度
            self.middle_drag_start = event.globalPos()
            self.update_rotation()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_dragging:
                self.dragging=False
                self.is_dragging=False
                self.drag_pos=None
                self.start_fall()  # 松手后重力下落
            else:
                QTimer.singleShot(1500, self.reset_pet)
        elif event.button() == Qt.RightButton:
            was_dragging = self.middle_dragging
            dragged = self.right_dragged
            self.middle_dragging = False
            # 纯右键点击（无拖动）→ 弹出菜单；右键拖动→已旋转，不弹
            if was_dragging and not dragged:
                self.show_context_menu(event.globalPos())

    # ===== 状态值系统 =====
    def decay_stats(self):
        """每分钟衰减一次状态值。"""
        self.mood = max(0, self.mood - 1)
        self.hunger = max(0, self.hunger - 2)
        self.fatigue = min(100, self.fatigue + 1)
        # 饱食度过低会拖累心情
        if self.hunger < 30:
            self.mood = max(0, self.mood - 1)
        # 心情过低切伤心表情（无专用 sad 图，暂用 dizzy 代替）
        if self.mood < 20 and not self.falling and not self.dragging:
            if os.path.exists(self.dizzy_path):
                self.load_pet_image(self.dizzy_path)

    def feed(self):
        """喂食：恢复饱食度与心情。"""
        self.hunger = min(100, self.hunger + 30)
        self.mood = min(100, self.mood + 20)
        if os.path.exists(self.happy_path):
            self.load_pet_image(self.happy_path)
        self.bubble.setText("Yummy!")
        self.bubble.move_to(self.pos())
        self.bubble.show()
        QTimer.singleShot(2000, self.reset_pet)
        QTimer.singleShot(3000, self.bubble.hide)

    def show_context_menu(self, pos):
        """右键菜单。"""
        menu = QMenu(self)
        feed_action = menu.addAction("Feed")
        action = menu.exec_(pos)
        if action == feed_action:
            self.feed()

    # ===== 分时段问候 =====
    def check_time_greet(self):
        """每分钟检查，每10分钟随机弹出一句问候。"""
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
        if elapsed >= 600:  # 10分钟 = 600秒
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

        # 使用 QTransform 旋转图像
        transform = QTransform().rotate(self.rotation_angle)
        rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)

        # 缩放后设置图像
        scaled_pixmap = rotated_pixmap.scaled(self.SIZE, self.SIZE, Qt.KeepAspectRatio)
        self.label.setPixmap(scaled_pixmap)
        self.label.repaint()

class BubbleDialog(QLabel):
    def __init__(self, parent=None, text="Hello!" ):
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
        """移动到指定位置（宠物右上角）"""
        self.move(pos.x() + 50, pos.y() - self.height())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet("Arike")  # 直接运行本文件时的测试用例
    pet.show()
    pet.greet()
    sys.exit(app.exec_())