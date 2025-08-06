import sys
from PyQt5.QtWidgets import QApplication
from login import if_login

app = QApplication(sys.argv)
window=if_login(app)
sys.exit(app.exec_())