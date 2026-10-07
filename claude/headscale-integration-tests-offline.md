---
name: headscale-integration-tests-offline
description: 这台机器上 route/HA 集成测试基本跑不通（Webservice 绕过不了构建），改用 hscontrol/servertest —— 它已覆盖路由和 HA
metadata:
  node_type: memory
  type: project
  originSessionId: 825a58f9-dee3-421b-bc8f-9b8d9527999e
  modified: 2026-09-27T15:50:56.244Z
---

2026-09-26 花了几小时实测，结论是**别在这台机器上追 route/HA 集成测试**。

**先看结论：`hscontrol/servertest` 已经覆盖了路由和 HA，纯进程内，不用 Docker、不用联网。**
`TestSameRouteCrossUser`（多用户路由隔离）、`TestRoutes/ha_secondary_recovers_after_all_offline`
（HA secondary 恢复）都在里面，单包跑 50 秒左右。要验路由逻辑先跑这个，不要碰 `hi`。

## 先纠正一个说法：这台机器不是「离线」

没有直连外网（实测全是 `000`），但**有可用代理**（内网 HTTP 代理）—— 走它
`proxy.golang.org` 和 `github.com` 都返回 200；Docker daemon 也配了 `registry-mirrors`
（`docker.1ms.run` / `docker.xuanyuan.me`）。真正的问题是**代理没接进构建链路**：
`cmd/hi/docker.go:234-258` 建测试容器时只传 `HEADSCALE_INTEGRATION_*` / `CI` / `GOCACHE`，
**不透传 `HTTPS_PROXY`**，所以容器里发起的 `docker build` 没有出口。
这是「链路没接上」，不是「没有网」—— 别再说成离线。

## 为什么跑不通

`go run ./cmd/hi run "..."` 有两层网络依赖，且**第二层无解**：

**1. 容器里的 `go test` 下载模块** —— `cmd/hi/docker.go:createGoTestContainer` 只传
`HEADSCALE_INTEGRATION_*` + `GOCACHE` + `CI`，**不透传 `GOPROXY`**。
绕法：`HEADSCALE_INTEGRATION_GO_CACHE=/root/go`（bind 宿主模块缓存到容器 `/go`）。这层能绕。

**2. headscale 镜像的 docker build** —— 这层看测试类型：
- **不带 `ExtraService` 的测试**（如 `TestACLAutogroupSelf`）：走 `hsic.New`，它认
  `HEADSCALE_INTEGRATION_HEADSCALE_IMAGE`（`integration/hsic/hsic.go:512`），
  用宿主预构建的镜像即可绕过。**能跑通。**
- **带 `ExtraService` 的测试**（`integration/scenario.go:1750-1763` 的 `Webservice`）：
  它**写死了 `pool.BuildAndRunWithBuildOptions`，完全不认那个环境变量** → 必然走构建 → 离线必挂。
  **所有 route 测试和所有 HA 测试都属于这一类**，所以它们在这台机器上根本跑不起来。
  另外这类测试的 `Versions` 都写死 `["head"]`，还要从源码构建 tailscale
  （`Dockerfile.tailscale-HEAD` 里 `git clone github.com/tailscale/tailscale` + `go install`），
  那是第二重网络依赖。

## 试过但不可靠的绕法（别重复）

**填 legacy builder 缓存**：dockertest 走的是 Docker **legacy `/build` API**，跟
`docker build`（BuildKit）的缓存是**两个独立存储**，所以宿主 BuildKit 构建再多也没用，
必须 `DOCKER_BUILDKIT=0`。而且**只能用环境变量传代理**
（`HTTPS_PROXY=... docker build ...`），**不能用 `--build-arg HTTPS_PROXY=...`** ——
显式 build-arg 会写进缓存键，导致后续无参构建全部 miss（表现为「dlv 那层命中、
`go mod download` 那层不命中」的半命中假象）。即便全做对，也只救得了不带 `ExtraService`
的测试，route/HA 那批还是过不了 `Webservice` 这关。

**Why:** `Webservice` 不认 `HEADSCALE_INTEGRATION_HEADSCALE_IMAGE` 是实现缺口，不是配置问题。
真要跑，得改 `integration/scenario.go` 的 `Webservice` 让它跟 `hsic.New` 一样先看环境变量
—— 那是改上游测试基础设施，没得到用户明确同意不要动。

**How to apply:** 验 headscale 逻辑优先级是 `go test ./hscontrol/servertest/` >
`go test ./...` > 集成测试。集成测试留给「需要真 tailscale 客户端行为」的场景（如
`TestACLAutogroupSelf` 那种不带 `ExtraService` 的），且必须修好 GOPROXY 那层。
判据看容器名：出现 `hs-webservice-*` 就说明踩到 `Webservice` 了。
相关：[[headscale-hot-swap-deploy-gotchas]]
