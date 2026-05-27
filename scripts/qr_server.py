"""
焊缝追溯 - Flask Web 服务
启动后访问 http://localhost:5000
"""
from flask import Flask, render_template_string
from qr_manager import get_weld_info, init_database

app = Flask(__name__)

# HTML 模板
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
        .grade-I { background: #4CAF50; }
        .grade-II { background: #FFC107; color: #333; }
        .grade-III { background: #FF9800; }
        .grade-IV { background: #F44336; }
        .history-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .history-table th { background: #eee; padding: 10px; text-align: left; }
        .history-table td { padding: 10px; border-bottom: 1px solid #eee; }
        .basis { background: #FFF9C4; padding: 12px; border-radius: 6px; font-size: 14px; line-height: 1.6; }
        .footer { text-align: center; padding: 15px; color: #aaa; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 焊缝追溯信息</h1>
            <p>{{ record.weld_id }}</p>
        </div>
        <div class="content">
            <!-- 工程信息 -->
            <div class="section">
                <h2>📋 工程信息</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <label>工程名称</label>
                        <span>{{ record.project_name or '--' }}</span>
                    </div>
                    <div class="info-item">
                        <label>桥梁类型</label>
                        <span>{{ record.bridge_type or '--' }}</span>
                    </div>
                    <div class="info-item">
                        <label>焊缝位置</label>
                        <span>{{ record.weld_position or '--' }}</span>
                    </div>
                    <div class="info-item">
                        <label>检测时间</label>
                        <span>{{ record.detect_time or '--' }}</span>
                    </div>
                </div>
            </div>

            <!-- 缺陷信息 -->
            <div class="section">
                <h2>⚠️ 缺陷识别结果</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <label>缺陷类型</label>
                        <span>{{ record.defect_type or '--' }}</span>
                    </div>
                    <div class="info-item">
                        <label>缺陷长度</label>
                        <span>{{ record.defect_length_mm }} mm</span>
                    </div>
                    <div class="info-item">
                        <label>缺陷宽度</label>
                        <span>{{ record.defect_width_mm }} mm</span>
                    </div>
                    <div class="info-item">
                        <label>缺陷面积</label>
                        <span>{{ record.defect_area_mm2 }} mm²</span>
                    </div>
                </div>
            </div>

            <!-- 评定结果 -->
            <div class="section">
                <h2>📊 损伤等级评定</h2>
                <div style="text-align: center; margin: 15px 0;">
                    <span class="grade grade-{{ grade_class }}">{{ record.damage_grade }}</span>
                </div>
                <div style="text-align: center; color: #666; margin-bottom: 10px;">
                    置信度：{{ record.confidence }}
                </div>
                <div class="basis">
                    <strong>判定依据：</strong><br>
                    {{ record.judgment_basis or '暂无' }}
                </div>
            </div>

            <!-- 历史记录 -->
            <div class="section">
                <h2>📜 历史检测记录</h2>
                {% if history %}
                <table class="history-table">
                    <tr>
                        <th>检测时间</th>
                        <th>损伤等级</th>
                        <th>缺陷类型</th>
                    </tr>
                    {% for h in history %}
                    <tr>
                        <td>{{ h.detect_time or '--' }}</td>
                        <td>{{ h.damage_grade or '--' }}</td>
                        <td>{{ h.defect_type or '--' }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <p style="color: #aaa;">暂无历史记录</p>
                {% endif %}
            </div>
        </div>
        <div class="footer">
            钢结构焊缝缺陷智能识别与损伤评定系统 © 2024
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    return """
    <html><body style="font-family:Microsoft YaHei;text-align:center;padding:50px;">
    <h1>🔍 焊缝追溯系统</h1>
    <p>请扫描二维码访问焊缝信息</p>
    <p style="color:#aaa;">示例：<a href="/weld/WELD-2024-001">/weld/WELD-2024-001</a></p>
    </body></html>
    """


@app.route("/weld/<weld_id>")
def weld_detail(weld_id):
    info = get_weld_info(weld_id)

    if not info:
        return """
        <html><body style="font-family:Microsoft YaHei;text-align:center;padding:50px;">
        <h1>❌ 未找到该焊缝信息</h1>
        <p>焊缝编号不存在或数据已删除</p>
        <a href="/">返回首页</a>
        </body></html>
        """, 404

    record = info["record"]
    history = info["history"]

    # 等级对应的 CSS class
    grade_class_map = {
        "I类": "grade-I", "II类": "grade-II",
        "III类": "grade-III", "IV类": "grade-IV"
    }
    grade_class = grade_class_map.get(record.get("damage_grade", ""), "")

    return render_template_string(
        PAGE_TEMPLATE,
        record=record,
        history=history,
        grade_class=grade_class
    )


if __name__ == "__main__":
    init_database()
    print("=" * 50)
    print("🔍 焊缝追溯系统启动中...")
    print("   本地访问: http://localhost:5000")
    print("   示例焊缝: http://localhost:5000/weld/WELD-2024-001")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)