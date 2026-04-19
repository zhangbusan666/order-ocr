#!/usr/bin/env python3
"""
独立演示脚本：无需 Flask，直接用命令行测试 OCR + 解析
用法：python demo.py <图片路径>
"""
import sys
import json

def demo(image_path: str):
    print(f"\n📄 测试图片: {image_path}\n")

    # 尝试导入 PaddleOCR
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        result = ocr.ocr(image_path, cls=True)

        lines = []
        for page in result:
            if not page:
                continue
            for item in page:
                bbox, (text, conf) = item
                lines.append({"text": text.strip(), "confidence": round(float(conf), 4), "bbox": bbox})

        print(f"✅ PaddleOCR 识别完成，共 {len(lines)} 行文本\n")

    except ImportError:
        print("⚠️  PaddleOCR 未安装，使用 mock 数据演示\n")
        lines = [
            {"text": "客户姓名", "confidence": 0.99, "bbox": [[10,10],[80,10],[80,25],[10,25]]},
            {"text": "张三",     "confidence": 0.97, "bbox": [[90,10],[140,10],[140,25],[90,25]]},
            {"text": "联系电话", "confidence": 0.99, "bbox": [[150,10],[220,10],[220,25],[150,25]]},
            {"text": "13800138000", "confidence": 0.96, "bbox": [[230,10],[310,10],[310,25],[230,25]]},
            {"text": "E-mail",   "confidence": 0.99, "bbox": [[320,10],[370,10],[370,25],[320,25]]},
            {"text": "zhangsan@example.com", "confidence": 0.95, "bbox": [[380,10],[500,10],[500,25],[380,25]]},
            {"text": "客户单位", "confidence": 0.99, "bbox": [[10,30],[80,30],[80,45],[10,45]]},
            {"text": "武汉大学生命科学学院", "confidence": 0.93, "bbox": [[90,30],[250,30],[250,45],[90,45]]},
            {"text": "送测日期", "confidence": 0.99, "bbox": [[260,30],[330,30],[330,45],[260,45]]},
            {"text": "2024年3月15日", "confidence": 0.95, "bbox": [[340,30],[430,30],[430,45],[340,45]]},
            {"text": "01",       "confidence": 0.99, "bbox": [[10,100],[30,100],[30,115],[10,115]]},
            {"text": "pUC19-GFP","confidence": 0.94, "bbox": [[35,100],[120,100],[120,115],[35,115]]},
            {"text": "质粒",     "confidence": 0.96, "bbox": [[125,100],[165,100],[165,115],[125,115]]},
            {"text": "pUC19",    "confidence": 0.95, "bbox": [[170,100],[220,100],[220,115],[170,115]]},
            {"text": "Amp",      "confidence": 0.97, "bbox": [[225,100],[265,100],[265,115],[225,115]]},
            {"text": "1.2kb",    "confidence": 0.93, "bbox": [[270,100],[310,100],[310,115],[270,115]]},
            {"text": "02",       "confidence": 0.99, "bbox": [[10,120],[30,120],[30,135],[10,135]]},
            {"text": "pET28a-His", "confidence": 0.92, "bbox": [[35,120],[140,120],[140,135],[35,135]]},
            {"text": "质粒",     "confidence": 0.96, "bbox": [[145,120],[185,120],[185,135],[145,135]]},
            {"text": "pET28a",   "confidence": 0.94, "bbox": [[190,120],[240,120],[240,135],[190,135]]},
            {"text": "Kan",      "confidence": 0.97, "bbox": [[245,120],[285,120],[285,135],[245,135]]},
        ]

    # 导入解析逻辑（动态加载）
    import importlib, sys, os
    sys.path.insert(0, os.path.dirname(__file__))

    # 内联简化解析（避免 Flask 依赖）
    import re

    def center_y(bbox):
        return sum(p[1] for p in bbox) / len(bbox)

    texts = [l["text"] for l in lines]
    bboxes = [l["bbox"] for l in lines]

    # 客户信息
    customer_aliases = {
        "客户姓名": ["客户姓名", "姓名"],
        "联系电话": ["联系电话", "电话"],
        "email":    ["E-mail", "email", "邮箱"],
        "客户单位": ["客户单位", "单位"],
        "送测日期": ["送测日期", "日期"],
    }
    customer = {}
    for field, aliases in customer_aliases.items():
        for alias in aliases:
            for i, t in enumerate(texts):
                if alias in t:
                    m = re.search(r'[:：](.+)', t)
                    if m:
                        customer[field] = m.group(1).strip()
                        break
                    if i + 1 < len(texts):
                        nxt = texts[i+1]
                        if not any(a in nxt for als in customer_aliases.values() for a in als):
                            customer[field] = nxt.strip()
                            break
            if customer.get(field):
                break

    # 样品行
    row_pattern = re.compile(r'^(0[1-9]|1[01])$')
    samples = []
    for i, (t, b) in enumerate(zip(texts, bboxes)):
        if row_pattern.match(t.strip()):
            row_y = center_y(b)
            row_texts = [texts[j] for j, bj in enumerate(bboxes)
                         if abs(center_y(bj) - row_y) < 15 and j != i]
            fields = ["样品名称","样品类型","载体名称","抗性","片段长度"]
            s = {"序号": t}
            for k, v in zip(fields, row_texts):
                s[k] = v
            s["原始内容"] = " | ".join(row_texts)
            if row_texts:
                samples.append(s)

    result = {
        "customer": customer,
        "samples":  samples,
        "total_lines": len(lines),
    }

    print("=" * 60)
    print("📊 结构化输出 JSON:")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print(f"✅ 客户字段识别: {len(customer)} 项")
    print(f"✅ 样品行识别: {len(samples)} 条")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "test.jpg"
    demo(path)
