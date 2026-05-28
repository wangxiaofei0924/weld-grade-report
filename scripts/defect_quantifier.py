"""
模块3：缺陷几何参数量化模块
输入：YOLOv8 检测/分割结果 + 标定参数
输出：缺陷实际尺寸（mm）
"""
import numpy as np
import cv2


class DefectQuantifier:
    """缺陷几何参数量化器"""

    def __init__(self, pixel_per_mm=11.81):
        """
        pixel_per_mm: 像素/毫米比，默认 300 DPI (300/25.4=11.81)
        """
        self.pixel_per_mm = pixel_per_mm

    def set_scale(self, dpi=None, pixel_per_mm=None):
        """设置标定比例"""
        if dpi:
            self.pixel_per_mm = dpi / 25.4
        elif pixel_per_mm:
            self.pixel_per_mm = pixel_per_mm

    def px_to_mm(self, px):
        """像素 → 毫米"""
        return px / self.pixel_per_mm

    def mm_to_px(self, mm):
        """毫米 → 像素"""
        return mm * self.pixel_per_mm

    def quantify_from_bbox(self, bbox, mask=None):
        """
        从边界框量化缺陷尺寸
        :param bbox: [x, y, w, h] 像素坐标
        :param mask: 可选，分割 mask（numpy 数组）
        :return: dict 包含实际尺寸
        """
        x, y, w, h = bbox

        # 长边 = 缺陷长度, 短边 = 缺陷宽度
        length_px = max(w, h)
        width_px = min(w, h)

        # 面积：优先用 mask 计算，否则用 bbox 估算
        if mask is not None and mask.any():
            area_px = np.sum(mask > 0)
        else:
            area_px = w * h

        # 像素 → 毫米
        length_mm = round(self.px_to_mm(length_px), 2)
        width_mm = round(self.px_to_mm(width_px), 2)
        area_mm2 = round(area_px / (self.pixel_per_mm ** 2), 2)

        # 长宽比
        aspect_ratio = round(length_px / width_px, 2) if width_px > 0 else 0

        return {
            "length_mm": length_mm,
            "width_mm": width_mm,
            "area_mm2": area_mm2,
            "length_px": length_px,
            "width_px": width_px,
            "area_px": int(area_px),
            "aspect_ratio": aspect_ratio
        }

    def quantify_from_contour(self, contour):
        """
        从轮廓量化缺陷尺寸
        :param contour: OpenCV 轮廓点集
        :return: dict
        """
        if len(contour) < 5:
            return self.quantify_from_bbox(cv2.boundingRect(contour))

        # 最小外接矩形（可旋转）
        rect = cv2.minAreaRect(contour)
        (cx, cy), (w, h), angle = rect

        # 面积（轮廓内像素数）
        area_px = cv2.contourArea(contour)

        # 像素 → 毫米
        length_mm = round(self.px_to_mm(max(w, h)), 2)
        width_mm = round(self.px_to_mm(min(w, h)), 2)
        area_mm2 = round(area_px / (self.pixel_per_mm ** 2), 2)

        return {
            "length_mm": length_mm,
            "width_mm": width_mm,
            "area_mm2": area_mm2,
            "length_px": max(w, h),
            "width_px": min(w, h),
            "area_px": int(area_px),
            "orientation_deg": round(angle, 1),
            "centroid": (round(cx), round(cy))
        }

    def quantify_from_segmentation(self, segmentation, image_shape):
        """
        从 COCO 格式分割点集量化
        :param segmentation: [[x1,y1, x2,y2, ...]] COCO 格式
        :param image_shape: (h, w) 图像尺寸
        """
        mask = np.zeros(image_shape, dtype=np.uint8)
        for seg in segmentation:
            pts = np.array(seg).reshape(-1, 2).astype(np.int32)
            cv2.fillPoly(mask, [pts], 255)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # 取最大轮廓
        main_contour = max(contours, key=cv2.contourArea)
        result = self.quantify_from_contour(main_contour)
        result["mask"] = mask
        return result

    def batch_quantify(self, detections):
        """
        批量量化
        :param detections: YOLO 检测结果列表
            [{"bbox": [x,y,w,h], "mask": array, "segmentation": [...]}, ...]
        :return: 量化结果列表
        """
        results = []
        for i, det in enumerate(detections):
            bbox = det.get("bbox")
            mask = det.get("mask")
            segmentation = det.get("segmentation")

            if segmentation and "image_shape" in det:
                result = self.quantify_from_segmentation(segmentation, det["image_shape"])
            elif mask is not None:
                contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                result = self.quantify_from_contour(max(contours, key=cv2.contourArea)) if contours else self.quantify_from_bbox(bbox, mask)
            else:
                result = self.quantify_from_bbox(bbox)

            result["defect_id"] = i
            results.append(result)

        return results


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("模块3：缺陷几何参数量化测试")
    print("=" * 50)

    q = DefectQuantifier(pixel_per_mm=11.81)  # 300 DPI

    # 模拟一个裂纹检测结果
    mock_bbox = [100, 150, 90, 4]  # x, y, w, h（像素）
    result = q.quantify_from_bbox(mock_bbox)

    print(f"\n模拟裂纹检测（300 DPI）：")
    print(f"  边界框(px): {mock_bbox}")
    print(f"  长度: {result['length_mm']} mm")
    print(f"  宽度: {result['width_mm']} mm")
    print(f"  面积: {result['area_mm2']} mm²")
    print(f"  长宽比: {result['aspect_ratio']}")

    # 模拟多缺陷批量量化
    print(f"\n批量量化测试：")
    mock_detections = [
        {"bbox": [100, 150, 90, 4], "defect_type": "crack"},
        {"bbox": [200, 300, 20, 20], "defect_type": "porosity"},
        {"bbox": [350, 200, 60, 30], "defect_type": "lack_of_fusion"},
    ]

    results = q.batch_quantify(mock_detections)
    for r in results:
        print(f"  缺陷{r['defect_id']}: {r['length_mm']}×{r['width_mm']}mm, 面积{r['area_mm2']}mm²")