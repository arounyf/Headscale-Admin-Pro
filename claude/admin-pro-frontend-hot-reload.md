---
name: admin-pro-frontend-hot-reload
description: Admin-Pro 改前端模板/静态资源不需要重启容器，rsync 进去即生效；重启会连带打断 headscale 与已连节点
metadata:
  node_type: memory
  type: project
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-25T15:01:11.902Z
---

`/root/Headscale-Admin-Pro` 部署到测试机的容器 `hs-admin` 时，
**改模板和静态资源不需要 `docker restart`**：Flask 跑在 debug 模式，Jinja 的
auto_reload 是开的，`rsync` 进 `/root/hs-admin/app/`（容器内 `/app`）之后刷新页面
就是新的。2026-09-25 接入 CodeMirror 时实测确认：`templates/admin/acl.html` 整页
重写 + 新增 `static/codemirror/`，未重启，服务端返回的页面里新内容全在。

**Why:** 容器里 PID 1 是 `sh -c ./init.sh 'python3 app.py'`，而 headscale serve 是
`python3 app.py` 的子进程。每次 `docker restart hs-admin` 都会顺手把 headscale 打断，
在测试节点上连着测的 tailscale 节点跟着掉线重连 —— 纯前端改动重启是白付这个代价。

**How to apply:** 判据是「这次改的是不是 Python 代码或 headscale 二进制」——
是才重启（`blueprints/*.py`、`utils.py`、`app.py`、`headscale` 二进制），
否则 rsync 完直接让用户刷新。验证不要靠重启后 curl 首页，而是用 [[headless-css-verification]]
里那套只读探针（伪造 cookie 抓 `/admin/...` 的响应字节）确认线上真的换了，这样
全程不动服务。

浏览器端另有一个坑：面板页面在 iframe 里，普通刷新可能命中缓存，让用户按 **Ctrl+F5**。
