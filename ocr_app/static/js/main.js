/* ═══════════════════════════════════════════════════════════════
   前端主逻辑 — 艾康健 OCR 识别系统
   ═══════════════════════════════════════════════════════════════ */

// ─── 主题切换 ────────────────────────────────────────────────────
const themeToggle = document.getElementById('themeToggle');
const iconSun     = document.getElementById('iconSun');
const iconMoon    = document.getElementById('iconMoon');

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  if (theme === 'dark') {
    iconSun.style.display  = 'none';
    iconMoon.style.display = '';
  } else {
    iconSun.style.display  = '';
    iconMoon.style.display = 'none';
  }
}

;(function initTheme() {
  const saved = localStorage.getItem('theme');
  if (saved) { applyTheme(saved); return; }
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) applyTheme('dark');
})();

themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

// ─── DOM 引用 ────────────────────────────────────────────────────
const dropZone      = document.getElementById('dropZone');
const fileInput     = document.getElementById('fileInput');
const selectBtn     = document.getElementById('selectBtn');
const changeBtn     = document.getElementById('changeBtn');
const dropContent   = document.getElementById('dropContent');
const dropPreview   = document.getElementById('dropPreview');
const previewImg    = document.getElementById('previewImg');
const recognizeBtn  = document.getElementById('recognizeBtn');
const recognizeBtnText = document.getElementById('recognizeBtnText');
const progressWrap  = document.getElementById('progressWrap');
const progressFill  = document.getElementById('progressFill');
const progressLabel = document.getElementById('progressLabel');
const emptyState    = document.getElementById('emptyState');
const resultContent = document.getElementById('resultContent');
const resultActions = document.getElementById('resultActions');

// 结果区
const customerGrid  = document.getElementById('customerGrid');
const samplesBody   = document.getElementById('samplesBody');
const sampleCount   = document.getElementById('sampleCount');
const emptyTable    = document.getElementById('emptyTable');
const remarksSection= document.getElementById('remarksSection');
const remarksContent= document.getElementById('remarksContent');
const statsRow      = document.getElementById('statsRow');
const rawTextContainer = document.getElementById('rawTextContainer');
const jsonViewer    = document.getElementById('jsonViewer');

let currentFile = null;
let lastResult  = null;

// ─── 文件选择 ────────────────────────────────────────────────────
selectBtn.addEventListener('click', () => fileInput.click());
changeBtn && changeBtn.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
dropZone.addEventListener('click', () => { if (!currentFile) fileInput.click(); });

fileInput.addEventListener('change', e => {
  const f = e.target.files[0];
  if (f) loadFile(f);
  fileInput.value = ''; // reset so same file can be reloaded
});

// ─── 拖拽 ─────────────────────────────────────────────────────────
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) loadFile(f);
});

function loadFile(file) {
  if (!file.type.startsWith('image/')) {
    showToast('请上传图片文件（JPG / PNG / TIFF 等）', 'error');
    return;
  }
  currentFile = file;
  const url = URL.createObjectURL(file);
  previewImg.src = url;
  dropContent.style.display = 'none';
  dropPreview.style.display = '';
  recognizeBtn.disabled = false;
}

// ─── 识别流程 ─────────────────────────────────────────────────────
recognizeBtn.addEventListener('click', async () => {
  if (!currentFile) return;

  setRecognizing(true);

  const steps = [
    [10,  '正在上传图片...'],
    [30,  '加载 PaddleOCR 引擎...'],
    [55,  '文字区域检测中...'],
    [75,  '文字识别中（中文）...'],
    [90,  '结构化解析中...'],
  ];

  let stepIdx = 0;
  const stepInterval = setInterval(() => {
    if (stepIdx < steps.length) {
      setProgress(...steps[stepIdx]);
      stepIdx++;
    }
  }, 600);

  try {
    const fd = new FormData();
    fd.append('file', currentFile);

    const resp = await fetch('/api/ocr', { method: 'POST', body: fd });
    clearInterval(stepInterval);

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error || `HTTP ${resp.status}`);
    }

    const { data } = await resp.json();
    setProgress(100, '识别完成！');

    setTimeout(() => {
      renderResult(data);
      lastResult = data;
      setRecognizing(false);
      showToast(`识别成功，共 ${data.total_lines} 行文本`, 'success');
    }, 400);

  } catch (err) {
    clearInterval(stepInterval);
    setRecognizing(false);
    showToast(`识别失败: ${err.message}`, 'error');
    console.error(err);
  }
});

function setRecognizing(active) {
  recognizeBtn.disabled = active;
  progressWrap.style.display = active ? '' : 'none';
  if (active) {
    recognizeBtnText.innerHTML = '<span class="spinner"></span> 识别中...';
    setProgress(5, '准备中...');
  } else {
    recognizeBtnText.textContent = '重新识别';
    recognizeBtn.disabled = false;
  }
}

function setProgress(pct, label) {
  progressFill.style.width = pct + '%';
  progressLabel.textContent = label;
}

// ─── 渲染结果 ─────────────────────────────────────────────────────
function renderResult(data) {
  emptyState.style.display = 'none';
  resultContent.style.display = '';
  resultActions.style.display = '';

  renderCustomer(data.customer || {});
  renderSamples(data.samples || []);
  renderRemarks(data.remarks || '');
  renderRawText(data.raw_texts || [], data);
  renderStats(data);
  renderJson(data);
}

// 客户信息
function renderCustomer(customer) {
  const labels = {
    '客户姓名': '客户姓名',
    '联系电话': '联系电话',
    'email':    'E-mail',
    '所属课题组': '课题组',
    '详细地址': '详细地址',
    '客户单位': '客户单位',
    '送测日期': '送测日期',
  };
  customerGrid.innerHTML = Object.entries(labels).map(([key, label]) => {
    const val = customer[key] || '';
    return `
      <div class="info-cell">
        <div class="info-cell__label">${label}</div>
        <div class="info-cell__value ${val ? '' : 'info-cell__value--empty'}">
          ${val ? escHtml(val) : '未识别'}
        </div>
      </div>`;
  }).join('');
}

