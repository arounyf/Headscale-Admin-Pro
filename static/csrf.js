/**
 * CSRF 保护辅助脚本
 * 从 cookie 中读取 Flask-WTF 设置的 csrf_token 并附加到所有 AJAX 请求
 * 此文件必须在 layui.js（或 jQuery）之后加载
 */
(function () {
  function getCSRFToken() {
    var match = document.cookie.match(
      /(?:^|;\s*)csrf_token\s*=\s*([^;]*)/
    );
    return match ? decodeURIComponent(match[1]) : "";
  }

  var token = getCSRFToken();
  if (!token) return;

  // 延迟配置，确保 layui/jQuery 已完全初始化
  function setupAjaxCSRF($) {
    $.ajaxSetup({
      beforeSend: function (xhr, settings) {
        var method = (settings.type || "GET").toUpperCase();
        if (method !== "GET" && !settings.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", token);
        }
      },
    });
  }

  // 如果 layui 已加载（同步模式），直接配置
  if (typeof layui !== "undefined" && layui.$) {
    setupAjaxCSRF(layui.$);
  } else {
    // 否则等待 DOM 加载完成后通过 jQuery 配置（兼容非 layui 页面）
    document.addEventListener("DOMContentLoaded", function () {
      if (typeof layui !== "undefined" && layui.$) {
        setupAjaxCSRF(layui.$);
      }
    });
  }
})();
