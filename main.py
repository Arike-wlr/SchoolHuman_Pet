import sys
from PyQt5.QtWidgets import QApplication
from login import if_login
app = QApplication(sys.argv)
if_login()
sys.exit(app.exec_())