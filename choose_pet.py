# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import (QApplication, QListWidget, QListWidgetItem,
                             QLabel, QVBoxLayout, QWidget, QPushButton , QApplication , QMessageBox)
from PyQt5.QtGui import QPixmap,QIcon,QFont
from PyQt5.QtCore import Qt,QSize

class PetSelectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Choose your desktop pet")
        self.resize(600, 400)

        # 宠物数据（图片路径和名称）
        self.pets = [
            {"name": "Shanghai Jiao Tong University", "image": "pet_sjtu/pet.png"},
            {"name": "Nanjing University", "image": "pet_nju/pet.png"},
            {"name": "Northwestern Polytechnical University", "image": "pet_npu/pet.png"},
            {"name": "Beihang University", "image": "pet_buaa/pet.png"},
            {"name": "Southeast University", "image": "pet_seu/pet.png"},
            {"name": "University of Science and Technology of China", "image": "pet_ustc/pet.png"}
        ]

        # 创建列表控件
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)  # 图标模式
        self.list_widget.setIconSize(QSize(100, 100))
        self.list_widget.setResizeMode(QListWidget.Adjust)  # 自动调整布局

        # 添加宠物项
        for pet in self.pets:
            item = QListWidgetItem(pet["name"])
            item.setIcon(QIcon(QPixmap(pet["image"])))
            item.setData(Qt.UserRole, pet)  # 存储完整数据
            self.list_widget.addItem(item)

        # 确认按钮
        self.btn_confirm = QPushButton("Confirm")
        self.btn_confirm.clicked.connect(self.on_confirm)

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Please choose your desktop pet:"))
        layout.addWidget(self.list_widget)
        layout.addWidget(self.btn_confirm)
        self.setLayout(layout)

    def on_confirm(self):
        selected_item = self.list_widget.currentItem()
        if selected_item:
            pet = selected_item.data(Qt.UserRole)
            with open ("userinfo.txt","a",encoding='utf-8') as f:
                f.write(f'Pet:{pet['name']}\n')
            QMessageBox.information(self, 'Success',f"You have chosen:{pet['name']}")
        else:
            QMessageBox.warning(self, 'Warning',"Please choose a desktop pet first！" )

    def change_pet(self):
        pass
        #TODO：删去txt最后一行，再重新init

        with open("userinfo.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()  # 读取所有行到列表

        if lines:  # 检查文件非空
            lines = lines[:-1]  # 删除最后一行

        with open("userinfo.txt", 'w', encoding='utf-8') as file:
            file.writelines(lines)

        self.initUI()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("SimSun", 12)  # 指定中文字体，但有0个作用（不会搞）
    app.setFont(font)
    window = PetSelectionWindow()
    window.show()
    sys.exit(app.exec_())