"""
模块3+4.3：损伤等级评定 + 二维码追溯 + 内嵌Flask服务 - PyQt5 完整版
"""
import sys
import os
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QComboBox,
                             QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QGroupBox, QFormLayout, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from flask import Flask, render_template_string

from inference_engine_neo4j import Neo4jDamageGrader
from qr_manager import init_database, add_weld_record, generate_qr, get_weld_info

# ============================================
# Flask 应用（内嵌）
# ============================================
flask_app = Flask(__name__)

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>焊缝追溯信息 - {{ record.weld_id }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 700px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: #2196F3; color: white; padding: 25px; text-align: center; }
        .header h1 { font-size: 22px; margin-bottom: 5px; }
        .header p { font-size: 14px; opacity: 0.9; }
        .content { padding: 25px; }
        .section { margin-bottom: 20px; }
        .section h2 { font-size: 16px; color: #333; border-left: 4px solid #2196F3; padding-left: 10px; margin-bottom: 12px; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .info-item { background: #f9f9f9; padding: 10px 14px; border-radius: 6px; }
        .info-item label { font-size: 12px; color: #888; display: block; margin-bottom: 3px; }
        .info-item span { font-size: 15px; color: #333; font-weight: bold; }
        .grade { display: inline-block; padding: 4px 16px; border-radius: 20px; font-size: 18px; font-weight: bold; color: white; }
        .grade-I { background: #4CAF50; } .grade-II { background: #FFC107; color: #333; }
        .grade-III { background: #FF9800; } .grade-IV { background: #F44336; }
        .history-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .history-table th { background: #eee; padding: 10px; text-align: left; }
        .history-table td { padding: 10px; border-bottom: 1px solid #eee; }
        .basis { background: #FFF9C4; padding: 12px; border-radius: 6px; font-size: 14px; line-height: 1.6; }
        .footer { text-align: center; padding: 15px; color: #aaa; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>🔍 焊缝追溯信息</h1><p>{{ record.weld_id }}</p></div>
        <div class="content">
            <div class="section">
                <h2>📋 工程信息</h2>
                <div class="info-grid">
                    <div class="info-item"><label>工程名称</label><span>{{ record.project_name or '--' }}</span></div>
                    <div class="info-item"><label>检测时间</label><span>{{ record.detect_time or '--' }}</span></div>
                </div>
            </div>
            <div class="section">
                <h2>⚠️ 缺陷识别结果</h2>
                <div class="info-grid">
                    <div class="info-item"><label>缺陷类型</label><span>{{ record.defect_type or '--' }}</span></div>
                    <div class="info-item"><label>缺陷长度</label><span>{{ record.defect_length_mm }} mm</span></div>
                    <div class="info-item"><label>缺陷宽度</label><span>{{ record.defect_width_mm }} mm</span></div>
                    <div class="info-item"><label>缺陷面积</label><span>{{ record.defect_area_mm2 }} mm²</span></div>
                </div>
            </div>
            <div class="section">
                <h2>📊 损伤等级评定</h2>
                <div style="text-align: center; margin: 15px 0;">
                    <span class="grade grade-{{ grade_class }}">{{ record.damage_grade }}</span>
                </div>
                <div style="text-align: center; color: #666; margin-bottom: 10px;">置信度：{{ record.confidence }}</div>
                <div class="basis"><strong>判定依据：</strong><br>{{ record.judgment_basis or '暂无' }}</div>
            </div>
            <div class="section">
                <h2>📜 历史检测记录</h2>
                {% if history %}
                <table class="history-table">
                    <tr><th>检测时间</th><th>损伤等级</th><th>缺陷类型</th></tr>
                    {% for h in history %}
                    <tr><td>{{ h.detect_time or '--' }}</td><td>{{ h.damage_grade or '--' }}</td><td>{{ h.defect_type or '--' }}</td></tr>
                    {% endfor %}
                </table>
                {% else %}<p style="color: #aaa;">暂无历史记录</p>{% endif %}
            </div>
        </div>
        <div class="footer">钢结构焊缝缺陷智能识别与损伤评定系统</div>
    </div>
</body>
</html>
"""

@flask_app.route("/")
def index():
    return """
    <html><body style="font-family:Microsoft YaHei;text-align:center;padding:50px;">
    <h1>🔍 焊缝追溯系统</h1><p>请扫描二维码访问焊缝信息</p>
    </body></html>"""

@flask_app.route("/weld/<weld_id>")
def weld_detail(weld_id):
    info = get_weld_info(weld_id)
    if not info:
        return "<h1>❌ 未找到该焊缝信息</h1>", 404
    record = info["record"]
    history = info["history"]
    grade_map = {"I类":"grade-I","II类":"grade-II","III类":"grade-III","IV类":"grade-IV"}
    grade_class = grade_map.get(record.get("damage_grade",""), "")
    return render_template_string(PAGE_TEMPLATE, record=record, history=history, grade_class=grade_class)


# ============================================
# PyQt5 主界面
# ============================================
class GradingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("钢结构焊缝损伤等级评定与追溯系统")
        self.resize(580, 780)

        init_database()
        self.grader = Neo4jDamageGrader(password="hgjlxf21")
        self.current_result = None
        self.flask_thread = None
        self.flask_running = False

        # ===== 服务器控制区 =====
        group_server = QGroupBox("🌐 追溯服务器")
        server_layout = QHBoxLayout()

        self.btn_server = QPushButton("▶ 启动追溯服务")
        self.btn_server.setStyleSheet("""
            QPushButton { background-color: #FF9800; color: white; padding: 8px 16px;
                border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #F57C00; }
        """)

        self.label_server_status = QLabel("状态：未启动")
        self.label_server_status.setStyleSheet("color: #999;")
        self.label_server_url = QLabel("")

        server_layout.addWidget(self.btn_server)
        server_layout.addWidget(self.label_server_status)
        server_layout.addWidget(self.label_server_url)
        server_layout.addStretch()
        group_server.setLayout(server_layout)

        # ===== 输入区 =====
        group_input = QGroupBox("① 缺陷参数输入")
        form = QFormLayout()
        self.combo_type = QComboBox()
        self.combo_type.addItems(["crack","porosity","lack_of_fusion","slag_inclusion","undercut","incomplete_penetration","pore_cluster"])
        form.addRow("缺陷类型:", self.combo_type)
        self.edit_length = QLineEdit(); self.edit_length.setPlaceholderText("mm")
        form.addRow("长度 (mm):", self.edit_length)
        self.edit_width = QLineEdit(); self.edit_width.setPlaceholderText("mm")
        form.addRow("宽度 (mm):", self.edit_width)
        self.edit_area = QLineEdit(); self.edit_area.setPlaceholderText("mm²（可留空）")
        form.addRow("面积 (mm²):", self.edit_area)
        group_input.setLayout(form)

        # ===== 工程信息区 =====
        group_project = QGroupBox("② 工程信息")
        form2 = QFormLayout()
        self.edit_weld_id = QLineEdit(); self.edit_weld_id.setPlaceholderText("如 WELD-2024-001")
        form2.addRow("焊缝编号:", self.edit_weld_id)
        self.edit_project = QLineEdit(); self.edit_project.setPlaceholderText("如 某某大桥检测")
        form2.addRow("工程名称:", self.edit_project)
        group_project.setLayout(form2)

        # ===== 按钮区 =====
        btn_layout = QHBoxLayout()
        self.btn_grade = QPushButton("🔍 智能评定")
        self.btn_grade.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; padding: 10px 20px;
                border-radius: 6px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_qr = QPushButton("📱 生成追溯二维码")
        self.btn_qr.setEnabled(False)
        self.btn_qr.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px;
                border-radius: 6px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        btn_layout.addWidget(self.btn_grade)
        btn_layout.addWidget(self.btn_qr)

        # ===== 结果区 =====
        group_result = QGroupBox("③ 评定结果")
        result_layout = QVBoxLayout()
        self.label_grade = QLabel("损伤等级：--")
        self.label_grade.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.label_grade.setAlignment(Qt.AlignCenter)
        self.label_confidence = QLabel("置信度：--"); self.label_confidence.setAlignment(Qt.AlignCenter)
        self.label_review = QLabel(""); self.label_review.setAlignment(Qt.AlignCenter)
        self.label_review.setStyleSheet("color: red; font-weight: bold;")
        self.text_reason = QTextEdit(); self.text_reason.setReadOnly(True); self.text_reason.setMaximumHeight(80)
        result_layout.addWidget(self.label_grade)
        result_layout.addWidget(self.label_confidence)
        result_layout.addWidget(self.label_review)
        result_layout.addWidget(QLabel("评定依据："))
        result_layout.addWidget(self.text_reason)
        group_result.setLayout(result_layout)

        # ===== 二维码显示区 =====
        group_qr = QGroupBox("④ 追溯二维码")
        qr_layout = QVBoxLayout()
        self.qr_label = QLabel(); self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumHeight(220); self.qr_label.setText("评定后点击\"生成追溯二维码\"")
        self.qr_info = QLabel(""); self.qr_info.setAlignment(Qt.AlignCenter)
        self.qr_info.setStyleSheet("color: #666;")
        qr_layout.addWidget(self.qr_label)
        qr_layout.addWidget(self.qr_info)
        group_qr.setLayout(qr_layout)

        # ===== 总布局 =====
        main_layout = QVBoxLayout()
        title = QLabel("🔬 钢结构焊缝损伤等级智能评定与追溯系统")
        title.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        main_layout.addWidget(group_server)
        main_layout.addWidget(group_input)
        main_layout.addWidget(group_project)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(group_result)
        main_layout.addWidget(group_qr)
        main_layout.addStretch()
        self.setLayout(main_layout)

        # 信号
        self.btn_server.clicked.connect(self.toggle_server)
        self.btn_grade.clicked.connect(self.do_grading)
        self.btn_qr.clicked.connect(self.generate_qrcode)

        # 样式
        self.setStyleSheet("""
            QGroupBox { font-size: 13px; font-weight: bold; border: 1px solid #ccc;
                border-radius: 6px; margin-top: 8px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLineEdit { padding: 6px; border: 1px solid #ccc; border-radius: 4px; }
            QComboBox { padding: 6px; border: 1px solid #ccc; border-radius: 4px; }
        """)

    def toggle_server(self):
        """一键启动/停止Flask服务"""
        if not self.flask_running:
            self.flask_thread = threading.Thread(
                target=flask_app.run,
                kwargs={"host": "0.0.0.0", "port": 5000, "debug": False, "use_reloader": False},
                daemon=True
            )
            self.flask_thread.start()
            self.flask_running = True
            self.btn_server.setText("⏹ 停止追溯服务")
            self.btn_server.setStyleSheet("""
                QPushButton { background-color: #F44336; color: white; padding: 8px 16px;
                    border-radius: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #D32F2F; }
            """)
            self.label_server_status.setText("状态：✅ 运行中")
            self.label_server_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.label_server_url.setText("http://localhost:5000")
            print("🌐 追溯服务已启动: http://localhost:5000")
        else:
            self.flask_running = False
            self.btn_server.setText("▶ 启动追溯服务")
            self.btn_server.setStyleSheet("""
                QPushButton { background-color: #FF9800; color: white; padding: 8px 16px;
                    border-radius: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #F57C00; }
            """)
            self.label_server_status.setText("状态：已停止")
            self.label_server_status.setStyleSheet("color: #999;")
            self.label_server_url.setText("")
            print("🌐 追溯服务已停止")

    def do_grading(self):
        defect_type = self.combo_type.currentText()
        try:
            length = float(self.edit_length.text()) if self.edit_length.text() else 0
            width = float(self.edit_width.text()) if self.edit_width.text() else 0
        except ValueError:
            QMessageBox.warning(self, "输入错误", "长度和宽度请输入有效数字"); return
        try:
            area = float(self.edit_area.text()) if self.edit_area.text() else length * width
        except ValueError:
            QMessageBox.warning(self, "输入错误", "面积请输入有效数字"); return

        defect = {"defect_type": defect_type, "length_mm": length, "width_mm": width, "area_mm2": area}
        self.current_result = self.grader.grade_defect(defect)
        self.current_result["defect_type"] = defect_type
        self.current_result["length_mm"] = length
        self.current_result["width_mm"] = width
        self.current_result["area_mm2"] = area

        grade = self.current_result["grade"]
        self.label_grade.setText(f"损伤等级：{grade}")
        colors = {"I类":"#4CAF50","II类":"#FFC107","III类":"#FF9800","IV类":"#F44336"}
        self.label_grade.setStyleSheet(f"color: {colors.get(grade,'#000')};")
        self.label_confidence.setText(f"置信度：{self.current_result['confidence']}")
        self.label_review.setText("⚠️ 置信度较低，建议人工复核" if self.current_result["need_review"] else "")
        self.text_reason.setText(self.current_result["reason"])
        self.btn_qr.setEnabled(True)
        self.qr_label.setText("点击右侧按钮生成追溯二维码 →")
        self.qr_info.setText("")

    def generate_qrcode(self):
        if not self.current_result: return
        weld_id = self.edit_weld_id.text().strip()
        if not weld_id:
            QMessageBox.warning(self, "缺少信息", "请输入焊缝编号"); return

        if not self.flask_running:
            QMessageBox.warning(self, "服务未启动", "请先点击\"启动追溯服务\""); return

        data = {
            "weld_id": weld_id,
            "project_name": self.edit_project.text().strip(),
            "detect_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "defect_type": self.current_result.get("defect_type"),
            "defect_length_mm": self.current_result.get("length_mm"),
            "defect_width_mm": self.current_result.get("width_mm"),
            "defect_area_mm2": self.current_result.get("area_mm2"),
            "damage_grade": self.current_result.get("grade"),
            "confidence": self.current_result.get("confidence"),
            "judgment_basis": self.current_result.get("reason")
        }
        add_weld_record(data)
        qr_path = generate_qr(weld_id)

        pixmap = QPixmap(qr_path)
        self.qr_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.qr_info.setText(f"✅ 二维码已保存\n扫码地址: http://localhost:5000/weld/{weld_id}")

    def closeEvent(self, event):
        self.grader.close()
        self.flask_running = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GradingWindow()
    window.show()
    sys.exit(app.exec_())