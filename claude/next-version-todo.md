# 下个版本待办

攒着，下个版本一起改。一条写清 **是什么 / 为什么 / 怎么改**。

---

## 1. ~~面板出厂 `server_url` 指向容器名~~ ✅ 已完成 2026-10-06

> **完成情况**（下面的分析保留，仍有参考价值）：
>
> - `config-example.yaml:15` → `server_url: 'http://<你的域名>:8080'`，上方补了 3 行中文注释
>   （是什么 / 在哪改 / 不改的后果）。**用了尖括号** —— 见下面「怎么改」里被推翻的那条结论。
> - **连带修了 `templates/admin/deploy.html:332`**：原来是裸 `{{ server_url }}` 注进 `<script>`，
>   尖括号会被转义成 `&lt;` 留在 JS 串里。改成 `'--login-server=' + {{ server_url|tojson }}`。
> - `README.md` 第 2 步展开成 4 行：`server_url` 是什么、填什么（给了局域网和反代两个例子）、
>   不改会怎样、以及它对应 `config.yaml` 的哪一项、在设置页保存时会重写该文件。
> - **验收升级为真二进制实测**（不再是「把函数抄出来跑」）：在 测试机上用
>   `headscale --force configtest`，A/B 两份配置只差 `server_url` 一个变量
>   （路径全改到容器内 `/tmp/hs-scratch`，不碰线上库），新旧值**都 `EXIT=0`**；
>   又清掉 scratch 库用全新库重跑一次新的，完整走完建表+迁移、仍 `EXIT=0`。
>   scratch 已删，测试机上实例未受影响（容器 `Up`、`GET /` 200）。
> - 仓库里其余 `hs-admin` 字串都是镜像名/容器名（`.github/workflows/main.yml`、
>   `docker-compose.yml`），**不是** `server_url`，保持原样。

### 是什么

`config-example.yaml:12` 出厂值：

```yaml
server_url: 'http://hs-admin'
```

容器名、没端口。这个键是 headscale 自己的配置项（面板设置页那个 `serverUrl` 输入框改的就是它），
同时也是面板部署页拼进给用户命令里的一段 —— `templates/admin/deploy.html:332`：

```js
var parts = ['tailscale', 'up', '--login-server={{ server_url }}'];
```

面板 README 里**完全没提** `server_url`。

### 为什么

面板部署页给出的第一条命令会是 `tailscale up --login-server=http://hs-admin`。
`hs-admin` 是容器名，公网／局域网客户端都解析不了；失败信息只说 DNS 解析不了，不会指向 `server_url`。
所以新用户大概率要先失败一次，才回头找到设置页那个字段。

> **未实证**：这条命令我没有实际跑过，是从一台客户端上 `getent hosts hs-admin` 解析失败推出来的。
> 推理链是通的（部署页确实拼的就是这个值），但没有跑过。

**严重性不高** —— 面板（:5000）和 headscale（:8080）是两个进程、两个地址。面板能进，
就能在设置页自救：`templates/admin/set.html:73` 的 `serverUrl` 输入框（autosave，`data-key="SERVER_URL"`）
改完会重写 `config.yaml`。所以这是**首次体验的 papercut，不是死路**。

### 怎么改

1. 出厂值换成一个一眼就知道要替换的占位符；
2. README 补一句：`server_url` 是什么、在哪改、该填什么。

**⚠️ 这条下的结论 2026-10-06 被推翻了，别照它做。** 原文写的是「占位符别用尖括号」，
理由是尖括号会被 autoescape 转成 `&lt;` 而 `<script>` 不解码实体。
**机制描述是对的，实测也确实是这个结果**（拿真 Jinja 渲染那一行、再按 raw text 规则
喂给 node 求值）：

```
tailscale up --login-server=http://&lt;你的域名&gt;:8080
```

**但结论下反了** —— 该修的不是占位符，是 `deploy.html` 的注入方式。
用户 2026-10-06 明确要求用尖括号占位符，改完发现真正的问题在模板这一侧。
正确做法是 `{{ server_url|tojson }}`：`tojson` 把 `<` `>` `&` `'` 转成 `<` 这类
**JS 层**转义，在 `<script>` 里安全（闭不了标签），JS 取到的又是原值。

**由此得出一条通用规则：任何注入 `<script>` 的配置值都必须走 `|tojson`，不能用裸 `{{ }}`。**
HTML 属性位置（如 `set.html:73` 的 `value="{{ server_url }}"`）则相反 —— 那里转义是对的，
浏览器会解码，不要改。

所以占位符**可以用尖括号，而且更好**（一眼就知道要替换）。

**顺带核实过：换占位符不会让 headscale 起不来。** 启动路径上 `server_url` 只被解析一次 ——
`hscontrol/types/config.go:1363` 的 `isSafeServerURL()`（且只在 `dns.base_domain` 非空时调用）。
它只做 `url.Parse` + 跟 `base_domain` 比字符串；Go 的 `encodeHost` 显式放行 `<` `>`，两处都返回 nil。
其余用到 `ServerURL` 的地方（`app.go` / `noise.go` / `debug.go` / `oidc.go` / `state.go`）
全是字符串拼接或 `HasPrefix`。

把 `isSafeServerURL` 逐字抄出来跑（base_domain 取面板配置里的 `example.com`）：

```
"http://hs-admin"                -> <nil>
"http://<你的域名或IP>:8080"       -> <nil>
"http://YOUR_DOMAIN:8080"        -> <nil>
""                               -> <nil>
```

连空字符串都能过 —— headscale 对 `server_url` 没有任何兜底，错值是静默生效的。

（2026-10-06 补充：上面这段「抄出来跑」已被真二进制 `configtest` 取代，见顶部完成情况。
函数本身读下来也确认了守卫在 `config.go:1242` 的 `if dnsConfig.BaseDomain != ""` ——
而出厂 `base_domain: example.com` 非空，所以这条校验在默认配置下**确实会执行**，
不是被跳过的死代码。）
