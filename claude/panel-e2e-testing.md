# 面板 E2E 测试

跑 Headscale-Admin-Pro 的端到端测试。全部走真实 HTTP（CSRF cookie、wtforms
校验、Flask session），不用 `test_client`，所以测到的就是浏览器会走的那条路径。

**Why:** 面板和 headscale 共用同一个 SQLite，很多缺陷只在「面板写库」和
「headscale 读库」错位时才暴露 —— 越权审批路由、绕过 API 直接删表、兜底配置
和出厂配置不一致，都是这一批测出来的。用 `test_client` 会跳过 CSRF 中间件和
路由挂载，这几类问题正好测不出来。

**How to apply:** 改动面板代码后，按下面顺序跑一遍；`mt_route_test` 和 ACL
语义那两节需要 测试节点上的 tailscale 节点配合。

## 一、环境

测试脚本跑在**测试服务器本身**（面板容器所在那台），不是从别处 ssh 过去跑。

| | |
|---|---|
| 面板 | `http://127.0.0.1:5000`（容器 `hs-admin`，`network_mode: host`） |
| 镜像 | `runyf/hs-admin:v5.4-beta`（`/root/hs-admin/docker-compose.yml`） |
| 脚本 | `/root/hs-test/` |
| 数据库 | `/root/hs-admin/data/db.sqlite` |
| SECRET_KEY | `/root/hs-admin/data/.secret_key` |
| ACL | `/root/hs-admin/config/acl.hujson` |
| 客户端节点 | 内网另一台机器，用 `--statedir=/tmp/mt-<name>` 起多个 tailscaled |

挂载（容器是静态壳，只有 `/app` 里的东西会换）：

```
/root/hs-admin/app    -> /app                 面板代码 + headscale 二进制
/root/hs-admin/config -> /etc/headscale       配置 + acl.hujson
/root/hs-admin/data   -> /var/lib/headscale   db.sqlite + .secret_key
```

容器里 `python3 app.py` 是父进程，`headscale serve` 是它的子进程 ——
`docker restart hs-admin` 会把 headscale 一起重启，已连节点全部掉线重连。
只改模板/静态资源不用重启（见 [admin-pro-frontend-hot-reload.md](admin-pro-frontend-hot-reload.md)）。

## 二、跑之前

测试假设 `admin` 密码是 `<测试口令>`。演示数据的密码如果被改过，先设回来：

```bash
cd /root/hs-test && python3 -c "
import e2e; print(e2e.set_password('/root/hs-admin/data/db.sqlite', 'admin', '<测试口令>'))"
```

**`admin` 自己的「路由」开关必须先打开 —— 审批前先给自己开。**
面板要求审批人本人 `route=1`，**管理员也不例外**（这是缺陷3 修复时刻意做的门控，
提示会指向「用户管理」里那个开关）。全新安装的 `admin` 默认 `route=0`，
此时 `mt_route_test` 的「管理员正常审批两个用户的路由」两项会**假失败**：

```
[FAIL] 审批 a-router(tenant-a) — code=1 库中=["10.99.0.0/24"]
        msg=你当前无此权限，请在「用户管理」里为自己打开「路由」开关
```

登录后开一次即可（一次装好，后续重跑不用再开）：

```bash
cd /root/hs-test && python3 -c "
import e2e
p = e2e.Panel('http://127.0.0.1:5000', open('/root/hs-admin/data/.secret_key').read().strip())
p.login('admin', '<测试口令>')
print(p.post('/api/user/route_enable', data={'user_id': '1', 'enable': 'true'}).json())"
```

确认面板活着、headscale 在 8080 上：

```bash
docker ps --filter name=hs-admin --format '{{.Status}}'
ss -ltnp | grep -E ':5000|:8080'
```

**不要对生产机跑这些脚本** —— 里面会注册用户、建密钥、改 ACL、
审批路由，全是写操作。

## 三、脚本

| 脚本 | 覆盖 | 依赖 |
|---|---|---|
| `hs-test/e2e.py`（在测试机上，不在仓库里） | 辅助库：`Panel` 类、验证码解码、`record/summary` | — |
| `reg_test.py` | 注册 + 登录 + 角色，全新安装环境 | — |
| `func_test.py` | 12 个管理页 + 10 个只读 AJAX 接口 | — |
| `func_write_test.py` | 20 个写操作（密钥、用户开关、设置、日志） | — |
| `mt_route_test.py` | 多用户路由：越权审批 + 隔离 | 测试节点上的客户端 |
| `fix_regress_test.py` | 归属校验 / delKey 走 API 的回归 | — |

统一收尾参数（都有默认值，可省）：`argv[1]` 面板地址、`argv[2]` SECRET_KEY 路径。
`func_test.py` 还接 `argv[3]` 用户名、`argv[4]` 密码。

```bash
cd /root/hs-test
python3 reg_test.py
python3 func_test.py
python3 func_write_test.py
python3 mt_route_test.py
python3 fix_regress_test.py
```

