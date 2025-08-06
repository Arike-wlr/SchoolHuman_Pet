# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel,
                            QLineEdit, QPushButton, QVBoxLayout,
                            QMessageBox)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Log in")
        self.resize(600, 400)

 # 布局管理器
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)  # 设置边距
        layout.setSpacing(15)  # 控件间距

        # 用户名输入框
        self.label_username = QLabel('Username:')
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Please enter your name(how your desktop pet would call you:")

        # 账号输入框
        self.label_account = QLabel('Account:')
        self.input_account = QLineEdit()
        self.input_account.setPlaceholderText("Please enter your phone number:")

        # 登录按钮
        self.btn_login = QPushButton('Log in')
        self.btn_login.clicked.connect(self.on_login)  # 绑定事件

        # 添加控件到布局
        layout.addWidget(self.label_username)
        layout.addWidget(self.input_username)
        layout.addWidget(self.label_account)
        layout.addWidget(self.input_account)
        layout.addWidget(self.btn_login)

        self.setLayout(layout)

    def on_login(self):
        """登录按钮点击事件"""
        username = self.input_username.text().strip()
        account = self.input_account.text().strip()

        if not username or not account:
            QMessageBox.warning(self, 'Warning', 'Your name and account cannot be empty!')
        else:
            with open ("userinfo.txt","w",encoding='utf-8') as f:
                f.write(f'Account:{account}\n')
                f.write(f'Username:{username}\n')
            QMessageBox.information(self, 'Success', f'Welcome,{username}')

def if_login():
    file_name = "userinfo.txt"  # 目标文件名
    current_dir = os.getcwd()  # 获取当前路径
    file_path = os.path.join(current_dir, file_name)  # 拼接完整路径

    if os.path.isfile(file_path):  # 检查是否为文件
        pass #直接进入
    else:
        window = LoginWindow()
        window.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    if_login()
    sys.exit(app.exec_())