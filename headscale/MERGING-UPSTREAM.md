# 上游同步（headscale 子树）

这个目录是 headscale 的源码，以 `git subtree` 并入本仓库。它是镜像里 headscale
二进制的**唯一来源** —— `Dockerfile` 的 `hs-builder` 阶段直接从这里构建。

以前二进制是从一个写死的 release URL 下载的，面板代码和二进制之间没有任何机制
保证对齐：改了 proto 却忘了改那个 URL，面板发出去的字段就会让 headscale 报
`unknown field`，而错误发生在用户点「注册」的那一刻，报的还是 protojson 的解析
错误，看不出是版本没对上。源码在树里之后这类偏斜不可能发生。

## 这棵子树从哪来

`arounyf/headscale` 的 `hs-admin` 分支，加入时的提交是 `ec80ab63`。

它带着 fork 相对上游的全部改动（多用户路由隔离、`users` 表扩展列、
`autogroup:self` 缓存、policy file mode 等），也带着完整历史 —— `git log` 能一路
查到 2020 年的初始提交，`git blame` 在 `hscontrol/` 下可用。

## 同步上游

本仓库需要一个指向上游的 remote，加一次即可：

```sh
git remote add upstream https://github.com/juanfont/headscale.git
```

之后每次同步：

```sh
git subtree pull --prefix=headscale upstream main -m "headscale: merge upstream v0.30.0"
```

非 squash 模式下这就是一个带 `-Xsubtree` 的普通 merge，不做 split 重放，所以
不会因为树大而额外变慢。

### 一次同步大概是什么样子

实测（2026-10-05）：把 `upstream/main`（`53113e2a`，比 fork 领先 278 个提交）拉进来，
产生 **63 个冲突，全部落在 `headscale/` 下**；仓库根目录 `git status` 干净，`cmd/`、
`hscontrol/`、`go.mod`、`proto/` 都没有出现在根上。

63 个冲突听着吓人，但那是 278 个上游提交对一个分叉了 134 个提交的 fork 的正常代价，
**不是命令用错了**。冲突集中在 `hscontrol/types/`、`hscontrol/integration/` 和
`proto/headscale/v1/*.proto`。

### 不要做的事

**不要在本仓库里直接 `git merge upstream/main`。**

普通 merge 把两边都当根目录处理。实测下来它做三件错事：

1. **上游的 `cmd/`、`hscontrol/` 会被倒在仓库根**，和 `headscale/` 里那一份形成
   两份副本；
2. 根目录的 `.gitignore`、`README.md`、`config-example.yaml` 直接冲突；
3. 最阴的一点：git 的改名检测会把 `headscale/.github/workflows/lint.yml` 认成上游
   `.github/workflows/lint.yml` 的重命名，而上游删掉了后者 —— 于是它**提议删掉子树
   里的文件**（`headscale/.github/*`、`headscale/buf.gen.yaml` 等都会中招）。上游的
   改动一个字节都没进 `headscale/`，子树却先被咬了一口。

**只要没有推，退回去是干净的**：没有在合并中就把整个工作区还原到合并前。

```sh
git merge --abort            # 冲突还没解决时
git reset --hard HEAD^       # 万一把它提交了
```

### 一个需要留意的风险

`git subtree` 靠 DAG 找 merge base（当前是 `b0c221f3`）。这个 fork 重写过几次历史，
每一次重写都会让共同祖先悄悄移位。重写前的位置留在**本地那份 headscale 检出**的
`backup/pre-msg-rewrite-3169`、`backup/pre-rebase-20260409-092352` 这类标签上
—— 它们从来没推到 GitHub（`arounyf/headscale` 上只有 `v0.28.0` 和
`v0.29.0-hs`…`v0.29.4-hs` 这几个 release tag），所以只有那个 clone 还在的时候才查得到。

症状是：`git subtree pull` 产生大批牵涉到你根本没改过的文件的冲突。此时先核对

```sh
git merge-base hs-admin upstream/main     # 在本地那份 headscale 检出里跑
```

