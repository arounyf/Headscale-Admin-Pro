# 上线流程

用户口述的规则，生产机和测试机通用。**核心：把所有耗时动作挪到停机窗口之外。**

| 机器 | 角色 |
|---|---|
| 生产机 | **生产**（公网，腾讯云） |
| 测试机 | 容器 `hs-admin` |
| 测试节点 | tailscale 测试节点（当客户端用） |

> 动手前先看「落地」—— 两台机器有几处不一样，别照抄。跨 headscale 版本升级先做「演练」。

## 顺序

1. **拉要上线的版本** —— 服务仍在跑
2. **备份数据**（含 `app/`）—— 服务仍在跑
3. **停止容器 + 清 `/app`**
4. **启动容器**（用新版本，`init.sh` 会把 `/app` 重新灌一遍）

## 为什么是这个顺序

和面板 README「如何升级」那套的区别就在这里 —— 那套是 `docker-compose down` 打头，之后才备份：

| | README 那套 | 本流程 |
|---|---|---|
| 停机窗口内包含 | 备份 + 删代码 + 删容器 + 删镜像 + **拉新镜像** + 起容器 | 只有 停 + 起 |
| 业务中断 | 分钟级 | 秒级 |

`docker pull` 一个 300MB 的镜像是全流程最慢的一步，它必须发生在停机之前。同理，备份 `data/` 也在停机前做完。

**判据：任何一步的耗时不由「服务是否在跑」决定，就该提到停机之前。**

## 落地

两台机器布局几乎一样，**但有四处不同，别照抄**：

| | 生产机 | 测试机 |
|---|---|---|
| compose 文件 | `docker-compose.yaml` | `docker-compose.yml` |
| `/app` 隐藏项 | **无** | 有 `.git`、`.claude` 等，清理必须带 `.[!.]*` |
| `FLASK_DEBUG` | `False` | `True` |
| 同机其它服务 | **有**（nginx + 若干自建服务，清单见本地记忆库）→ 停机窗口里别碰别的容器 | 无 |

挂载（两台相同，生产 compose 里写成 `~`）：

```
~/hs-admin/app    -> /app                 面板代码 + headscale 二进制
~/hs-admin/config -> /etc/headscale       headscale 配置 + acl.hujson
~/hs-admin/data   -> /var/lib/headscale   db.sqlite + headscale.log
```

端口归属两台一致：**8080 = headscale，5000 = 面板**。生产前面还有 nginx 占 80/443。

生产补充事实（2026-09-28 实测）：

- 主机 `<生产主机名>`，腾讯云，公网入口 `https://<生产域名>`（nginx 反代面板）
- 规模 123 节点 / 99 用户；`data/` 约 1GB，其中 **`headscale.log` 占 1003M**，`db.sqlite` 只有 ~450K
- 备份命名习惯 `data.bak.YYYYMMDD_HHMM`（已有 7/07、7/09、7/30 几份）
- 磁盘 40G、升级时约剩 17G，够放一份 data 备份
- `docker compose` v2.38.2；`docker-compose` 老命令也在
- **停机窗口里别碰同机其它容器** —— 这台机器跑着一堆别的服务

### 跨 headscale 版本：先用真库副本演练

面板版本沿 headscale 版本走（v5.x ↔ v0.29.x-hs），所以升级面板常常连带升级 headscale，
**会在真库上跑 schema 迁移**。生产库上失败代价很大，先拿副本在测试机验：

```bash
# 1) 生产上做一致性快照（只读，不锁库）
python3 -c "
import sqlite3
s=sqlite3.connect('file:/root/hs-admin/data/db.sqlite?mode=ro', uri=True)
d=sqlite3.connect('/tmp/prod-snap/db.sqlite'); s.backup(d)"

# 2) 连同基线一起带走：各表行数、PRAGMA table_info(users) 列名、migrations 条数与末条

# 3) 传到测试机，用**新镜像里的 headscale** 对着副本跑一次 serve
#    最小配置的坑：dns.magic_dns / dns.override_local_dns 不配会 FTL 退出；
#    derp 全关且无 urls/paths 会报 "initial DERPMap is empty" 起不来 —— 给个本地 paths 文件即可

# 4) 起来后逐表比对副本与迁移后的库，确认只有 migrations 和 database_versions 变了
```

2026-09-28 用这套验 `v0.29.3-hs → v0.29.4-hs`：9 张表逐行一致，只多一条
`202609261200-add-users-custom-columns`，`users` 列数与索引数不变。

### 停机前（服务照常跑）