每个脚本以 `汇总: N/M 通过` 结尾，失败项在下面单列。退出码 0 = 全过。

### 验证码怎么绕过的

登录和注册都有图形验证码，但 `/get_captcha` 把真实验证码写进了 Flask 的
**签名** session。用面板自己的 `SECRET_KEY` 把它解出来即可 —— 走的是完整
HTTP 链路，不是把校验关掉：

```python
p.get("/login")          # 拿 csrf_token cookie
p.get("/get_captcha")    # session['code'] = 真实验证码
code = e2e.read_session(p.s.cookies.get("session"), SECRET).get("code")
p.post("/login", data={"username": ..., "password": ..., "vercode": code, ...})
```

`Panel.post` 会自动带上 `X-CSRFToken`（取自 `csrf_token` cookie），别忘了。

## 四、多用户路由测试

场外准备：`tenant-a` 的 `a-router` 和 `tenant-b` 的 `b-router` **同时广告同一个
网段**（`10.99.0.0/24`）。这是用户重点要求验证的场景 —— 两家人用同一个内网段，
流量必须只走自己家的路由器。

### 在测试节点上起节点

```bash
ssh root@<测试节点>
# 每个节点一个独立 statedir + 端口 + socket
tailscaled --state=mem: --statedir=/tmp/mt-a-router --tun=userspace-networking \
  --port=41641 --socket=/tmp/mt-a-router/tailscaled.sock &
tailscale --socket=/tmp/mt-a-router/tailscaled.sock up \
  --login-server=http://<测试机>:8080 --auth-key=<key> --hostname=a-router \
  --advertise-routes=10.99.0.0/24 --accept-routes
```

节点名与用途：`a-client` / `a-router`（tenant-a）、`b-client` / `b-router`
（tenant-b）、`ad-exit` / `ad-node`（管理员，ACL 用）。

### 清理

```bash
ssh root@<测试节点> 'pkill -f "statedir=/tmp/mt[-]"'
```

**方括号不能省。** `pkill -f "statedir=/tmp/mt-"` 会匹配到 ssh 远程命令自己的
argv，把当前这条 ssh 一起杀掉，表现为「命令没输出、连接断开」。用 `[-]` 让模式
本身不匹配字面量即可。

### 同一用户 HA 配对（可选，验证修复没有过度门控）

给同一个用户再起一个**广告同一前缀**的路由器，确认合法配对没被「按 route scope
门控」误伤：

```bash
# 测试机上建密钥
KEY=$(docker exec hs-admin headscale preauthkeys create -u 3 --expiration 1h | tail -1)
# 测试节点上起第二个路由器（必须 setsid，否则 ssh 一断进程就没）
ssh root@<测试节点> "KEY='$KEY' bash -s" <<'EOF'
mkdir -p /tmp/mt-a-router2
setsid nohup tailscaled --state=mem: --statedir=/tmp/mt-a-router2 \
  --tun=userspace-networking --port=42105 \
  --socket=/tmp/mt-a-router2/tailscaled.sock >/tmp/mt-a-router2.log 2>&1 </dev/null &
sleep 5
tailscale --socket=/tmp/mt-a-router2/tailscaled.sock up \
  --login-server=http://<测试机>:8080 --auth-key="$KEY" --hostname=a-router2 \
  --advertise-routes=10.99.0.0/24 --accept-routes
EOF
docker exec hs-admin headscale nodes approve-routes -i <新id> -r 10.99.0.0/24
```

期望：`a-client` 能看到**两个**自家路由器，前缀只挂在其中一个（HA 主），
仍然看不到 `b-router`。**注意 netmap 有延迟** —— 刚批完路由就查会读到旧状态
（看起来前缀还挂在原来那台上），隔十几秒再查才是收敛后的结果。

清理：`pkill -f "statedir=/tmp/mt-a-router2"` + `headscale nodes delete -i <id> --force`。

### 判定隔离

```bash
# 在 a-client 上看它对 10.99.0.0/24 的主路由指向谁
grep -o '10\.99\.0\.0/24[^]]*' /tmp/mt-a-client/*.log
```

权威判据是 netmap 里该网段挂在哪条路由上，不是 `tailscale ping` 通不通。

## 五、ACL 语义测试

面板模板里的两条 ACL 是定制过的：

```
{"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self:*"]}      # 用户自隔离
{"action": "accept", "src": ["group:admin"],    "dst": ["autogroup:internet:*"]}    # 仅管理员可走出口
```

替换掉了上游的 `{"src":["*"],"dst":["*:*"]}`。测这两条的三个要点：

1. **PacketFilter 才是权威产物。** 客户端实际执行的是 netmap 里的 `PacketFilter`，
   判断某条流量是否放行必须看它。
2. **`tailscale ping` 不能当证据。** 它走 disco 协议，绕过 ACL；换 `--tsmp`
   也一样。要验 ACL 得看 PacketFilter 或真跑业务流量。
