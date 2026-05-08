/**
 * Toast 消息组件 (Alpine)
 *
 * 使用: showToast('操作成功', 'success') 或 dispatchEvent
 * icons: success | error | warning | info
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('toastContainer', () => ({
    toasts: [],

    init() {
      document.addEventListener('toast:show', (e) => {
        this.add(e.detail.msg, e.detail.icon);
      });
    },

    add(msg, icon = 'info') {
      const id = Date.now() + Math.random();
      this.toasts.push({ id, msg, icon });
      setTimeout(() => this.remove(id), 3000);
    },

    remove(id) {
      this.toasts = this.toasts.filter(t => t.id !== id);
    },

    iconHtml(icon) {
      const icons = {
        success: `<svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`,
        error: `<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`,
        warning: `<svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>`,
        info: `<svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
      };
      return icons[icon] || icons.info;
    },

    bgClass(icon) {
      const map = { success: 'border-emerald-400', error: 'border-red-400', warning: 'border-amber-400', info: 'border-blue-400' };
      return `bg-white/95 backdrop-blur border-l-4 ${map[icon] || map.info} shadow-lg`;
    }
  }));
});
