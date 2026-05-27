"""
模块3：基于知识图谱的损伤等级智能评定 - 推理引擎核心
"""

# ============================================
# 第一部分：知识库（暂时硬编码，后续从Neo4j加载）
# ============================================

# 规则库：每条规则 = (缺陷类型, 参数条件, 损伤等级, 标准出处)
RULES = [
    # 裂纹类 (crack)
    {"defect_type": "crack", "param": "length_mm", "operator": ">", "threshold": 5.0,
     "grade": "III类", "source": "GB/T 11345 第X条", "rule_id": "R001"},
    {"defect_type": "crack", "param": "length_mm", "operator": ">", "threshold": 10.0,
     "grade": "IV类", "source": "GB/T 11345 第X条", "rule_id": "R002"},

    # 未焊透 (lack_of_fusion)
    {"defect_type": "lack_of_fusion", "param": "width_mm", "operator": ">", "threshold": 2.0,
     "grade": "IV类", "source": "GB/T 3323 第X条", "rule_id": "R003"},
    {"defect_type": "lack_of_fusion", "param": "length_mm", "operator": ">", "threshold": 8.0,
     "grade": "III类", "source": "GB/T 3323 第X条", "rule_id": "R004"},

    # 气孔 (porosity)
    {"defect_type": "porosity", "param": "area_mm2", "operator": ">", "threshold": 5.0,
     "grade": "III类", "source": "GB/T 3323 第X条", "rule_id": "R005"},
    {"defect_type": "porosity", "param": "area_mm2", "operator": ">", "threshold": 10.0,
     "grade": "IV类", "source": "GB/T 3323 第X条", "rule_id": "R006"},

    # 夹渣 (slag_inclusion)
    {"defect_type": "slag_inclusion", "param": "length_mm", "operator": ">", "threshold": 6.0,
     "grade": "III类", "source": "GB/T 11345 第X条", "rule_id": "R007"},
    {"defect_type": "slag_inclusion", "param": "length_mm", "operator": ">", "threshold": 12.0,
     "grade": "IV类", "source": "GB/T 11345 第X条", "rule_id": "R008"},

    # 气孔群 (pore_cluster)
    {"defect_type": "pore_cluster", "param": "area_mm2", "operator": ">", "threshold": 8.0,
     "grade": "III类", "source": "GB/T 11345 第X条", "rule_id": "R009"},

    # 咬边 (undercut)
    {"defect_type": "undercut", "param": "length_mm", "operator": ">", "threshold": 10.0,
     "grade": "III类", "source": "JTG 5210 第X条", "rule_id": "R010"},

    # 未熔合 (incomplete_penetration)
    {"defect_type": "incomplete_penetration", "param": "length_mm", "operator": ">", "threshold": 5.0,
     "grade": "III类", "source": "GB/T 3323 第X条", "rule_id": "R011"},
]


# ============================================
# 第二部分：推理引擎
# ============================================

