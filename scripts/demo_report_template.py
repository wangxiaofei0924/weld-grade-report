import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QComboBox,
                             QPushButton, QVBoxLayout, QLabel, QTextEdit)

class ReportPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("报告模板预览")
        self.resize(500, 400)

        # 模板选择下拉框
        self.combo = QComboBox()
        self.combo.addItems(["竣工验收报告模板", "在役检测报告模板"])

        # 预览按钮
        self.btn_preview = QPushButton("预览模板结构")

        # 显示区域
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(QLabel("选择报告模板："))
        layout.addWidget(self.combo)
        layout.addWidget(self.btn_preview)
        layout.addWidget(self.text_area)
        self.setLayout(layout)

        # 信号与槽：点击按钮触发函数
        self.btn_preview.clicked.connect(self.show_template_info)

        # 样式美化
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QComboBox {
                padding: 5px;
            }
        """)

    def show_template_info(self):
        template_name = self.combo.currentText()
        info = f"已选择：{template_name}\n\n包含模块：\n"
        info += "① 检测概况\n"
        info += "② 焊缝基本信息\n"
        info += "③ 缺陷识别结果（含缺陷标注框图像）\n"
        info += "④ 量化数据（缺陷长度、宽度等）\n"
        info += "⑤ 损伤等级评定结果\n"
        info += "⑥ 判定依据（标准条款引用）\n"
        info += "⑦ 养护建议"
        self.text_area.setText(info)

app = QApplication(sys.argv)
window = ReportPreview()
window.show()
sys.exit(app.exec_())