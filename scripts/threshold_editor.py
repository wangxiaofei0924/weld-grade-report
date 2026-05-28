"""
模块4.6：阈值调整 GUI
从 Neo4j 加载规则，支持双击编辑阈值并保存
"""
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt
from neo4j import GraphDatabase


class ThresholdEditor(QWidget):
    def __init__(self, password="hgjlxf21"):
        super().__init__()
        self.setWindowTitle("规则阈值管理")
        self.resize(750, 500)
        self.driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", password))
        self.rules = []
        self.modified = {}  # {rule_id: new_threshold}

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["规则ID", "缺陷类型", "参数", "运算符", "阈值", "标准出处"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.DoubleClicked)  # 双击编辑

        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("🔄 从 Neo4j 加载规则")
        self.btn_save = QPushButton("💾 保存修改到 Neo4j")
        self.btn_reset = QPushButton("↩ 恢复默认值")
        self.btn_save.setEnabled(False)
        self.btn_reset.setEnabled(False)

        self.btn_load.setStyleSheet("background:#2196F3;color:white;padding:8px 16px;border-radius:4px;font-weight:bold;")
        self.btn_save.setStyleSheet("background:#4CAF50;color:white;padding:8px 16px;border-radius:4px;font-weight:bold;")
        self.btn_reset.setStyleSheet("background:#FF9800;color:white;padding:8px 16px;border-radius:4px;font-weight:bold;")

        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()

        # 状态标签
        self.label_status = QLabel("点击'从 Neo4j 加载规则'开始")
        self.label_status.setStyleSheet("color:#666;")

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(QLabel("📋 规则阈值管理（双击阈值单元格可编辑）"))
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)
        layout.addWidget(self.label_status)
        self.setLayout(layout)

        # 信号
        self.btn_load.clicked.connect(self.load_rules)
        self.btn_save.clicked.connect(self.save_rules)
        self.btn_reset.clicked.connect(self.reset_rules)
        self.table.cellChanged.connect(self.on_cell_changed)

    def load_rules(self):
        """从 Neo4j 加载所有规则"""
        query = """
            MATCH (d:DefectType)-[r:评定规则]->(g:Grade)
            RETURN r.rule_id AS rule_id,
                   d.name AS defect_type,
                   r.param AS param,
                   r.operator AS operator,
                   r.threshold AS threshold,
                   r.source AS source,
                   g.name AS grade
            ORDER BY r.rule_id
        """
        with self.driver.session() as session:
            results = session.run(query)
            self.rules = []
            for record in results:
                self.rules.append({
                    "rule_id": record["rule_id"],
                    "defect_type": record["defect_type"],
                    "param": record["param"],
                    "operator": record["operator"],
                    "threshold": record["threshold"],
                    "source": record["source"],
                    "grade": record["grade"]
                })

        # 填充表格
        self.table.blockSignals(True)  # 暂时禁用信号，避免触发 cellChanged
        self.table.setRowCount(len(self.rules))
        for i, rule in enumerate(self.rules):
            self.table.setItem(i, 0, QTableWidgetItem(rule["rule_id"]))
            self.table.setItem(i, 1, QTableWidgetItem(rule["defect_type"]))
            self.table.setItem(i, 2, QTableWidgetItem(rule["param"]))
            self.table.setItem(i, 3, QTableWidgetItem(rule["operator"]))
            self.table.setItem(i, 4, QTableWidgetItem(str(rule["threshold"])))
            self.table.setItem(i, 5, QTableWidgetItem(rule["source"]))

            # 第4列（阈值）可编辑，其他列只读
            for col in [0, 1, 2, 3, 5]:
                item = self.table.item(i, col)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        self.table.blockSignals(False)
        self.modified = {}
        self.btn_save.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.label_status.setText(f"✅ 已加载 {len(self.rules)} 条规则 | 双击阈值可编辑")
        self.label_status.setStyleSheet("color:#4CAF50;")

    def on_cell_changed(self, row, col):
        """阈值单元格被编辑后记录修改"""
        if col == 4:  # 阈值列
            rule_id = self.table.item(row, 0).text()
            try:
                new_val = float(self.table.item(row, 4).text())
                old_val = self.rules[row]["threshold"]
                if new_val != old_val:
                    self.modified[rule_id] = {"old": old_val, "new": new_val, "row": row}
                    self.btn_save.setEnabled(True)
                    self.btn_reset.setEnabled(True)
                    self.label_status.setText(f"⚠️ 已修改 {len(self.modified)} 条规则，点击'保存修改'生效")
                    self.label_status.setStyleSheet("color:#FF9800;font-weight:bold;")
            except ValueError:
                pass

    def save_rules(self):
        """保存修改到 Neo4j"""
        if not self.modified:
            return

        reply = QMessageBox.question(
            self, "确认保存",
            f"即将修改 {len(self.modified)} 条规则阈值，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        with self.driver.session() as session:
            for rule_id, change in self.modified.items():
                session.run(
                    """
                    MATCH ()-[r:评定规则 {rule_id: $rule_id}]->()
                    SET r.threshold = $new_val
                    """,
                    rule_id=rule_id, new_val=change["new"]
                )
                print(f"  ✅ {rule_id}: {change['old']} → {change['new']}")

        self.modified = {}
        self.btn_save.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.label_status.setText(f"✅ 修改已保存到 Neo4j")
        self.label_status.setStyleSheet("color:#4CAF50;")

    def reset_rules(self):
        """恢复修改前的值"""
        reply = QMessageBox.question(
            self, "确认恢复", "将放弃所有未保存的修改，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.table.blockSignals(True)
        for rule_id, change in self.modified.items():
            row = change["row"]
            self.table.item(row, 4).setText(str(change["old"]))
        self.table.blockSignals(False)
        self.modified = {}
        self.btn_save.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.label_status.setText("↩ 已恢复修改前的值")
        self.label_status.setStyleSheet("color:#666;")

    def closeEvent(self, event):
        self.driver.close()
        event.accept()


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ThresholdEditor(password="hgjlxf21")  # 密码如果改了替换掉
    editor.show()
    sys.exit(app.exec_())