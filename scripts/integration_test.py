"""
全流程联调测试：模块1/2 → 模块3 → 模块4
等模块1/2数据就绪后运行此脚本
"""
import sys
sys.path.insert(0, r"D:\SteelWeldProject\weld-inspection")

from src.database.manager import DatabaseManager
from src.acquisition.calibration import px_to_mm
from inference_engine_neo4j import Neo4jDamageGrader, batch_grade
from report_generator import ReportGenerator


def run_full_pipeline(db_path, grader_password="hgjlxf21"):
    """
    全流程：读数据库 → 推理评定 → 生成报告
    """
    print("=" * 60)
    print("全流程联调测试")
    print("=" * 60)

    # ===== 第1步：从模块1/2数据库读取数据 =====
    print("\n[1/4] 读取模块1/2数据...")
    db = DatabaseManager(db_path)
    session = db.get_session()

    from src.database.models import Image, Defect
    images = session.query(Image).all()
    print(f"  找到 {len(images)} 张图像")

    if len(images) == 0:
        print("  ❌ 数据库为空，请先运行模块1/2预处理流程")
        session.close()
        return

    # ===== 第2步：遍历每张图像，转换缺陷数据 =====
    print("\n[2/4] 转换缺陷数据...")
    all_defects = []

    for img in images:
        defects = session.query(Defect).filter(Defect.image_id == img.id).all()
        print(f"  图像{img.id}: {len(defects)}个缺陷, ppm={img.pixel_per_mm}")

        for d in defects:
            # 像素 → 毫米
            length_mm = d.bbox_w / img.pixel_per_mm
            width_mm = d.bbox_h / img.pixel_per_mm
            area_mm2 = (d.bbox_w * d.bbox_h) / (img.pixel_per_mm ** 2)

            all_defects.append({
                "defect_type": d.defect_type,
                "length_mm": round(length_mm, 2),
                "width_mm": round(width_mm, 2),
                "area_mm2": round(area_mm2, 2),
                "image_id": img.id,
                "image_path": img.processed_path
            })

    session.close()
    print(f"  共转换 {len(all_defects)} 条缺陷记录")

    # ===== 第3步：推理评定 =====
    print("\n[3/4] 执行损伤等级评定...")
    summary = batch_grade(all_defects)
    print(f"  总体等级: {summary['overall_grade']}")
    print(f"  需复核: {'是' if summary['need_review'] else '否'}")

    for r in summary["details"]:
        flag = " ⚠️" if r["need_review"] else ""
        print(f"    {r['defect_type']}: {r['grade']} (置信度:{r['confidence']}){flag}")

    # ===== 第4步：生成报告 =====
    print("\n[4/4] 生成检测报告...")
    report_data = {
        "project_name": "联调测试项目",
        "detect_date": "2024年6月",
        "bridge_type": "钢箱梁桥",
        "weld_id": "INTEGRATION-TEST",
        "weld_position": "测试焊缝",
        "weld_type": "对接焊缝",
        "plate_thickness": "16",
        "defects": [
            {"type": d["defect_type"], "length": str(d["length_mm"]),
             "width": str(d["width_mm"]), "area": str(d["area_mm2"]),
             "position": "-", "remark": ""}
            for d in all_defects
        ],
        "overall_grade": summary["overall_grade"],
        "confidence": summary["details"][0]["confidence"] if summary["details"] else 0,
        "judgment_basis": summary["details"][0]["reason"] if summary["details"] else "",
        "grade_details": summary["details"],
        "maintenance_advice": "根据评定结果给出养护建议。",
        "defect_images": [],
    }

    gen = ReportGenerator()
    output = gen.generate(report_data)

    print("\n" + "=" * 60)
    print(f"✅ 全流程完成！报告: {output}")
    print("=" * 60)


if __name__ == "__main__":
    db_path = r"D:\SteelWeldProject\weld-inspection\data\weld_inspection.db"
    run_full_pipeline(db_path)