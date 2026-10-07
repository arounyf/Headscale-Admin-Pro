# 修掉两个红测试包 + 打通「官方 0.29.x 直切 fork」+ release 正文入库

## Context

上次发布前跑全量测试，23 个包里 21 绿 2 红（`hscontrol/derp`、`hscontrol/db`）。
当时已在 `ff5a894a` 上用 worktree 复现，确认都是既有问题，不是本次改动引入的。
用户决定「两个都修」。

查下来 `hscontrol/db` 的红不是测试写坏了，是**升级路径上的真 bug**：
`squibble.Validate`（`hscontrol/db/db.go:1013-1051`）在**每次 SQLite 启动**时都跑
（不是测试专用），schema 对不上就是 `validating schema: ...` 直接起不来。

根因是一条被 fork **回头改过**的已发布迁移 `202507021200`（v0.27.0 的 schema 重建）：

| | `tablesToRename` | 新 `users` DDL | `users` copy | acl/log copy |
|---|---|---|---|---|
| upstream/main | 5 张表 | 上游 10 列 | 上游 10 列 | 无 |
| 本仓库 | +`acl` `log` | +7 个 hs-admin 列 | +7 列 | 有（`db.go:429-434`）|

迁移记录只存 ID，不存「当时跑的是哪版 SQL」。于是库在野分成两半，
**取决于 `202507021200` 是否已被登记**（`migrations` slice 按顺序走，
`runMigrations` 只对 7 个 legacy ID 有特殊处理，`db.go:1191-1205`）：

**A. 已登记（官方 0.27 及以后建的库 —— 含本 fork 对应的上游 v0.29.4）**
fork 版 SQL 被跳过 → 7 列从没加上 → `squibble.Validate` 报 `+ add column ...` → **起不来**。
对应 5 个 fork fixture：`request_tags_*` / `null_tags_*` / `recover_null_tags_*` /
`zero_time_expiry_*` / `clear_tagged_node_expiry_*`。
**这就是「官方 0.29.x 直切过来」，也是用户希望打通的那条路。**

**B. 未登记（官方 0.26.x 建的库）**
fork 版真跑 → copy 引用 `users_old.password` 不存在 → `copying data: no such column: password`
→ **起不来**。对应 7 个上游 dump（`headscale_0.26.*`、`failing-node-preauth-*`、
`*-old-table-cleanup`）。**这条路按用户的支持策略不在范围内。**

**12 个 fixture 全查过**：`users` 都是上游 10 列、都没有 `acl`/`log` 表；
5 个登记了 `202507021200`、7 个没登记 —— 与上面两半严格对应。

**用户的数据库改动全部是追加式的**（只 `ADD COLUMN` / `CREATE TABLE`，不删不改名），
所以 A 可以用纯追加的迁移补齐；B 则必须改老迁移 body，与 AGENTS.md
「只能追加到末尾」正面冲突 —— 因此本次**明确不支持 B**，把 7 个 dump 划出测试集。

支持的升级路径（本次要保证全绿）：**全新安装**、**上一个 fork 版本 → 本版本**、
**官方 0.29.x → 本 fork**。

---

## 改动 1：`hscontrol/db/db.go` —— 追加一条补列迁移

追加到 `migrations` 数组**末尾**（`202607241200-clear-tagged-node-expiry`，`db.go:830` 之后），
ID 按 `YYYYMMDDHHMM-short-description` 格式：`202609261200-add-users-custom-columns`。

内容：幂等地把缺的列 `ALTER TABLE users ADD COLUMN` 上去 —— **直接复用**
`InitSchema` 里那段现成写法（`db.go:862-906`：`PRAGMA table_info(users)` → 比对 →
逐个 `ALTER`）。守卫照抄 `202507021200` 的
`if cfg.Database.Type != types.DatabaseSqlite { return nil }`（`db.go:249-253`）。

为什么放末尾就够：A 类库里 `202507021200` 已登记、永不重跑，这条迁移的位置与它无关；
对已达标的库（全新安装、上一个 fork 版本）它是幂等 no-op。

顺手把 `InitSchema` 里的局部 `customFields` 提成包级变量，让「7 列是哪 7 列」
只有一处定义。**这次 bug 的本质就是同一份 DDL 在三个地方各写一份然后漂移**
（`schema.sql:20-27`、`202507021200` 的 DDL、`InitSchema` 的 `customFields`），
所以这里做去重是有针对性的，不是「以防万一」的抽象。

**不建 `acl`/`log`**：`squibble.Validate` 的 `IgnoreTables` 里本来就有它们
（`db.go:1037-1039`），缺表不会导致启动失败；`alembic_version` 同在忽略列表里，
说明这两张表归面板的 Alembic 管，headscale 不该替它建。

---

## 改动 2：把 7 个 0.26.x dump 划出「必须通过」的测试集

`hscontrol/db/testdata/sqlite/` 的 12 个 fixture 里，7 个是 pre-0.27 形状
（`headscale_0.26.0-beta.1/beta.2/0.26.0/0.26.1/0.26.1-litestream/0.26.1-*-old-table-cleanup`,
`failing-node-preauth-constraint_dump`）。按用户的支持策略，官方 0.26 直切不支持，
所以它们不该出现在断言「迁移必须成功」的集合里。

做法：

1. 移到 `hscontrol/db/testdata/sqlite/upstream-pre-0.27/`，并加一个短 `README.md`
   写明：为什么停在这、卡在哪（`202507021200` 的 copy）、
   以及若要支持需要动什么（改那条迁移的 body）。**不删**——它们是真实 dump，
   是这次问题的证据，将来要支持 0.26 时直接搬回来。
2. `db_test.go:31` 那条 `failing-node-preauth-constraint_dump.sql` 从
   `TestSQLiteMigrationAndDataValidation` 的 6 条手写用例里删掉。
