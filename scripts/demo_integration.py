import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton,
                             QVBoxLayout, QLabel, QTextEdit)
from neo4j import GraphDatabase

class Neo4jQueryDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neo4j + PyQt5 联调")
        self.resize(500, 400)

        # 连接 Neo4j（确认数据库已启动）
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "hgjlxf21")
        )

        self.btn = QPushButton("查询图谱中的规则")
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("点击按钮查询 Neo4j："))
        layout.addWidget(self.btn)
        layout.addWidget(self.result_display)
        self.setLayout(layout)

        self.btn.clicked.connect(self.query_neo4j)

    def query_neo4j(self):
        query = """
            MATCH (d:Defect)-[r:判定为]->(g:Grade)
            RETURN d.name AS defect, g.name AS grade, r.依据 AS basis
        """
        with self.driver.session() as session:
            results = session.run(query)
            text = ""
            for record in results:
                text += f"缺陷: {record['defect']} → {record['grade']}\n"
                text += f"  依据: {record['basis']}\n\n"

        if not text:
            text = "（图谱为空，请先在 Neo4j Browser 中添加示例数据）"
        self.result_display.setText(text)

    def closeEvent(self, event):
        self.driver.close()
        event.accept()

app = QApplication(sys.argv)
window = Neo4jQueryDemo()
window.show()
sys.exit(app.exec_())