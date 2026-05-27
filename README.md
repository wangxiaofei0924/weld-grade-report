\# 钢结构焊缝缺陷智能识别与损伤评定系统



\## 模块3：基于知识图谱的损伤等级智能评定



基于 Neo4j 图数据库构建钢结构焊缝损伤知识图谱，包含 7 种缺陷类型、4 个损伤等级、11 条评定规则。推理引擎从图谱实时加载规则，输入缺陷量化数据后自动评定损伤等级并输出置信度与判定依据。



\### 技术栈

\- \*\*Neo4j\*\* - 知识图谱存储与规则查询

\- \*\*PyQt5\*\* - 桌面可视化评定界面

\- \*\*Python\*\* - 推理引擎核心逻辑



\---



\## 模块4：智能化检测报告自动生成与追溯



\### 报告自动生成

\- 基于 `python-docx` 的 Word 报告模板引擎

\- 支持自动填充检测概况、焊缝信息、缺陷数据、评定结果、判定依据、养护建议

\- 缺陷图像自动插入、数据表格自动生成



\### 二维码追溯系统

\- 每条焊缝生成唯一二维码

\- 扫码可查看工程信息、缺陷识别结果、损伤等级、历史检测记录

\- 内嵌 Flask Web 服务，PyQt5 界面一键启动/停止



\### 技术栈

\- \*\*python-docx\*\* - Word 报告生成

\- \*\*qrcode + Pillow\*\* - 二维码图片生成

\- \*\*Flask\*\* - 追溯信息 Web 服务

\- \*\*SQLite\*\* - 追溯数据本地存储

\- \*\*PyQt5\*\* - 统一可视化界面



\---



\## 项目结构

SteelWeldProject/

├── scripts/ # 核心代码

│ ├── grading\_ui.py # 主程序：评定+追溯+报告 一体化界面

│ ├── inference\_engine\_neo4j.py # Neo4j知识图谱推理引擎

│ ├── report\_generator.py # Word报告自动生成引擎

│ ├── qr\_manager.py # 二维码生成+数据库管理

│ ├── qr\_server.py # Flask追溯Web服务（备用）

│ ├── integration\_test.py # 全流程联调测试脚本

│ └── demo\_\*.py # 技术预研Demo

├── templates/ # 报告模板

│ └── report\_template.docx # Word报告模板

├── data/ # 数据目录

│ ├── qrcodes/ # 生成的二维码图片

│ └── weld\_trace.db # 追溯信息数据库

├── outputs/ # 生成的检测报告

└── weld-inspection/ # 模块1/2：图像采集与缺陷识别



\---



\## 快速开始



\### 环境要求

\- Python 3.9+

\- Neo4j 数据库



\### 安装依赖

```bash

pip install neo4j pyqt5 python-docx qrcode\[pil] flask sqlalchemy opencv-python

cd scripts

python grading\_ui.py



操作流程：



1\.点击"启动追溯服务"



2\.输入缺陷参数（类型、长度、宽度）



3\.点击"智能评定" → 查看损伤等级和判定依据



4\.点击"生成追溯二维码" → 扫码查看追溯信息



5\.调用报告生成器输出 Word 检测报告



作者

wangxiaofei0924



