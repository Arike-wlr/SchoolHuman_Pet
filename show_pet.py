# 简单示例：使用PyQt5创建基础窗口
from PyQt5.QtWidgets import QApplication, QLabel, QWidget,QDesktopWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QPoint
import sys
import os
import keyboard
from PyQt5.QtGui import QTransform
class DesktopPet(QWidget):
    def __init__(self,pet_name,username):
        super().__init__()
        self.pet_name=pet_name.upper()
        self.pet_folder = f"pet_{pet_name}"  # 存储宠物文件夹名
        self.pet_init = f"{self.pet_folder}/pet.png" # 初始形态的图片
        self.SIZE=500  # 初始形态的图片大小
        self.username=username
        self.initUI()

        self.dragging=False
        self.drag_pos=QPoint(0, 0)
        self.rotation_angle = 0
        self.middle_dragging = False
        self.middle_drag_start = QPoint(0, 0)

    def initUI(self):
        # 设置无边框和置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 加载宠物图像
        self.label = QLabel(self)
        pixmap = QPixmap(self.pet_init)

        scaled_pixmap = pixmap.scaled(self.SIZE, self.SIZE, Qt.KeepAspectRatio)  # 宽度和高度设为200px，保持比例
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
        self.bubble = BubbleDialog(self, self.username,self.pet_name)  # 初始化对话框(关键：parent=self
        self.bubble.hide()  # 默认隐藏

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
        else:
            print(f"Failed to load image at {hello_path}")

    def reset_pet(self):
        #恢复默认初始形态
        self.load_pet_image(self.pet_init)

    def animate(self):
        pass


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging=True
            self.drag_pos=event.globalPos() - self.pos()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.middle_dragging = True
            self.middle_drag_start = event.globalPos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            self.bubble.move_to(self.pos())
            event.accept()
        elif self.middle_dragging and event.buttons() == Qt.RightButton:
            delta = event.globalPos() - self.middle_drag_start
            self.rotation_angle += delta.x() * 0.5  # 控制旋转速度
            self.middle_drag_start = event.globalPos()
            self.update_rotation()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging=False
            self.drag_pos=None
        elif event.button() == Qt.RightButton:
            self.middle_dragging = False

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
    def __init__(self, uname,pname,parent=DesktopPet, text="Hello!" ):
        super().__init__(parent)
        self.uname=uname
        self.pname=pname
        self.setText(text)
        self.setStyleSheet("""
            background-color: white;
            border: 5px solid #0078D7;
            border-radius: 10px;
            # padding: 5px;
            padding: 10px;  # 增加内边距
            margin: 15px;   # 增加外边距（需配合布局）
            font: bold 36px;
        """)
        self.setAlignment(Qt.AlignCenter)
        self.adjustSize()  # 根据文本调整大小
        self.adjustSize()  # 先根据文本计算基础大小
        self.resize(self.width() + 200, self.height() + 50)  # 增加额外边距
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def move_to(self, pos: QPoint):
        """移动到指定位置（宠物右上角）"""
        self.move(pos.x() + 50, pos.y() - self.height())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet("sjtu","Arike")
    pet.show()
    pet.greet()
    sys.exit(app.exec_())