3. `TestSQLiteAllTestdataMigrations`（`db_test.go:610-613`）已经 `schema.IsDir() → continue`，
   子目录天然被跳过，测试代码不用改。

剩下 5 个 fork fixture + 其余留在原地的，正好由改动 1 修好。

---

## 改动 3：`hscontrol/derp` —— 让测试自洽

`hscontrol/derp/derp_bug_test.go` 全文只有一个测试，却依赖两个外部条件：

- `controlplane.tailscale.com` 的真实网络（要拿到 `nyc` region）
- `/tmp/test-derp.yaml` 这个**没有任何代码会创建**的文件

而 `GetDERPMap`（`hscontrol/derp/derp.go:129`）先处理 URL、后处理 Path，
两边都不做 fallback，任一失败直接返回错误。

改法：两个条件都改成测试内自建。

- URL 侧用 `httptest.NewServer` 返回一份最小 DERP JSON
  （`loadDERPMapFromURL` 走 `json.Unmarshal` 到 `tailcfg.DERPMap`，
  只要一个 `RegionCode: "nyc"` 的 region）。
- Path 侧用 `t.TempDir()` + `os.WriteFile(..., 0o600)`，内容按 `derp-example.yaml`
  的形状写 `regions: {900: {regioncode: test-derp}}`
  （`loadDERPMapFromPath` 用 yaml.v3 解析，结构体没有 yaml tag，键名取小写）。
  这个 idiom 仓库里已有：`hscontrol/types/config_test.go:355-373`。

断言不变：两个 region 都在、且合并在同一个 map 里 —— 这才是测试名
`TestGetDERPMap_BothURLAndPath` 真正要验的东西。

---

## 改动 4：把 release 正文落进仓库

现在正文是发布后手工 `gh release edit --notes-file` 补的，因为
`.github/workflows/build-runyf.yml:52-65` 的 `Generate release notes` 无条件用
`git log` 覆写 `/tmp/notes.md`，而 `body_path` 指的就是它（`:72`）。

- 新建 `.github/release-notes/v0.29.4-hs.md`，内容就是这次已经上线的那份正文
  （现在在 `/tmp/release-notes.md`，2465 字节）。
- 改 `Generate release notes` 这一步：先看
  `.github/release-notes/${GITHUB_REF_NAME}.md` 在不在，在就直接 `cp` 到 `/tmp/notes.md`，
  不在才走原来的 `git log` 分支。`body_path` 不动。

以后发版变成「先写这个 md 再打 tag」，正文进版本历史、可 review、可 diff。

---

## 验证

**1. 单包** —— 目标是把 2 红变 0 红：

```bash
go test ./hscontrol/derp/... -run TestGetDERPMap_BothURLAndPath -v
go test ./hscontrol/db/... -run 'TestSQLite' -v
```

`hscontrol/db` 要看到留下的 fixture 在两个测试函数里**全部**通过。
重点确认这几条：
- 5 个 fork fixture 从 `validating schema` 转绿（改动 1 生效）。
- `request_tags_migration_test.sql`（`db_test.go:81`）等手写用例的 `wantFunc`
  仍断言数据保真 —— 补列迁移**不能动任何既有数据**，这是回归重点。
- 7 个挪走的 dump 不再被扫到，`TestSQLiteAllTestdataMigrations` 不报文件缺失。

**2. 真升级路径（改动 1 的正主，必须做）**：
单元测试之外，还要真起一次进程 —— 因为 `squibble.Validate` 是**启动路径**上的，
`NewHeadscaleDatabase` 通过不代表 `headscale serve` 能起来。

拿一个官方 0.29.x 形状的库（就用留下的 5 个 fork fixture 之一，
它们是 10 列 + 已登记 `202507021200` 的真实形状）复制成 `db.sqlite`，
按 AGENTS.md 的部署方式在 测试机上换二进制后启动，确认：
headscale 起得来、`PRAGMA table_info(users)` 里 7 列齐了、
`sqlite3 db.sqlite 'select count(*) from users/nodes/api_keys'` 与迁移前一致。

**3. 全量**：`make fmt && make lint && go test ./...`，再跑一遍 `hscontrol/servertest`
（上次 452s，确认没被 db 改动影响）。

**4. 部署回归（按 AGENTS.md 的部署规矩，不重建容器）**：
测试机上热替换 `/app/headscale`（`docker exec hs-admin cp` + `pkill headscale`），
确认 5 个节点仍在线、面板 ACL 保存仍通（`/etc/headscale/acl.hujson`
md5 应仍是 `258c88c0b29b8b57e37c2ba7a34c06cf`，被测试改过要还原）。

**5. release 正文（改动 4）**：离线核对 tag 名对应的 md 存在、`cp` 分支生效；
真验证留到下次发版。

---

## 不做 / 风险

- **不支持官方 0.26.x → fork**（改动 2）。要支持只能改 `202507021200` 的 body，
  而那与 AGENTS.md「只追加到末尾」冲突，且用户的支持策略本就不含它。
- **不改 `hscontrol/types/users.go` 的 `types.User`**：那 7 列 Go 侧不读不写，
  补进模型会牵动 `AutoMigrate` 行为，超出范围。7 列只作为裸 SQL 存在。
- **Postgres 上的 7 列仍不会补**：`squibble.Validate` 只在 SQLite 跑，
  Postgres 缺这几列不会导致启动失败，是现状，本次不改变
  （`ALTER TABLE ADD COLUMN IF NOT EXISTS` 在 Postgres 有、SQLite 没有，
  两边通用要多写一套 `information_schema` 查询，收益不成比例）。
- **挪 fixture 是「降低覆盖」**，不是「修好」——所以配 README 留证据，
  而不是静默删掉。
