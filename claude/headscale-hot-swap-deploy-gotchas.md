---
name: headscale-hot-swap-deploy-gotchas
description: 在 测试机上热替换 headscale 二进制时 AGENTS.md 记的那两条命令都不够用（Text file busy + 没有守护进程）
metadata:
  node_type: memory
  type: project
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-26T07:54:29.619Z
---

2026-09-26 实测：AGENTS.md「Test server: always hot-swap, never rebuild」里那段

```bash
docker exec hs-admin cp /app/headscale /usr/bin/headscale
docker exec hs-admin pkill headscale
```

**执行会静默失效**，两个坑：

1. `cp` 报 `Text file busy` —— headscale 进程正跑在这个 inode 上，`cp` 不能就地覆写。正确做法是先写到同目录临时名再 rename：
   `docker exec hs-admin sh -c 'cp /app/headscale /usr/bin/headscale.new && chmod u+x /usr/bin/headscale.new && mv -f /usr/bin/headscale.new /usr/bin/headscale'`
2. `pkill` 之后**没有任何东西会把它拉起来**。`app.py:49` 只在面板启动时调一次 `start_headscale()`；另一个入口是面板 `POST /api/set/switch_headscale`（`blueprints/set.py`），但它挂了 `@login_required` + 验证码 + CSRFProtect，脚本登录不了。所以停掉之后要自己起，且要起成 argv 恰好是 `['headscale','serve']`（面板 `utils.py:_headscale_serve_pids()` 按精确 argv 认进程）：
   `docker exec -d hs-admin sh -c 'headscale serve >> /var/lib/headscale/headscale.log 2>&1'`

**Why:** 第一次照 AGENTS.md 做，`cp` 失败我没细看，接着 `pkill` 又把旧进程 SIGTERM 了，然后"重启"起来的还是旧二进制 —— 表面 `/health` 200、节点都回来了，其实一个字节都没换。

判断停/起**别用 `pgrep -x headscale`**：被 SIGTERM 的旧进程会变成僵尸（父进程 `app.py` 从不 reap），`pgrep` 一直命中它。用 `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/health` 当存活判据（停掉后是 000）。

**How to apply:** 换二进制按「临时名+mv → 等 `/health` 变 000 → detach 启动 → 等 `/health` 回 200 → `headscale version` 核对 commit」这个顺序；核对这一步不能省，`/health` 200 不代表换成功了。版本号里的 `+dirty` 是本地未提交构建，`parseVersion` 能吃（实测能把 `v0.29.4-hs+dirty` 存进 `database_versions` 并在下次启动通过版本门）。回滚只要把备份的二进制再 mv 回去，因为 schema 是纯追加的，旧二进制对新库照样 `squibble.Validate` 通过。相关：[[headscale-policy-file-mode-write]]、[[admin-pro-frontend-hot-reload]]