class DamageGrader:
    """损伤等级评定器"""

    def __init__(self, rules=None):
        self.rules = rules or RULES

    def _check_rule(self, rule, value):
        """检查单条规则是否匹配"""
        op = rule["operator"]
        threshold = rule["threshold"]

        if op == ">":
            return value > threshold
        elif op == ">=":
            return value >= threshold
        elif op == "<":
            return value < threshold
        elif op == "<=":
            return value <= threshold
        elif op == "==":
            return value == threshold
        return False

    def _calc_confidence(self, matched_rules, defect):
        """计算置信度（0~1）"""
        if not matched_rules:
            return 0.3  # 无匹配规则，低置信度

        # 取最高等级那条规则
        best = matched_rules[0]
        threshold = best["threshold"]
        value = defect.get(best["param"], 0)

        # 距阈值越远，置信度越高
        if threshold > 0:
            margin = abs(value - threshold) / threshold
        else:
            margin = 0.5

        if margin > 0.5:
            return 0.95
        elif margin > 0.2:
            return 0.85
        elif margin > 0.1:
            return 0.75
        else:
            return 0.60  # 接近阈值，需人工复核

    def grade_defect(self, defect):
        """
        评定单个缺陷的损伤等级
        :param defect: dict, 包含 defect_type, length_mm, width_mm, area_mm2
        :return: dict, 包含 grade, confidence, reason, need_review
        """
        defect_type = defect.get("defect_type", "")
        matched_rules = []

        # 遍历规则库，匹配缺陷类型
        for rule in self.rules:
            if rule["defect_type"] != defect_type:
                continue

            param_name = rule["param"]
            value = defect.get(param_name, 0)

            if self._check_rule(rule, value):
                matched_rules.append(rule)

        if not matched_rules:
            return {
                "grade": "I类",
                "confidence": 0.95,
                "reason": "缺陷参数未触及任何降级阈值，评定为I类",
                "need_review": False
            }

        # 按等级严重程度排序（IV类 > III类 > II类 > I类）
        grade_order = {"I类": 0, "II类": 1, "III类": 2, "IV类": 3}
        matched_rules.sort(key=lambda r: grade_order.get(r["grade"], 0), reverse=True)

        best_rule = matched_rules[0]
        confidence = self._calc_confidence(matched_rules, defect)
        need_review = confidence < 0.65

        # 生成评定依据
        param_label = {
            "length_mm": "长度",
            "width_mm": "宽度",
            "area_mm2": "面积"
        }
        label = param_label.get(best_rule["param"], best_rule["param"])
        value = defect.get(best_rule["param"], 0)

        reason = (
            f"根据{best_rule['source']}，"
            f"缺陷类型'{defect_type}'的{label}为{value:.1f}mm，"
            f"{'＞' if best_rule['operator']=='>' else best_rule['operator']}"
            f"{best_rule['threshold']}mm，评定为{best_rule['grade']}。"
        )

        return {
            "grade": best_rule["grade"],
            "confidence": round(confidence, 2),
            "reason": reason,
            "need_review": need_review,
            "matched_rule_id": best_rule["rule_id"]
        }


# ============================================
# 第三部分：批量评定接口
# ============================================

def batch_grade(defects_list):
    """批量评定多个缺陷，返回汇总结果"""
    grader = DamageGrader()
    results = []

    for defect in defects_list:
        result = grader.grade_defect(defect)
        result["defect_type"] = defect.get("defect_type", "")
        results.append(result)

    # 汇总：取最严重等级
    grade_order = {"I类": 0, "II类": 1, "III类": 2, "IV类": 3}
    overall = max(results, key=lambda r: grade_order.get(r["grade"], 0))

    return {
        "defect_count": len(defects_list),
        "overall_grade": overall["grade"],
        "details": results,
        "need_review": any(r["need_review"] for r in results)
    }


# ============================================
# 第四部分：测试入口
# ============================================

if __name__ == "__main__":
    # 模拟模块2输出的缺陷数据
    mock_defects = [
        {"defect_type": "crack",      "length_mm": 7.5, "width_mm": 0.3, "area_mm2": 2.25},
        {"defect_type": "porosity",   "length_mm": 2.0, "width_mm": 1.5, "area_mm2": 3.0},
        {"defect_type": "lack_of_fusion", "length_mm": 12.0, "width_mm": 3.0, "area_mm2": 36.0},
        {"defect_type": "slag_inclusion", "length_mm": 13.0, "width_mm": 2.0, "area_mm2": 26.0},
        {"defect_type": "pore_cluster",   "length_mm": 3.0, "width_mm": 2.0, "area_mm2": 6.0},
        {"defect_type": "undercut",   "length_mm": 8.0, "width_mm": 1.0, "area_mm2": 8.0},
    ]

    print("=" * 60)
    print("损伤等级评定 - 推理引擎测试（假数据）")
    print("=" * 60)

    grader = DamageGrader()
    for i, defect in enumerate(mock_defects, 1):
        result = grader.grade_defect(defect)
        review_flag = "⚠️ 需人工复核" if result["need_review"] else ""
        print(f"\n--- 缺陷{i}: {defect['defect_type']} ---")
        print(f"    长度={defect['length_mm']}mm, 宽度={defect['width_mm']}mm, 面积={defect['area_mm2']}mm²")
        print(f"    评定结果: {result['grade']}")
        print(f"    置信度: {result['confidence']}")
        print(f"    依据: {result['reason']}")
        print(f"    {review_flag}")

    print("\n" + "=" * 60)
    summary = batch_grade(mock_defects)
    print(f"批量评定汇总：共 {summary['defect_count']} 个缺陷，总体等级: {summary['overall_grade']}")
    if summary['need_review']:
        print("⚠️ 存在需人工复核的缺陷")
    print("=" * 60)