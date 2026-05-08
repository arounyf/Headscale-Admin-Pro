/**
 * CSRF 保护 (兼容 jQuery + fetch)
 * 从 cookie 读取 csrf_token，附加到所有非 GET 请求
 */
(function () {
  function getCSRFToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrf_token\s*=\s*([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  var token = getCSRFToken();
  if (!token) return;

  // 拦截原生 fetch，自动加 X-CSRFToken
  var origFetch = window.fetch;
  window.fetch = function (url, options) {
    options = options || {};
    var method = (options.method || 'GET').toUpperCase();
    if (method !== 'GET') {
      options.headers = options.headers || {};
      if (!options.headers['X-CSRFToken'] && !(options.headers instanceof Headers && options.headers.has('X-CSRFToken'))) {
        if (options.headers instanceof Headers) {
          options.headers.set('X-CSRFToken', token);
        } else {
          options.headers['X-CSRFToken'] = token;
        }
      }
    }
    return origFetch.call(this, url, options);
  };

  // 兼容 jQuery $.ajax（如果 layui 仍在使用）
  function setupAjaxCSRF($) {
    $.ajaxSetup({
      beforeSend: function (xhr, settings) {
        var method = (settings.type || 'GET').toUpperCase();
        if (method !== 'GET' && !settings.crossDomain) {
          xhr.setRequestHeader('X-CSRFToken', token);
        }
      }
    });
  }

  if (typeof layui !== 'undefined' && layui.$) {
    setupAjaxCSRF(layui.$);
  } else {
    document.addEventListener('DOMContentLoaded', function () {
      if (typeof layui !== 'undefined' && layui.$) {
        setupAjaxCSRF(layui.$);
      }
    });
  }
})();