是不是还指向一个合理的提交，再决定是否用 `git subtree pull` 的 `<onto>` 参数
显式指定基线。

## 改 headscale 代码

直接在 `headscale/` 里改，正常提交。两点注意：

- `headscale/` 自带 `.gitignore`，在里面 `make build` 产生的二进制不会被本仓库
  跟踪，不需要额外加规则。
- `hscontrol/types/version.go` 是**故意**和上游不一样的地方之一（多了
  `Version`/`Commit`/`BuildTime` 三个变量，外加末尾读它们的十来行）。`git subtree pull`
  时它大概率会冲突，解决方式是两边的都要：上游的 `debug.ReadBuildInfo` 逻辑留着，
  注入那一段也留着，别为了消冲突把注入去掉 —— 去掉之后二进制又变回 `dev`，上面那节
  说的校验也就跟着失效了，而且不会有任何报错。
- **`hscontrol/state/state.go` 的 `setUserAdminFields` 里没有 `created_at`/`updated_at`
  两项，是故意的。** 上游将来可能往那儿加回 `if f.CreatedAt != ""` 之类的分支（写
  `users` 表扩展列的那个 patch 不是上游的，所以真冲突时会看起来像"上游的版本更全"）。
  冲突解决方向是**删掉**：那两个列归 GORM，写 caller 送来的字符串会让面板建的用户
  `created_at` 差一个时区，并顺着 `TailscaleUser().Created` 发给每个节点。
  `TestCreateUserWithAdminFields` 会挡住回归 —— 它送哨兵时间戳并断言进不去。
- `headscale/.github/workflows/` 是**失效的** —— GitHub 只读仓库根目录下的
  `.github/workflows/`。那些工作流（包括原来负责发版的 `build-runyf.yml`）作为
  历史保留，删掉会让以后每次 subtree pull 都冲突，但它们不会运行。本仓库的
  `.github/workflows/main.yml` 才是实际生效的那一个。

## 版本号

镜像里 headscale 的版本号**继承上游**，没有需要手工维护的数字：

`Dockerfile` 的 `hs-builder` 阶段从 `headscale/CHANGELOG.md` 顶部取那个 `## x.y.z`，
用 `-ldflags -X` 填进 `hscontrol/types/version.go` 的 `Version`。`git subtree pull`
把上游的 CHANGELOG 带进来之后，版本号自动就是对的（上游每次发版都改它，正常合并
总会带上）。`headscale/CHANGELOG.md` 被 `.dockerignore` 的 `headscale/**/*.md`
挡在构建上下文之外，所以那里专门给它开了一条 `!` 例外。

打进去的是 `vX.Y.Z-hs`。`-hs` 是面板一直用的标记，说明这棵树里的 headscale 是
改过的；`parseVersion` 在第一个 `-` 处截断，所以下一节那道校验读到的仍然是
`0.29.4`，后缀不影响版本门的判断。

同一处还打了 `Commit` 和 `BuildTime`，值由 `.github/workflows/main.yml` 的
build-args 传进来（`github.sha` 和构建那一刻的 UTC 时间）—— 上下文里没有 `.git`，
这两个值 Dockerfile 自己查不出来。直接 `docker build` 不传就是 `unknown`，那是诚实
的：本地裸构建确实没有一个 commit 可以标定它。所以同一个 commit 在本地构建和在镜像
里，`headscale version` 的输出会不一样，不是坏了。

之所以非注入不可：构建上下文里没有 `.git`（`.dockerignore:8` 排掉了），Go 的 VCS
stamping 什么都拿不到，`debug.ReadBuildInfo()` 只报 `(devel)`，二进制于是自称 `dev`、
commit 和 build time 都是 `unknown`。

三个值任一没取到（`CHANGELOG.md` 里那个数字缺失、build-arg 是空的），`test -n` 会让
构建直接失败。剩下的风险是 `-X` **打不中符号**：链接器对此是静默忽略的，`Makefile:45`
就有一个这样的死参数，实测把包路径打错一位，构建照样成功、二进制照样自称 `dev`。
所以构建末尾拿产物对了三行：

