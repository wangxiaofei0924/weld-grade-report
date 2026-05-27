import sys
from PyQt5.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel("Hello, PyQt5!")
label.resize(400, 300)
label.show()
sys.exit(app.exec_())