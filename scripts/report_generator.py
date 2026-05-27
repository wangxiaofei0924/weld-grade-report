"""
模块4.2：智能化报告自动生成引擎
"""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime
import os


class ReportGenerator:
    """检测报告自动生成器"""

    def __init__(self, template_path=None):
        if template_path is None:
            template_path = r"D:\SteelWeldProject\templates\report_template.docx"
        self.template_path = template_path

    def generate(self, data, output_path=None):
        """
        根据模板和数据生成报告
        :param data: dict, 包含所有占位符的值
        :param output_path: 输出路径
        :return: 生成的docx文件路径
        """
        doc = Document(self.template_path)

        # 构建替换映射
        replacements = {
            "{{PROJECT_NAME}}": data.get("project_name", ""),
            "{{DETECT_DATE}}": data.get("detect_date", ""),
            "{{REPORT_DATE}}": datetime.now().strftime("%Y年%m月%d日"),
            "{{BRIDGE_TYPE}}": data.get("bridge_type", ""),
            "{{STANDARDS}}": data.get("standards", "JTG 5210 / GB/T 11345 / GB/T 3323"),
            "{{EQUIPMENT}}": data.get("equipment", "X射线数字成像检测系统"),
            "{{WELD_ID}}": data.get("weld_id", ""),
            "{{WELD_POSITION}}": data.get("weld_position", ""),
            "{{WELD_TYPE}}": data.get("weld_type", ""),
            "{{PLATE_THICKNESS}}": data.get("plate_thickness", ""),
            "{{DETECT_METHOD}}": data.get("detect_method", "X射线检测"),
            "{{DEFECT_COUNT}}": str(len(data.get("defects", []))),
            "{{OVERALL_GRADE}}": data.get("overall_grade", ""),
            "{{CONFIDENCE}}": str(data.get("confidence", "")),
            "{{JUDGMENT_BASIS}}": data.get("judgment_basis", ""),
            "{{MAINTENANCE_ADVICE}}": data.get("maintenance_advice", ""),
        }

        # 替换段落中的占位符
        for para in doc.paragraphs:
            for key, value in replacements.items():
                if key in para.text:
                    para.clear()
                    run = para.add_run(para.text.replace(key, str(value)) if para.text else str(value))
                    run.font.size = para.runs[0].font.size if para.runs else Pt(11)

        # 替换表格中的占位符
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in replacements.items():
                        if key in cell.text:
                            for para in cell.paragraphs:
                                if key in para.text:
                                    para.clear()
                                    para.add_run(para.text.replace(key, str(value)) if para.text else str(value))

        # 处理缺陷表格（{{DEFECT_TABLE_ROWS}}）
        self._fill_defect_table(doc, data.get("defects", []))

        # 处理缺陷详情文本
        self._fill_grade_details(doc, data.get("grade_details", []))

        # 处理缺陷图像占位符
        self._fill_defect_images(doc, data.get("defect_images", []))

        # 保存
        if output_path is None:
            output_path = os.path.join(
                r"D:\SteelWeldProject\outputs",
                f"检测报告_{data.get('weld_id','unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        print(f"✅ 报告已生成: {output_path}")
        return output_path

    def _fill_defect_table(self, doc, defects):
        """填充缺陷量化数据表格"""
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if "{{DEFECT_TABLE_ROWS}}" in cell.text:
                        # 清空该单元格
                        cell.paragraphs[0].clear()
                        # 为每个缺陷添加一行文本
                        for i, d in enumerate(defects, 1):
                            text = f"{i} | {d.get('type','')} | {d.get('length','')} | {d.get('width','')} | {d.get('area','')} | {d.get('position','')} | {d.get('remark','')}"
                            cell.paragraphs[0].add_run(text + "\n")

    def _fill_grade_details(self, doc, grade_details):
        """填充评定详情"""
        text = ""
        for i, gd in enumerate(grade_details, 1):
            text += f"{i}. 缺陷类型：{gd.get('type','')}，评定等级：{gd.get('grade','')}，置信度：{gd.get('confidence','')}\n"
            text += f"   依据：{gd.get('reason','')}\n\n"

        for para in doc.paragraphs:
            if "{{GRADE_DETAILS}}" in para.text:
                para.clear()
                para.add_run(text if text else "暂无详情")

    def _fill_defect_images(self, doc, image_paths):
        """插入缺陷图像"""
        for para in doc.paragraphs:
            if "{{DEFECT_IMAGE_PLACEHOLDER}}" in para.text:
                para.clear()
                if image_paths:
                    for img_path in image_paths:
                        if os.path.exists(img_path):
                            para.add_run(f"[缺陷图像: {os.path.basename(img_path)}]")
                            # 正式版取消注释下面这行来插入真实图片
                            # run = para.add_run()
                            # run.add_picture(img_path, width=Inches(4))
                else:
                    para.add_run("（暂无缺陷图像）")


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    # 模拟数据
    mock_data = {
        "project_name": "某某大桥钢箱梁检测",
        "detect_date": "2024年6月15日",
        "bridge_type": "钢箱梁桥",
        "weld_id": "WELD-2024-001",
        "weld_position": "顶板纵向焊缝",
        "weld_type": "对接焊缝",
        "plate_thickness": "16",
        "standards": "JTG 5210-2021 / GB/T 11345-2013 / GB/T 3323-2005",
        "defects": [
            {"type": "裂纹", "length": "7.5", "width": "0.3", "area": "2.25", "position": "(100,150)", "remark": ""},
            {"type": "气孔", "length": "2.0", "width": "1.5", "area": "3.0", "position": "(200,300)", "remark": ""},
            {"type": "未焊透", "length": "12.0", "width": "3.0", "area": "36.0", "position": "(350,200)", "remark": ""},
        ],
        "overall_grade": "IV类",
        "confidence": 0.85,
        "judgment_basis": "根据GB/T 3323 第X条，未焊透宽度3.0mm＞2.0mm，评定为IV类。",
        "grade_details": [
            {"type": "裂纹", "grade": "III类", "confidence": 0.85, "reason": "根据GB/T 11345，裂纹长度7.5mm＞5.0mm"},
            {"type": "气孔", "grade": "I类", "confidence": 0.95, "reason": "气孔面积3.0mm²＜5.0mm²，未触及降级阈值"},
            {"type": "未焊透", "grade": "IV类", "confidence": 0.85, "reason": "根据GB/T 3323，未焊透宽度3.0mm＞2.0mm"},
        ],
        "maintenance_advice": "建议对IV类损伤焊缝进行返修处理，对III类焊缝加强监测。",
        "defect_images": [],
    }

    gen = ReportGenerator()
    output = gen.generate(mock_data)
    print(f"\n📄 报告文件: {output}")
    print("用 Word 打开查看效果")