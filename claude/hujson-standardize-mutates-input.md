---
name: hujson-standardize-mutates-input
description: hujson.Parse + Standardize 会就地改写调用方的 byte slice（注释变空格），校验后再拿同一个 slice 落盘会把注释写坏
metadata:
  node_type: memory
  type: reference
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-25T16:28:08.446Z
---

`hscontrol/policy/v2/types.go` 的 `unmarshalPolicy` 走 `hujson.Parse(b)` → `ast.Standardize()`。这两步**就地**改写 `b` 指向的数组：`Standardize` 把注释替换成等长空格（为了保持字节偏移合法），而 `hujson.Parse` 的 `Value.Pack` 就是 `b` 本身，不复制。

**Why:** 任何「先校验、后用同一个 slice 落盘」的代码都会静默写坏内容 —— 注释消失（变成空格），字节数不变所以哈希/长度看起来还像对的。2026-09-25 在 `cmd/headscale/cli/policy.go` 的 bypass 分支踩到：`policy.NewPolicyManager(policyBytes, ...)` 之后再 `SetPolicyBytes(cfg, string(policyBytes))`，写进 `acl.hujson` 的注释全变空格（旧代码 db 模式同样中招，只是存进库看不出来）。

**How to apply:** 拿用户提交的字节去校验时传副本（`bytes.Clone(x)`），或者先 `string(x)` 存下来再校验；落盘用的必须是校验前的那份。`hscontrol/grpcv1.go` 的 `SetPolicy` 之所以没这个问题，是因为它校验用 `[]byte(p)`（字符串转切片必复制）、落盘用原字符串 `p`。

排查手法：让 headscale 写一个带注释的策略文件，`cat -A` 看注释那行是不是变成一长串空格。相关：[[headscale-policy-file-mode-write]]