3. **验 `group:admin` 是否解析正确**：用管理员预授权密钥建 `ad-exit`（广告
   `0.0.0.0/0`）。建密钥时 `headscale preauthkeys create -u` 要**数字 id**
   （`headscale users list -o json` 里取），传用户名会报
   `strconv.ParseUint: parsing "tenant-a": invalid syntax`。

### 同前缀可见性泄漏（2026-10-05 已修）

曾有的缺陷：两个用户的路由节点广告**同一个网段**时，对方的路由器节点会出现在
自己的 peers 列表里。机制在 `hscontrol/types/node.go` 的 `canAccess`：判据是
`m.DestsOverlapsPrefixes(dstRoutes...)` —— **前缀重叠**，不是前缀归属，由
`hscontrol/policy/v2/policy.go` 的 `BuildPeerMap` 调用。只是可见性泄漏，节点间
流量仍被 PacketFilter 挡着。

**已修**：`ac68ca60 policy: keep a foreign scope's routes out of peer visibility`
把 peer 的路由按「双方是否共享 route scope」做了门控。只动 per-node 路径
（`autogroup:self` / grants），纯全局策略仍走快路径；同一用户的 router/HA 配对不受影响。

验证方法（可复现）：

```bash
# 每个客户端的 peers 里只应出现自己用户
ssh root@<测试节点> 'for n in mt-a-client mt-b-client; do echo "== $n"; \
  tailscale --socket=/tmp/$n/tailscaled.sock status | grep -v "^#"; done

# 合法路径没被修坏：本用户路由器仍持有该网段
tailscale --socket=/tmp/mt-a-client/tailscaled.sock status --json | \
  python3 -c 'import json,sys; [print(v["HostName"], v["AllowedIPs"]) for v in json.load(sys.stdin)["Peer"].values()]'
```

**对照实验是必要的**：把旧二进制换回去泄漏立刻复现，换回来又消失 —— 否则分不清是
修复生效还是节点重连把状态冲干净了。换二进制的顺序见
[headscale-hot-swap-deploy-gotchas.md](headscale-hot-swap-deploy-gotchas.md)。

## 六、坑

- `headscale ... -o json` 的键是 **snake_case**（`given_name`、`available_routes`），
  不是面板 API 的 camelCase。
- 改 `--advertise-routes` 重跑 `tailscale up` 时必须同时带 `--accept-routes`，
  否则退出码 1 抱怨「非默认设置」。
- `/api/system/info` 和 `/api/system/data_usage` 返回**裸 JSON**（不套 `res()`），
  断言 `code == "0"` 会失败 —— 设计如此，不是缺陷。
- 断言配置项时注意 `save_config_yaml` 用了 `yaml.preserve_quotes`，写回去的
  数字可能是带引号的 `'7'`。
- 面板改完代码要 `docker restart hs-admin` 才生效（waitress 没有 reloader），
  但这一下会连带重启 headscale，测试节点要重连。
- **日志里两类噪声别当故障追**：
  - `noise handshake failed ... chacha20poly1305: message authentication failed`，
    每 30 秒一条、来自测试节点 —— 是那台机器上的**系统 tailscaled**
    （`/var/lib/tailscale/tailscaled.state`，不是那 6 个 `/tmp/mt-*` 测试节点），
    它 `Logged out` 但 `ControlURL` 指着测试 headscale，卡在「注册了但没认证」的
    循环里。`headscale nodes list -o json` 里 6 个测试节点全 `online=true` 就与它无关。
  - `HA probe: node did not respond node.id=N` —— userspace-networking 下探针答不上来。
    选举按 `TypedUserID()` 分 scope（`electPrimaryRoutes`），a-router/b-router 分属
    tenant-a/tenant-b，**不是跨用户配对**，各自是自己 scope 的主路由器所以都会被探。
    全部候选不健康时会保留原主，路由因此不会掉 —— 看 `AllowedIPs` 还在就没事。

## 七、这一轮的结论

- 生产数据升级：11 张表行数一致、`integrity_check` 正常、无迁移报错。
- 全新 Docker 安装：`init.sh` 各条路径均执行。
- 注册/登录 12/12；页面+只读接口 20/22（2 项为上面说的裸 JSON）；写操作 20/20；
  修复回归 8/8；路由单测 11/11。
- 修复的缺陷：`approve_routes` 缺归属校验（跨用户提权，已实证）、`node_route_info`
  缺归属校验、管理员 `route=0` 时提示误导、`delKey` 绕过 API、`DEFAULT_ACL`
  与 `init.sh` 出厂 ACL 不一致。
- 同前缀可见性泄漏（缺陷 4）：headscale 侧 `ac68ca60` 修复，已用**回滚对照实验**
  验证 —— 旧二进制泄漏复现、新二进制干净，且同一用户 HA 配对与合法路由均未受影响。
