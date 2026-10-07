---
name: verify-release-effects-before-tagging
description: 推 release tag 前必须核实 CI 实际会推哪些 tag/镜像，别拿 workflow 的日志文案当行为描述
metadata:
  node_type: memory
  type: feedback
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-27T15:50:39.990Z
---

2026-09-27：推面板 `v5.4-beta` 之前我跟用户说「不会动 `:latest`」，依据是 workflow 里
`Determine if stable release` 那步打印了 `Pre-release: v5.4-beta (no :latest)`。实际上那步
只控制后面显式的 `imagetools create --tag latest`；真正决定 tag 列表的是
`docker/metadata-action` 的默认 `flavor: latest=auto` —— 它对**任何** tag 事件都追加
`:latest`（`src/meta.ts:280` 的 `procRefTag` 无条件返回 true，连 semver 判断都没有）。
结果 beta 把 `:latest` 从 v5.3 顶掉了，而 `:latest` 正是面板升级文档里让大家用的通道。

**Why:** 那句话被用户当成了判断依据，而它错得毫无根据 —— 我只读了 workflow 的意图，
没读它依赖的 action 的默认行为，推之前也没用任何方式验证过实际 tag 列表。对外动作
（打 tag、推镜像）发生后就很难干净地撤回，恢复只能删 tag 重新推、还会连带覆盖 Release
正文，代价远超事前核实。

**How to apply:** 推 release tag 前，把「CI 实际会产出什么」列出来并核实：读依赖 action
的源码/默认值，或先在废弃 tag 上试。**不要把 workflow 里的 echo 文案当成对行为的描述。**
没核实就说「我没验证过」，别把推测讲成保证。

相关：[[headscale-release-tag-and-panel-bundle]]、[[gh-defaults-to-upstream-repo]]
