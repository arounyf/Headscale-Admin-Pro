---
name: headscale-policy-file-mode-write
description: 本 fork 的 SetPolicy 支持 file 模式（2026-09-25 起），面板保存 ACL 已改为交给 headscale 落盘
metadata:
  node_type: memory
  type: project
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-26T09:09:08.942Z
---

2026-09-25 在 `/root/headscale`（分支 `hs-admin`）给 `SetPolicy` 去掉了 `policy.mode != database` 的硬闸门：`db.SetPolicyBytes(cfg, data)` 按 mode 落库或落 `policy.path`（同目录临时文件 + rename 原子替换，沿用原文件权限），校验并应用在落盘之前，所以坏策略到不了磁盘。CLI 的 `policy set -f` 的 bypass 分支同一天改成按 mode 落盘（以前在 file 模式下静默写进一张没人读的表）。

同级事实：**测试机上的 `/etc/headscale` 是 bind mount，源在宿主 `/root/hs-admin/config/`**（`/app` ← `/root/hs-admin/app`，`/var/lib/headscale` ← `/root/hs-admin/data`）。所以容器里的 `acl.hujson` 就是宿主上那个文件，改动前最好先 `md5sum` 存一份，SIGHUP 不是唯一出路。

⚠️ **别改宿主的 `/etc/headscale/acl.hujson`** —— 那个是个 2026-06-20 的陈旧残留（328 B），跟线上文件不是同一个（线上在 `/root/hs-admin/config/`，379 B，md5 `258c88c0b29b8b57e37c2ba7a34c06cf`）。改了会静默无效。判据：`docker inspect hs-admin --format '{{json .Mounts}}'`。

**Why:** 面板 `blueprints/acl.py` 的 `save_acl` 已不再自己写文件 + `kill -HUP`，改为把内容写进临时文件后调 `headscale policy set -f`，把 headscale 的原话回给前端（前端 `jumpToError` 认 `line N, column M`）。代价是 **headscale 没在跑时保存会失败**（换来的是不再出现「保存成功」其实没生效）。

**How to apply:** 再动 ACL 相关代码时，落盘方一律是 headscale，面板只做搬运；改完 `/app` 里的 Python 需要重启容器里的进程才生效（`docker restart hs-admin` 会连 headscale 一起重启，节点会重连但会自己回来 —— 实测 node-a/node-b 都恢复 online）。相关：[[hujson-standardize-mutates-input]]、[[admin-pro-frontend-hot-reload]]
