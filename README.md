# 常规测序样品接收单 OCR 识别系统

基于 **PaddleOCR + Flask** 的中文手写订单智能识别与结构化输出系统。

## 项目结构

```
ocr_app/
├── app.py              # Flask 主应用（OCR识别 + 结构化解析 + API）
├── demo.py             # 命令行演示脚本（无需Flask）
├── preview.html        # 独立前端预览（可直接浏览器打开）
├── requirements.txt    # Python 依赖
├── templates/
│   └── index.html      # 主页面模板
├── static/
│   ├── css/main.css    # 全局样式（亮/暗双主题）
│   └── js/main.js      # 前端交互逻辑
└── uploads/            # 临时文件目录（自动创建）
```

## 快速开始

### 方式一：直接预览 UI（无需安装）
```bash
# 直接用浏览器打开
open ocr_app/preview.html
```

### 方式二：运行完整应用

**1. 创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate   # Windows
```

**2. 安装依赖**
```bash
pip install -r ocr_app/requirements.txt
```

> PaddleOCR 安装较大（含模型下载），建议使用国内镜像：
> ```bash
> pip install -r ocr_app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

**3. 启动服务**
```bash
cd ocr_app
python app.py
```

**4. 打开浏览器**
访问 http://127.0.0.1:5000

### 方式三：命令行快速测试
```bash
cd ocr_app
python demo.py ../一代电子订单.jpg
```

## 功能特性

### OCR 识别
- 使用 PaddleOCR v3 中文模型（PP-OCRv4）
- 支持手写 + 印刷混合识别
- 图片倾斜自动矫正（angle classification）
- 未安装 PaddleOCR 时自动降级为演示模式

### 结构化解析
识别结果自动解析为以下结构：

```json
{
  "customer": {
    "客户姓名": "王芳",
    "联系电话": "13912345678",
    "email": "wangfang@whu.edu.cn",
    "所属课题组": "分子生物学实验室",
    "详细地址": "武汉市武昌区八一路299号",
    "客户单位": "武汉大学生命科学学院",
    "送测日期": "2024年3月18日"
  },
  "samples": [
    {
      "序号": "01",
      "样品名称": "pUC19-GFP",
      "样品类型": "质粒",
      "载体名称": "pUC19",
      "抗性": "Amp",
      "片段长度": "1.2kb",
      "引物类别": "通用引物",
      "正向引物": "M13F",
      "反向引物": "M13R"
    }
  ],
  "remarks": "备注文本..."
}
```

### 界面功能
- **拖拽上传** / 点击选择图片
- **实时进度**显示识别步骤
- **三视图切换**：结构化视图 / 原始文本 / JSON
- **识别置信度**可视化（绿/黄/红）
- **一键复制 JSON** / **导出 CSV**
- **亮/暗主题**切换

## API 文档

### POST /api/ocr

上传图片进行识别。

**Request**
```
Content-Type: multipart/form-data
file: <图片文件>
```

**Response**
```json
{
  "success": true,
  "data": {
    "customer": {...},
    "samples": [...],
    "remarks": "...",
    "raw_texts": [...],
    "total_lines": 43
  }
}
```

### GET /api/health

检查服务状态。

```json
{
  "status": "ok",
  "paddleocr": "ready"
}
```

## 识别优化建议

1. **图片质量**：扫描仪 300+ DPI 效果最佳，手机拍照确保光线充足
2. **表格识别**：PaddleOCR 支持 `table` 模式，可进一步提升表格结构解析
3. **模型升级**：使用 `PP-OCRv4` 服务器版模型（`use_doc_orientation_classify=True`）
4. **置信度过滤**：低于 0.7 的识别结果可提示人工复核

## 技术栈

| 层次 | 技术 |
|------|------|
| OCR 引擎 | PaddleOCR 2.7+ (PP-OCRv4) |
| 后端框架 | Flask 3.0+ |
| 前端 | 原生 HTML5 + CSS3 + ES6 |
| 部署 | 单机 Python 服务 / 可容器化 |
