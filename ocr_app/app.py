"""
常规测序样品接收单 OCR 识别服务
基于 PaddleOCR + Flask 实现中文手写订单结构化识别
"""
import os
import json
import re
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

# ─── PaddleOCR 懒加载（首次请求时初始化，避免启动太慢）─────────────────────────
# 注意：PaddleOCR 3.x 使用新 API，初始化参数与 2.x 不同
_ocr_instance = None

def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            # 3.x 新参数：不再用 use_angle_cls/use_gpu，改用以下参数
            _ocr_instance = PaddleOCR(
                lang="ch",
                use_doc_orientation_classify=False,  # 关闭文档方向分类（加速）
                use_doc_unwarping=False,              # 关闭文档矫正（加速）
                use_textline_orientation=False,       # 关闭文本行方向（加速）
            )
        except ImportError:
            _ocr_instance = "MOCK"  # 未安装时返回 mock 数据，方便开发调试
    return _ocr_instance


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── OCR 核心 ─────────────────────────────────────────────────────────────────

def run_ocr(image_path: str) -> list[dict]:
    """
    运行 PaddleOCR，返回 [{"text": ..., "confidence": ..., "bbox": [...]}] 列表
    兼容 PaddleOCR 3.x（使用 predict() 新 API）
    """
    ocr = get_ocr()
    if ocr == "MOCK":
        return _mock_ocr_result()

    # PaddleOCR 3.x: 使用 predict() 方法，返回 OCRResult 对象列表
    result = ocr.predict(image_path)
    lines = []
    for page_result in result:
        # 3.x 返回的是 OCRResult 对象，字段通过 [] 或属性访问
        # 正确字段名：rec_texts / rec_scores / rec_polys（不是 det_polys）
        rec_texts  = page_result["rec_texts"]  if "rec_texts"  in page_result else []
        rec_scores = page_result["rec_scores"] if "rec_scores" in page_result else []
        rec_polys  = page_result["rec_polys"]  if "rec_polys"  in page_result else []
        rec_boxes  = page_result["rec_boxes"]  if "rec_boxes"  in page_result else []

        # 优先用 rec_polys，fallback 到 rec_boxes
        polys = rec_polys if rec_polys else rec_boxes

        for i, (text, conf) in enumerate(zip(rec_texts, rec_scores)):
            if text and text.strip():
                poly = polys[i] if i < len(polys) else None
                # numpy array 转普通列表
                if poly is not None:
                    try:
                        bbox = poly.tolist()
                    except AttributeError:
                        bbox = [list(map(float, p)) for p in poly]
                else:
                    bbox = []
                lines.append({
                    "text": text.strip(),
                    "confidence": round(float(conf), 4),
                    "bbox": bbox,
                })
    return lines


def _mock_ocr_result() -> list[dict]:
    """未安装 PaddleOCR 时的 mock 数据，用于界面演示"""
    return [
        {"text": "客户姓名", "confidence": 0.99, "bbox": [[10,10],[80,10],[80,25],[10,25]]},
        {"text": "张三", "confidence": 0.97, "bbox": [[90,10],[140,10],[140,25],[90,25]]},
        {"text": "联系电话", "confidence": 0.99, "bbox": [[150,10],[220,10],[220,25],[150,25]]},
        {"text": "13800138000", "confidence": 0.96, "bbox": [[230,10],[310,10],[310,25],[230,25]]},
        {"text": "E-mail", "confidence": 0.99, "bbox": [[320,10],[370,10],[370,25],[320,25]]},
        {"text": "zhangsan@example.com", "confidence": 0.95, "bbox": [[380,10],[500,10],[500,25],[380,25]]},
        {"text": "客户单位", "confidence": 0.99, "bbox": [[10,30],[80,30],[80,45],[10,45]]},
        {"text": "武汉大学生命科学学院", "confidence": 0.93, "bbox": [[90,30],[250,30],[250,45],[90,45]]},
        {"text": "送测日期", "confidence": 0.99, "bbox": [[260,30],[330,30],[330,45],[260,45]]},
        {"text": "2024年3月15日", "confidence": 0.95, "bbox": [[340,30],[430,30],[430,45],[340,45]]},
        {"text": "样品名称", "confidence": 0.99, "bbox": [[10,80],[80,80],[80,95],[10,95]]},
        {"text": "pUC19-GFP", "confidence": 0.94, "bbox": [[90,80],[170,80],[170,95],[90,95]]},
        {"text": "样品类型", "confidence": 0.99, "bbox": [[180,80],[250,80],[250,95],[180,95]]},
        {"text": "质粒", "confidence": 0.96, "bbox": [[260,80],[300,80],[300,95],[260,95]]},
        {"text": "载体名称", "confidence": 0.98, "bbox": [[310,80],[380,80],[380,95],[310,95]]},
        {"text": "pUC19", "confidence": 0.95, "bbox": [[390,80],[440,80],[440,95],[390,95]]},
        {"text": "抗性", "confidence": 0.99, "bbox": [[450,80],[490,80],[490,95],[450,95]]},
        {"text": "Amp", "confidence": 0.97, "bbox": [[500,80],[540,80],[540,95],[500,95]]},
    ]


