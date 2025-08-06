# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import (QApplication, QListWidget, QListWidgetItem,
                             QLabel, QVBoxLayout, QWidget, QPushButton , QApplication , QMessageBox)
from PyQt5.QtGui import QPixmap,QIcon,QFont
from PyQt5.QtCore import Qt,QSize
from show_pet import DesktopPet

class PetSelectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.if_chosen()

    def if_chosen(self):
        with open("userinfo.txt","r",encoding="utf_8") as f:
            lines=f.readlines()
        if (len(lines)==2):
            self.initUI()
        elif(len(lines)==3):
            self.ask_change_pet()
            #(DoneTODO:询问是否要换宠物

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
            self.pet = DesktopPet("pet_sjtu/pet.png")
            self.pet.show()
            self.close()
        else:
            QMessageBox.warning(self, 'Warning',"Please choose a desktop pet first！" )

    def ask_change_pet(self):
        # 创建弹窗
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Confirmation of Pet Replacement")
        msg_box.setText("Are you sure you want to change your current pet?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setIcon(QMessageBox.Question)
        # 显示弹窗并获取结果
        response = msg_box.exec_()
        if response == QMessageBox.Yes:
            self.change_pet()
        else:
            self.pet = DesktopPet("pet_sjtu/pet.png")
            self.pet.show()
            self.close()
            #TODO:直接进入相应宠物的界面

    def change_pet(self):
        pass
        #(DoneTODO：删去txt最后一行，再重新init

        with open("userinfo.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()  # 读取所有行到列表

        if lines:  # 检查文件非空
            lines = lines[:-1]  # 删除最后一行

        with open("userinfo.txt", 'w', encoding='utf-8') as file:
            file.writelines(lines)

        self.initUI()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PetSelectionWindow()
    window.show()
    sys.exit(app.exec_())