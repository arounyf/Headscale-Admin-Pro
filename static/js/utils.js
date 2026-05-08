/**
 * 通用工具函数
 */

// ── CSRF Token ──
function getCSRFToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token\s*=\s*([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

// ── fetch 封装 (自动 CSRF) ──
async function api(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { ...options.headers };

  if (method !== 'GET') {
    const token = getCSRFToken();
    if (token) headers['X-CSRFToken'] = token;
  }

  // auto content-type for JSON body
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const resp = await fetch(url, { ...options, method, headers });
  const data = await resp.json();
  return data; // { code, msg, data }
}

// ── AJAX POST (兼容 FormData，用于简单场景) ──
async function apiPost(url, formData) {
  const token = getCSRFToken();
  const headers = {};
  if (token) headers['X-CSRFToken'] = token;

  const resp = await fetch(url, {
    method: 'POST',
    headers,
    body: formData instanceof FormData ? formData : new URLSearchParams(formData),
  });
  return resp.json();
}

// ── 通用 toast ──
function showToast(msg, icon) {
  if (typeof Alpine !== 'undefined') {
    document.dispatchEvent(new CustomEvent('toast:show', { detail: { msg, icon } }));
    return;
  }
  // 降级：简单 alert
  alert(msg);
}

// ── 时间格式化 ──
function timeAgo(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);

  if (diff < 60) return '刚刚';
  if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
  if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
  if (diff < 2592000) return Math.floor(diff / 86400) + '天前';
  return date.toLocaleString('zh-CN');
}

// ── URL 参数解析 ──
function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

// ── HTML 转义 ──
function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