# ─── 结构化解析 ───────────────────────────────────────────────────────────────

CUSTOMER_FIELDS = {
    "客户姓名": ["客户姓名", "姓名"],
    "联系电话": ["联系电话", "电话"],
    "email": ["E-mail", "email", "邮箱"],
    "所属课题组": ["所属课题组", "课题组"],
    "详细地址": ["详细地址", "地址"],
    "客户单位": ["客户单位", "单位"],
    "送测日期": ["送测日期", "日期"],
}

SAMPLE_HEADERS = ["样品名称", "样品类型", "载体名称", "抗性", "片段长度",
                  "引物类别", "引物名称", "正向引物", "反向引物",
                  "引物浓度", "OD数", "测序要求", "特殊备注", "返样要求"]


def parse_structured(lines: list[dict]) -> dict:
    """
    将 OCR 识别结果解析为结构化 JSON：
    {
      "customer": { ... },
      "samples": [ {...}, ... ],
      "remarks": "...",
      "raw_texts": [...]
    }
    """
    texts = [l["text"] for l in lines]
    raw_joined = "\n".join(texts)

    customer = _extract_customer(lines)
    samples = _extract_samples(lines)
    remarks = _extract_remarks(lines)

    return {
        "customer": customer,
        "samples": samples,
        "remarks": remarks,
        "raw_texts": texts,
        "total_lines": len(lines),
    }


def _extract_customer(lines: list[dict]) -> dict:
    """提取客户信息字段（基于标签-值相邻关系）"""
    result = {k: "" for k in CUSTOMER_FIELDS}
    texts = [l["text"] for l in lines]

    for field, aliases in CUSTOMER_FIELDS.items():
        for alias in aliases:
            for i, t in enumerate(texts):
                if alias in t:
                    # 尝试从同一文本行提取冒号后内容
                    colon_match = re.search(r'[:：](.+)', t)
                    if colon_match:
                        result[field] = colon_match.group(1).strip()
                        break
                    # 尝试取下一个 token
                    if i + 1 < len(texts):
                        next_t = texts[i + 1]
                        if not any(a in next_t for aliases2 in CUSTOMER_FIELDS.values() for a in aliases2):
                            result[field] = next_t.strip()
                            break
            if result[field]:
                break

    return result


def _extract_samples(lines: list[dict]) -> list[dict]:
    """
    提取样品表格行（通过行号 01-11 定位）
    返回每行包含序号和已识别字段的列表
    """
    samples = []
    row_pattern = re.compile(r'^(0[1-9]|1[01])$')
    texts = [l["text"] for l in lines]
    bboxes = [l["bbox"] for l in lines]

    # 找到行号索引
    row_indices = [(i, t) for i, t in enumerate(texts) if row_pattern.match(t.strip())]

    for idx, (i, row_num) in enumerate(row_indices):
        # 确定同行文本范围（Y 坐标接近）
        row_y = _center_y(bboxes[i])
        row_texts = []
        for j, (t, b) in enumerate(zip(texts, bboxes)):
            if abs(_center_y(b) - row_y) < 15 and j != i:
                row_texts.append(t)

        sample = {"序号": row_num, "原始内容": " | ".join(row_texts)}

        # 简单启发：按位置顺序赋值常见字段
        fields = ["样品名称", "样品类型", "载体名称", "抗性", "片段长度", "引物类别", "正向引物", "反向引物"]
        for k, v in zip(fields, row_texts):
            sample[k] = v

        if row_texts:  # 有内容才加入
            samples.append(sample)

    return samples


def _extract_remarks(lines: list[dict]) -> str:
    texts = [l["text"] for l in lines]
    remarks = []
    in_remarks = False
    for t in texts:
        if "备注" in t:
            in_remarks = True
            continue
        if in_remarks and len(t) > 2:
            remarks.append(t)
            if len(remarks) >= 5:
                break
    return " ".join(remarks)


def _center_y(bbox) -> float:
    ys = [p[1] for p in bbox]
    return sum(ys) / len(ys)


# ─── Flask 路由 ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ocr", methods=["POST"])
def ocr_endpoint():
    if "file" not in request.files:
        return jsonify({"error": "未收到文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "不支持的文件类型，请上传 PNG/JPG/TIFF 等图片"}), 400

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        lines = run_ocr(save_path)
        structured = parse_structured(lines)
        return jsonify({"success": True, "data": structured})
    except Exception as e:
        return jsonify({"error": f"识别失败: {str(e)}"}), 500
    finally:
        # 识别完毕后删除临时文件
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route("/api/health")
def health():
    ocr = get_ocr()
    return jsonify({
        "status": "ok",
        "paddleocr": "mock_mode" if ocr == "MOCK" else "ready",
    })


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    print("🚀 OCR 服务已启动: http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