```bash
cd /root/hs-admin

# 1) 拉版本
docker pull runyf/hs-admin:<要上线的 tag>

# 2) 备份数据
#    data 必需；config 里有 ACL；app 也必须备 —— 窗口里会清空它，
#    它是回滚面板代码和旧二进制的唯一凭据
TS=$(date +%Y%m%d_%H%M)
cp -r data   data.bak.$TS
cp -r config config.bak.$TS
cp -r app    app.bak.$TS

# 3) 顺手确认新镜像里的 headscale 是不是预期的版本
CID=$(docker create runyf/hs-admin:<tag>)
docker cp "$CID":/init_data/headscale /tmp/hs-new && docker rm "$CID"
chmod +x /tmp/hs-new && /tmp/hs-new version
```

### 停机窗口内（越短越好）

```bash
docker rm -f hs-admin                 # 停掉并删除旧容器
find app -mindepth 1 -delete          # 清空 /app（必需，见下）
docker compose up -d                  # 按 compose 里的 tag 起新容器；init.sh 会重新灌 /app
```

> `docker-compose.yml` 里的 `image:` 必须已经是新 tag —— 这一步提前改好，别留在停机窗口里做。

**「清 `/app`」不是可选项 —— 漏了整次升级就是白升，而且不报错。**

`init.sh` 只在 `/app` 为空时才从镜像灌东西：面板代码走 `cp -r /init_data/* /app`，
headscale 二进制走第 78 行 —— `cd /app` 之后 `cp headscale /usr/bin`。
也就是说**运行时真正生效的二进制是 bind mount 里的 `/app/headscale`，不是镜像里那份**。
`/app` 非空 → 两步全跳过 → 容器起来了、验证命令全绿、版本一个字节没变。

2026-10-05 上线前实测：生产 `/app/headscale` 与 `/usr/bin/headscale` 是同一个旧 md5
（`55091256…`），镜像里那份是新的（`a8e51909…`）—— 不清 `/app`，`up -d` 起来的就是旧版本。

用 `find app -mindepth 1 -delete`，别用发布说明里的 `rm -rf app/*`：后者不匹配隐藏项。
生产 `/app` 目前没有隐藏项，两者等价；测试机上有 `.git`/`.claude`/`.github`，
`rm -rf app/*` 清不干净会让 init.sh 照样判定「已有数据」，见下面「坑」。

### 起来之后必须验证

**先记住两个端口各归谁**（2026-09-27 实测确认）：

| 端口 | 进程 | 说明 |
|---|---|---|
| `8080` | `headscale` | 控制面。`/health` 200 **只证明 headscale 活着** |
| `5000` | `python3 app.py` | 面板本身。静态资源、登录页都在这 |

`ss -ltnp | grep -E ':(5000|8080)'` 可以随时确认。

```bash
# headscale 侧 —— 8080
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/health   # 期望 200
docker exec hs-admin headscale version                                   # 期望的 commit
docker exec hs-admin md5sum /usr/bin/headscale /app/headscale            # 两处一致

# 面板侧 —— 5000（8080 测不出面板，别漏）
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/static/index.js   # 期望 200
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/login             # 期望 200
docker logs hs-admin 2>&1 | grep -icE 'traceback|error'                          # 期望 0

# 其它
md5sum /root/hs-admin/config/acl.hujson                                  # 没被碰过
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
```

节点是否回连，用 `headscale nodes list -o json` 看 `online` 字段（snake_case：`given_name` / `last_seen`）。
**注意时序**：容器刚起来那几秒查，`online` 会全是 `None`（字段还没出现）—— 实测节点 7 秒后才回连，等 10 秒再查。

面板登录**没法脚本验**：登录表单要 `vercode` 验证码，脚本 POST 必定 400（这是预期，不是故障）。所以面板侧以上面「静态资源 200 + 日志无 traceback」为准，登录留给人手动点一下。

## 坑

- **清 `/app` 是停机窗口的必需步骤，不是可选项**（命令见上面「停机窗口内」）。`init.sh` 判空用的是 `ls -A /app`（**含隐藏项**），所以 `rm -rf app/*` 在 测试机上清不干净 —— 目录仍非空 → init.sh 判定「已有数据」**跳过重灌**；生产上更隐蔽：`rm -rf app/*` 能清干净，但**一旦漏掉这一步，服务照样正常起来、验证命令全绿、版本纹丝不动**，没有任何报错。统一用 `find app -mindepth 1 -delete`。
  测试机上先备份 `.git`（那是个 git 工作副本）；生产 `/app` 没有隐藏项。
- **`docker-compose.yml` 的 tag**：12 上写的是 `runyf/hs-admin:v6.0-beta.5`，这个 tag **Docker Hub 上不存在**，是本地构建的。别以为 compose 里的 tag 就是线上发布的 tag。
- 停机时 headscale 收 SIGTERM 优雅退出，已连节点会断开并在新进程起来后自动重连（实测 `/health` 3 秒回 200）。

相关：[[headscale-hot-swap-deploy-gotchas]]、[[admin-pro-frontend-hot-reload]]
