---
name: gh-defaults-to-upstream-repo
description: 在 /root/headscale 里跑 gh 默认查的是上游 juanfont/headscale，不是 fork —— 必须加 -R arounyf/headscale
metadata:
  node_type: memory
  type: project
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-27T15:30:50.460Z
---

`/root/headscale` 有两个 remote：`origin` = `git@github.com:arounyf/headscale.git`（fork）、
`upstream` = `https://github.com/juanfont/headscale.git`。但 `gh` 在这个目录下解析出来的是
**上游 `juanfont/headscale`**。

症状（2026-09-27 实际踩到）：推完 tag 后 `gh run list` 列的全是上游的 workflow
（Tests / Release / Lint / Build / CodeQL / pages-build-deployment），自己刚触发的 run
**一条都不出现**，看起来像"CI 没触发"；`gh run list --workflow=build-runyf.yml` 直接
`HTTP 404`，报错里的路径是 `.../repos/juanfont/headscale/actions/workflows/build-runyf.yml`
—— 这行 404 里的仓库名才是唯一可靠的线索。

**How to apply:** 这个目录下所有 `gh` 命令显式加 `-R arounyf/headscale`。
另外这台机器没有直连外网，`gh` 要走代理：`HTTPS_PROXY=http://<代理地址>`。
相关：[[headscale-integration-tests-offline]]、[[headscale-release-tag-and-panel-bundle]]
