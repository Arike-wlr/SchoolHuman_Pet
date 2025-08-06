# 简单示例：使用PyQt5创建基础窗口
from PyQt5.QtWidgets import QApplication, QLabel, QWidget,QDesktopWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
import sys


class DesktopPet(QWidget):
    def __init__(self,pet):
        super().__init__()
        self.pet=pet
        self.initUI()

    def initUI(self):
        # 设置无边框和置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 加载宠物图像
        self.label = QLabel(self)
        pixmap = QPixmap(self.pet)
        SIZE=200
        scaled_pixmap = pixmap.scaled(SIZE, SIZE, Qt.KeepAspectRatio)  # 宽度和高度设为200px，保持比例
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

    def animate(self):
        # 实现动画逻辑
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet("pet_sjtu/pet.png")
    pet.show()
    sys.exit(app.exec_())