```sh
/headscale version > /tmp/stamp
grep -qx "headscale version v$VERSION" /tmp/stamp
grep -qx "commit: $HS_COMMIT"          /tmp/stamp
grep -qx "build time: $HS_BUILD_TIME"  /tmp/stamp
```

对不上镜像就出不来。**改 `version.go` 里那几个变量名或包路径时，这三行是唯一会
告诉你打歪了的东西** —— 去掉它们，失败会退回成「镜像里的二进制自称 dev」这个本来
要修的状态，而且没有任何报错。

### 这个数字会打开 headscale 的数据库版本校验

以前报 `dev` 时，`hscontrol/db/versioncheck.go` 的校验是**整段跳过**的。有真版本号
之后它会真的拦人。实测（`v0.29.4` 的二进制，逐条改库里的值重跑）：

| `database_versions` 里存的 | 结果 |
| --- | --- |
| 空 —— 这个特性之前的老库 | 放行，之后写入 `v0.29.4` |
| `dev` / Go 伪版本 —— 本地构建留下的 | 放行，之后写入 `v0.29.4` |
| 同一个 minor（`v0.29.0-hs`、`v0.29.4-hs`） | 放行，**并改写为 `v0.29.4`** |
| 低一个 minor（`v0.28.0`） | 放行，之后写入 `v0.29.4` |
| 低两个及以上 minor（`v0.27.0-hs`） | **拒绝启动** |
| 存的比当前高（`v0.30.0`） | **拒绝启动** |

注意放行那一列：**跑过一次之后，库里的基线就被改写成当前版本了**，此后的可升级
窗口由那个新值决定。

**所以每次 subtree pull 都要看一眼跨了几个 minor。** 从 `0.29.4` 直接并到 `0.31.0`
（跳过 `0.30`）会让镜像里的 headscale 起不来 —— 面板上表现为 headscale「已停止」，
而且**换回旧镜像也救不了**（旧镜像版本更低，同样被拒）。真跨了两个 minor，得先发一个
中间版本，让用户先升到 `0.30.x` 再升下一个。

对现存用户是安全的：这个 fork 发过的二进制带过的版本号最早是 `v0.28.0`，离 `0.29.4`
只差一个 minor；更早的版本根本没有这个特性，库里是空的。

## 发布

本仓库只有一条版本线：面板的 `v5.x`。镜像里内置的 headscale 版本号继承上游
（见上一节），不再单独给 headscale 打 tag。

面板的每个 Release 会附上镜像里那个 headscale 二进制，名字就叫 `headscale`，
下载路径 `releases/download/<tag>/headscale`。这是 `arounyf/headscale` 归档之后
补上的：以前那个路径是 `releases/download/v0.29.4-hs/headscale`，文档里引它的地方
现在会走到一个不再更新的仓库。

这份资产不是 workflow 里另写一段 `go build` 编出来的，而是从 `Dockerfile` 的
`hs-builder` 阶段直接导出（`--target hs-binary --output type=local`）——

```sh
docker buildx build --target hs-binary --output type=local,dest=dist .
```

——所以版本号取自 CHANGELOG、三个 `-ldflags -X`、末尾三行自检仍然只有一处定义，
发出去的二进制和镜像里跑的必然是同一个构建。改 `hs-builder` 那一段时，Release
资产会跟着一起变，不会有第二处需要同步的地方。

两个约束：`hs-binary` 那个 `FROM scratch` 阶段**必须留在面板镜像阶段之前**，
Dockerfile 的最后一个 `FROM` 才是默认构建目标；导出的是 runner 架构
（CI 上是 linux/amd64），镜像本身也没做多架构。

`arounyf/headscale` 已归档（GitHub 的 archive，只读），`hs-admin` 停在 `ec80ab63`
—— 与这棵子树加入时的内容一致。它的 `v0.29.4-hs` release 资产原地不动，还在引用
那个下载 URL 的旧文档不会 404（归档后实测该 URL 仍 302 到 CDN 并返回 200）；但新的
二进制不再从那里发布，要再往里推任何东西都得先解除归档。
