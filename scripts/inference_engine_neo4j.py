"""
模块3：基于知识图谱的损伤等级智能评定 - Neo4j版推理引擎
"""
from neo4j import GraphDatabase


class Neo4jDamageGrader:
    """从Neo4j知识图谱加载规则的损伤等级评定器"""

    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="hgjlxf21"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def load_rules(self):
        """从Neo4j加载所有评定规则"""
        query = """
            MATCH (d:DefectType)-[r:评定规则]->(g:Grade)
            RETURN d.name AS defect_type,
                   r.rule_id AS rule_id,
                   r.param AS param,
                   r.operator AS operator,
                   r.threshold AS threshold,
                   r.source AS source,
                   g.name AS grade,
                   g.level AS grade_level
            ORDER BY g.level DESC
        """
        with self.driver.session() as session:
            results = session.run(query)
            rules = []
            for record in results:
                rules.append({
                    "defect_type": record["defect_type"],
                    "rule_id": record["rule_id"],
                    "param": record["param"],
                    "operator": record["operator"],
                    "threshold": record["threshold"],
                    "source": record["source"],
                    "grade": record["grade"],
                    "grade_level": record["grade_level"]
                })
            return rules

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
            return 0.3

        best = matched_rules[0]
        threshold = best["threshold"]
        value = defect.get(best["param"], 0)

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
            return 0.60

    def grade_defect(self, defect):
        """评定单个缺陷"""
        rules = self.load_rules()
        defect_type = defect.get("defect_type", "")
        matched_rules = []

        for rule in rules:
            if rule["defect_type"] != defect_type:
                continue
            value = defect.get(rule["param"], 0)
            if self._check_rule(rule, value):
                matched_rules.append(rule)

        if not matched_rules:
            return {
                "grade": "I类",
                "confidence": 0.95,
                "reason": "缺陷参数未触及任何降级阈值，评定为I类",
                "need_review": False
            }

        # 已按grade_level DESC排序，第一项即最严重
        best_rule = matched_rules[0]
        confidence = self._calc_confidence(matched_rules, defect)
        need_review = confidence < 0.65

        param_label = {"length_mm": "长度", "width_mm": "宽度", "area_mm2": "面积"}
        label = param_label.get(best_rule["param"], best_rule["param"])
        value = defect.get(best_rule["param"], 0)

        reason = (
            f"根据{best_rule['source']}，"
            f"缺陷类型'{defect_type}'的{label}为{value:.1f}mm，"
            f"{'＞' if best_rule['operator'] == '>' else best_rule['operator']}"
            f"{best_rule['threshold']}mm，评定为{best_rule['grade']}。"
        )

        return {
            "grade": best_rule["grade"],
            "confidence": round(confidence, 2),
            "reason": reason,
            "need_review": need_review,
            "matched_rule_id": best_rule["rule_id"]
        }

    def close(self):
        self.driver.close()


def batch_grade(defects_list, grader=None):
    """批量评定"""
    if grader is None:
        grader = Neo4jDamageGrader()

    results = []
    for defect in defects_list:
        result = grader.grade_defect(defect)
        result["defect_type"] = defect.get("defect_type", "")
        results.append(result)

    grade_order = {"I类": 0, "II类": 1, "III类": 2, "IV类": 3}
    overall = max(results, key=lambda r: grade_order.get(r["grade"], 0))

    return {
        "defect_count": len(defects_list),
        "overall_grade": overall["grade"],
        "details": results,
        "need_review": any(r["need_review"] for r in results)
    }


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    mock_defects = [
        {"defect_type": "crack",      "length_mm": 7.5, "width_mm": 0.3, "area_mm2": 2.25},
        {"defect_type": "porosity",   "length_mm": 2.0, "width_mm": 1.5, "area_mm2": 3.0},
        {"defect_type": "lack_of_fusion", "length_mm": 12.0, "width_mm": 3.0, "area_mm2": 36.0},
        {"defect_type": "slag_inclusion", "length_mm": 13.0, "width_mm": 2.0, "area_mm2": 26.0},
        {"defect_type": "pore_cluster",   "length_mm": 3.0, "width_mm": 2.0, "area_mm2": 6.0},
        {"defect_type": "undercut",   "length_mm": 8.0, "width_mm": 1.0, "area_mm2": 8.0},
    ]

    print("=" * 60)
    print("Neo4j知识图谱推理引擎测试")
    print("=" * 60)

    grader = Neo4jDamageGrader(password="hgjlxf21")

    for i, defect in enumerate(mock_defects, 1):
        result = grader.grade_defect(defect)
        review_flag = "⚠️ 需人工复核" if result["need_review"] else ""
        print(f"\n--- 缺陷{i}: {defect['defect_type']} ---")
        print(f"    评定: {result['grade']} | 置信度: {result['confidence']} | 规则: {result.get('matched_rule_id','')}")
        print(f"    依据: {result['reason']}")
        print(f"    {review_flag}")

    print("\n" + "=" * 60)
    summary = batch_grade(mock_defects, grader)
    print(f"汇总: {summary['defect_count']}个缺陷, 总体等级: {summary['overall_grade']}")
    print("=" * 60)

    grader.close()