// 样品表格
function renderSamples(samples) {
  samplesBody.innerHTML = '';
  if (samples.length === 0) {
    document.querySelector('.table-scroll').style.display = 'none';
    emptyTable.style.display = '';
    sampleCount.textContent = '';
    return;
  }
  document.querySelector('.table-scroll').style.display = '';
  emptyTable.style.display = 'none';
  sampleCount.textContent = `（共 ${samples.length} 条样品）`;

  const cols = ['样品名称','样品类型','载体名称','抗性','片段长度','引物类别','正向引物','反向引物','原始内容'];

  samples.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><span class="row-num">${s['序号'] || '-'}</span></td>` +
      cols.map(c => `<td title="${escHtml(s[c] || '')}">${escHtml(s[c] || '—')}</td>`).join('');
    samplesBody.appendChild(tr);
  });
}

// 备注
function renderRemarks(text) {
  if (!text || text.trim().length < 5) {
    remarksSection.style.display = 'none';
    return;
  }
  remarksSection.style.display = '';
  remarksContent.textContent = text;
}

// 原始文本
function renderRawText(texts, data) {
  // 重新从 data 中取完整信息（含 confidence）
  rawTextContainer.innerHTML = '';
  // raw_texts 是纯文本，若 lines 可用则加置信度
  const lines = (data._lines || []);
  if (lines.length) {
    lines.forEach((l, i) => {
      const conf = l.confidence;
      const cls  = conf >= 0.9 ? 'conf--high' : conf >= 0.7 ? 'conf--mid' : 'conf--low';
      rawTextContainer.innerHTML += `
        <div class="raw-line">
          <span class="raw-line__idx">${i + 1}</span>
          <span class="raw-line__text">${escHtml(l.text)}</span>
          <span class="raw-line__conf ${cls}">${(conf * 100).toFixed(0)}%</span>
        </div>`;
    });
  } else {
    texts.forEach((t, i) => {
      rawTextContainer.innerHTML += `
        <div class="raw-line">
          <span class="raw-line__idx">${i + 1}</span>
          <span class="raw-line__text">${escHtml(t)}</span>
        </div>`;
    });
  }
}

// 统计
function renderStats(data) {
  statsRow.innerHTML = `
    <span class="stat-chip">识别行数 <strong>${data.total_lines}</strong></span>
    <span class="stat-chip">样品条数 <strong>${(data.samples || []).length}</strong></span>
    <span class="stat-chip">客户字段 <strong>${Object.values(data.customer || {}).filter(Boolean).length} / 7</strong></span>
  `;
}

// JSON
function renderJson(data) {
  // 清理内部字段
  const clean = JSON.parse(JSON.stringify(data));
  delete clean._lines;
  jsonViewer.textContent = JSON.stringify(clean, null, 2);
}

// ─── Tab 切换 ────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('tab--active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('tab-pane--active'));
    tab.classList.add('tab--active');
    const pane = document.getElementById('tab-' + tab.dataset.tab);
    if (pane) pane.classList.add('tab-pane--active');
  });
});

// ─── 复制 / 导出 ─────────────────────────────────────────────────
function copyToClipboard(text, label) {
  navigator.clipboard.writeText(text).then(() => {
    showToast(`${label}已复制到剪贴板`, 'success');
  }).catch(() => {
    showToast('复制失败，请手动复制', 'error');
  });
}

document.getElementById('copyJsonBtn').addEventListener('click', () => {
  if (!lastResult) return;
  const clean = JSON.parse(JSON.stringify(lastResult));
  delete clean._lines;
  copyToClipboard(JSON.stringify(clean, null, 2), 'JSON');
});

document.getElementById('copyJsonInline').addEventListener('click', () => {
  copyToClipboard(jsonViewer.textContent, 'JSON');
});

document.getElementById('exportCsvBtn').addEventListener('click', () => {
  if (!lastResult) return;
  exportCsv(lastResult);
});

function exportCsv(data) {
  const header = ['序号','样品名称','样品类型','载体名称','抗性','片段长度','引物类别','正向引物','反向引物'];
  const rows = (data.samples || []).map(s =>
    header.map(k => `"${(s[k] || '').replace(/"/g, '""')}"`)
  );

  // 客户信息行
  const customerLine = Object.entries(data.customer || {}).map(([k,v]) => `${k}: ${v}`).join(' | ');

  const csv = [
    `# 客户信息,${customerLine}`,
    header.join(','),
    ...rows.map(r => r.join(',')),
  ].join('\n');

  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `测序订单_${new Date().toLocaleDateString('zh-CN')}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('CSV 已下载', 'success');
}

// ─── Toast ───────────────────────────────────────────────────────
function showToast(msg, type = 'info', duration = 3000) {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;

  const icons = {
    success: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16" style="color:var(--green)"><path d="M4 10l4 4 8-8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    error:   '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16" style="color:var(--red)"><line x1="6" y1="6" x2="14" y2="14" stroke-linecap="round"/><line x1="14" y1="6" x2="6" y2="14" stroke-linecap="round"/></svg>',
    info:    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16" style="color:var(--accent)"><circle cx="10" cy="10" r="8"/><path d="M10 9v5" stroke-linecap="round"/><circle cx="10" cy="6.5" r="0.75" fill="currentColor" stroke="none"/></svg>',
  };

  toast.innerHTML = `${icons[type] || ''} <span>${escHtml(msg)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── 工具函数 ────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
