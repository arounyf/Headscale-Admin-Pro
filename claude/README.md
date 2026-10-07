# claude/

给 AI 用的操作手册 + 两个仓库文档的集中入口。

**这是「标准版」** —— 本目录随 `Headscale-Admin-Pro` 仓库发布（仓库是 public）。
它的用处是：**本地文件全丢了，也能照它把环境重新准备出来、直接接上开发流程**。
所以规矩是：

- 正文里**不写**真实的内网 IP / 公网地址 / 域名 / 口令 —— 一律写成 `生产机` /
  `测试机` / `测试节点` / `<代理地址>` 这类**角色标签**
- **真实值在本地记忆库里**，不进仓库（git 存标准，记忆存实参）
- 新增条目照这个规矩写，别把地址贴回来

一件事一个文件。动手前先按索引查一遍。

```
/root/Headscale-Admin-Pro/claude/
├── README.md          ← 你在这
├── *.md               我们写的说明（规则 / 流程 / 坑），真实文件
├── plans/             已执行完的计划存档
├── headscale/         软链 → /root/headscale 里的 md
└── panel/             软链 → /root/Headscale-Admin-Pro 里的 md
```

## 一、我们写的说明

### 待办 —— 下个版本

| 文件 | 一句话 |
|---|---|
| [next-version-todo.md](next-version-todo.md) | 攒着下个版本一起改。首条（出厂 `server_url` 占位符）**2026-10-06 已完成**；现无待办，等下一条 |

### 规则 —— 做之前必须先满足

| 文件 | 一句话 |
|---|---|
| [verify-release-effects-before-tagging.md](verify-release-effects-before-tagging.md) | 推 release tag 前必须核实 CI **实际**会产出哪些 tag/镜像，别拿 workflow 里的文案当行为描述 |
| [gh-defaults-to-upstream-repo.md](gh-defaults-to-upstream-repo.md) | `/root/headscale` 下跑 `gh` 会解析成上游 `juanfont/headscale`，必须显式 `-R arounyf/headscale` |
| [hujson-standardize-mutates-input.md](hujson-standardize-mutates-input.md) | `hujson.Standardize` 就地改写入参；拿校验过的 slice 去落盘会把注释写成空格 |

### 流程 —— 按顺序执行

| 文件 | 一句话 |
|---|---|
| [prod-release-flow.md](prod-release-flow.md) | **生产上线**：拉版本 + 备份都在停机前做完，停机窗口只留「停 + 清 `/app` + 起」——清 `/app` 漏了就是白升且不报错 |
| [headscale-hot-swap-deploy-gotchas.md](headscale-hot-swap-deploy-gotchas.md) | 测试机上换 headscale 二进制：`cp` 报 Text file busy、`pkill` 后没人拉起；正确顺序与判活方法 |
| [admin-pro-frontend-hot-reload.md](admin-pro-frontend-hot-reload.md) | 改模板/静态资源 rsync 即生效，不用重启；Python 代码和二进制才要重启 |
| [headscale-policy-file-mode-write.md](headscale-policy-file-mode-write.md) | 线上 ACL 落在宿主 `/root/hs-admin/config/`，不是 `/etc/headscale/` |
| [panel-e2e-testing.md](panel-e2e-testing.md) | **面板 E2E 测试**：脚本在 测试机的 `/root/hs-test/`，验证码靠解签名 session 绕过；多用户路由与 ACL 语义怎么验 |

### 环境与工具

| 文件 | 一句话 |
|---|---|
| [headscale-integration-tests-offline.md](headscale-integration-tests-offline.md) | route/HA 集成测试在这台机器上跑不通（Webservice 绕过不了构建），改用 `hscontrol/servertest` |
| [headless-css-verification.md](headless-css-verification.md) | headless 下 `getComputedStyle` 返回假值；用 canvas ink box 量对齐 |

### 历史方案

[plans/](plans/) —— 已执行完的计划存档，留作「当时为什么这么做」的证据。

## 二、仓库里的相关文档

这几个文件**原位没动**，各自在所属仓库里。本机另有 `claude/headscale/`、`claude/panel/`
软链方便夹览，但那两个目录**不进仓库**（指向仓库外的绝对路径，对别人是断链）。

| 文件 | 在哪 | 为什么不能真移走 |
|---|---|---|
| [headscale/AGENTS.md](../headscale/AGENTS.md) | 仓库 `headscale/` 子树 | 项目指令，每次会话自动加载 |
| [headscale/.github/release-notes/v0.29.4-hs.md](../headscale/.github/release-notes/v0.29.4-hs.md) | 同左 | CI 从仓库内取发布正文（`build-runyf.yml`） |
| [headscale/README.md](../headscale/README.md) | 同左 | 仓库在 GitHub 上的门面 |
| [headscale/CHANGELOG.md](../headscale/CHANGELOG.md) | 同左 | 上游文件，我们在上面追加 |
| [headscale/docs/ref/policy.md](../headscale/docs/ref/policy.md) | 同左 | 上游文档，我们改过 |
| [headscale/docs/about/faq.md](../headscale/docs/about/faq.md) | 同左 | 上游文档，我们改过 |
| [headscale/hscontrol/…/upstream-pre-0.27/README.md](../headscale/hscontrol/db/testdata/sqlite/upstream-pre-0.27/README.md) | 同左 | 挪走的 fixture 的证据，要和数据放一起 |
| [README.md](../README.md) | 仓库根 | 面板在 GitHub 上的门面 |

> 面板仓库里除了这 2 个，剩下的说明就是本目录 `claude/` 下这批。其余（`config-example.yaml`、
> `derp-example.yaml` 等）是配置模板，不是文档。

## 三、环境速查

整套流程要四种角色。**这里只写要准备什么，具体地址按你自己的环境填**
（我们的真实值不进仓库）：

| 角色 | 要准备什么 |
|---|---|
| 生产机 | headscale + Admin-Pro，公网可达；前面有 nginx 反代到面板（80/443） |
| 测试机 | headscale + Admin-Pro，容器叫 `hs-admin`、`network_mode: host`（面板 :5000 / headscale :8080） |
| 测试节点 | 一台能跑 tailscaled 的机器，当客户端用（E2E 要多开几个 statedir） |
| 代理 | 能出外网的 HTTP 代理 —— 构建、`gh`、go modules 都得走它 |

测试机上的挂载（容器是静态壳，只换 `/app` 里的东西）：

```
/root/hs-admin/app    -> /app                 面板代码 + headscale 二进制
/root/hs-admin/config -> /etc/headscale       headscale 配置 + acl.hujson
/root/hs-admin/data   -> /var/lib/headscale   db.sqlite
```

## 四、新增条目

一件事一个文件，正文写清 **是什么 / 为什么 / 怎么用**。`Why:` 和 `How to apply:` 两段别省 —— 只记「怎么做」下次照样会绕回去。

写完在第一节的索引里加一行。

> 同一批说明在 `/root/.claude/projects/-root-headscale/memory/` 还有一份，那是 Claude Code 每次会话自动加载的记忆库（索引是那边的 `MEMORY.md`）。**两边要同步**，否则我不会自动读到这儿的新条目。
