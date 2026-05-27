"""
模块4.3：焊缝追溯二维码系统
"""
import os
import json
import sqlite3
from pathlib import Path
import qrcode


# 数据存储目录
DATA_DIR = Path(r"D:\SteelWeldProject\data")
DB_PATH = DATA_DIR / "weld_trace.db"
QR_DIR = DATA_DIR / "qrcodes"
QR_DIR.mkdir(parents=True, exist_ok=True)


def init_database():
    """初始化追溯数据库"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weld_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weld_id TEXT UNIQUE NOT NULL,
            project_name TEXT,
            bridge_type TEXT,
            weld_position TEXT,
            detect_time TEXT,
            original_image TEXT,
            defect_image TEXT,
            defect_type TEXT,
            defect_length_mm REAL,
            defect_width_mm REAL,
            defect_area_mm2 REAL,
            damage_grade TEXT,
            confidence REAL,
            judgment_basis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 历史记录表（同一焊缝多次检测）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weld_id TEXT NOT NULL,
            detect_time TEXT,
            damage_grade TEXT,
            defect_type TEXT,
            remarks TEXT,
            FOREIGN KEY (weld_id) REFERENCES weld_records(weld_id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")


def add_weld_record(data):
    """添加一条焊缝检测记录"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO weld_records
        (weld_id, project_name, bridge_type, weld_position, detect_time,
         original_image, defect_image, defect_type, defect_length_mm,
         defect_width_mm, defect_area_mm2, damage_grade, confidence, judgment_basis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("weld_id"),
        data.get("project_name"),
        data.get("bridge_type"),
        data.get("weld_position"),
        data.get("detect_time"),
        data.get("original_image"),
        data.get("defect_image"),
        data.get("defect_type"),
        data.get("defect_length_mm"),
        data.get("defect_width_mm"),
        data.get("defect_area_mm2"),
        data.get("damage_grade"),
        data.get("confidence"),
        data.get("judgment_basis")
    ))

    # 同时插入历史记录
    cursor.execute("""
        INSERT INTO inspection_history (weld_id, detect_time, damage_grade, defect_type)
        VALUES (?, ?, ?, ?)
    """, (
        data.get("weld_id"),
        data.get("detect_time"),
        data.get("damage_grade"),
        data.get("defect_type")
    ))

    conn.commit()
    conn.close()
    print(f"✅ 记录已保存: {data.get('weld_id')}")


def generate_qr(weld_id, base_url="http://localhost:5000"):
    """为焊缝生成二维码"""
    url = f"{base_url}/weld/{weld_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_path = QR_DIR / f"{weld_id}.png"
    img.save(str(img_path))

    print(f"✅ 二维码已生成: {img_path}")
    print(f"   扫码地址: {url}")
    return str(img_path)


def get_weld_info(weld_id):
    """查询焊缝完整信息（含历史记录）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 最新记录
    cursor.execute(
        "SELECT * FROM weld_records WHERE weld_id = ? ORDER BY created_at DESC LIMIT 1",
        (weld_id,)
    )
    record = cursor.fetchone()

    # 历史记录
    cursor.execute(
        "SELECT * FROM inspection_history WHERE weld_id = ? ORDER BY detect_time DESC",
        (weld_id,)
    )
    history = cursor.fetchall()

    conn.close()

    if record:
        return {
            "record": dict(record),
            "history": [dict(h) for h in history]
        }
    return None


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    init_database()

    # 添加一条模拟记录
    mock_data = {
        "weld_id": "WELD-2024-001",
        "project_name": "某某大桥钢结构检测",
        "bridge_type": "钢箱梁桥",
        "weld_position": "顶板纵向焊缝",
        "detect_time": "2024-06-15",
        "original_image": "data/raw/weld_001.tiff",
        "defect_image": "data/processed/weld_001_labeled.png",
        "defect_type": "crack",
        "defect_length_mm": 7.5,
        "defect_width_mm": 0.3,
        "defect_area_mm2": 2.25,
        "damage_grade": "III类",
        "confidence": 0.85,
        "judgment_basis": "根据GB/T 11345 第X条，裂纹长度7.5mm＞5.0mm，评定为III类"
    }

    add_weld_record(mock_data)
    generate_qr("WELD-2024-001")

    # 查询验证
    info = get_weld_info("WELD-2024-001")
    if info:
        print(f"\n📋 追溯信息查询结果：")
        print(f"   焊缝编号: {info['record']['weld_id']}")
        print(f"   损伤等级: {info['record']['damage_grade']}")
        print(f"   历史检测次数: {len(info['history'])}")