import sys
import os
from PyQt5.QtWidgets import QApplication, QInputDialog
from show_pet import DesktopPet

exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
APP_DATA_DIR = os.path.join(exe_dir, 'data')
os.makedirs(APP_DATA_DIR, exist_ok=True)
USERINFO_FILE = os.path.join(APP_DATA_DIR, "userinfo.txt")


def get_username():
    """读取已保存的用户名；没有则弹窗询问并保存。"""
    if os.path.isfile(USERINFO_FILE):
        with open(USERINFO_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Username:"):
                    name = line.split(":", 1)[1].strip()
                    if name:
                        return name

    # 首次运行：弹窗询问用户名
    name, ok = QInputDialog.getText(
        None,
        "Welcome",
        "Please enter your name (how your desktop pet would call you):",
    )
    if not ok or not name.strip():
        sys.exit(0)  # 用户取消则退出
    name = name.strip()
    with open(USERINFO_FILE, "w", encoding="utf-8") as f:
        f.write(f"Username:{name}\n")
    return name


app = QApplication(sys.argv)
username = get_username()
pet = DesktopPet(username)
pet.show()
pet.greet()
sys.exit(app.exec_())
