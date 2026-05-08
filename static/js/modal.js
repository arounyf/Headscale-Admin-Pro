/**
 * Modal / Confirm 对话框 (Alpine)
 *
 * 使用:
 * - Modal: dispatchEvent('modal:open', { title, body, onConfirm })
 * - Confirm: dispatchEvent('confirm:open', { msg, onConfirm, onCancel })
 */
document.addEventListener('alpine:init', () => {
  // ── Modal ──
  Alpine.data('globalModal', () => ({
    show: false,
    title: '',
    body: '',
    confirmText: '确定',
    cancelText: '取消',
    showFooter: true,
    onConfirm: null,

    init() {
      document.addEventListener('modal:open', (e) => {
        const { title, body, confirmText, cancelText, showFooter, onConfirm } = e.detail;
        this.title = title || '';
        this.body = body || '';
        this.confirmText = confirmText || '确定';
        this.cancelText = cancelText || '取消';
        this.showFooter = showFooter !== false;
        this.onConfirm = onConfirm || null;
        this.show = true;
      });
      document.addEventListener('modal:close', () => { this.show = false; });
    },

    close() { this.show = false; },

    confirm() {
      if (this.onConfirm) this.onConfirm();
      this.show = false;
    }
  }));

  // ── Confirm ──
  Alpine.data('globalConfirm', () => ({
    show: false,
    msg: '',
    onConfirm: null,
    onCancel: null,

    init() {
      document.addEventListener('confirm:open', (e) => {
        const { msg, onConfirm, onCancel } = e.detail;
        this.msg = msg || '';
        this.onConfirm = onConfirm || null;
        this.onCancel = onCancel || null;
        this.show = true;
      });
    },

    close() { this.show = false; },

    confirm() {
      if (this.onConfirm) this.onConfirm();
      this.show = false;
    },

    cancel() {
      if (this.onCancel) this.onCancel();
      this.show = false;
    }
  }));
});

// ── 便捷函数 ──
function openModal(title, body, onConfirm, opts = {}) {
  document.dispatchEvent(new CustomEvent('modal:open', {
    detail: { title, body, onConfirm, ...opts }
  }));
}

function openConfirm(msg, onConfirm, onCancel) {
  document.dispatchEvent(new CustomEvent('confirm:open', {
    detail: { msg, onConfirm, onCancel }
  }));
}
