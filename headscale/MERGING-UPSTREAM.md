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

`git subtree` 靠 DAG 找 merge base（当前是 `b0c221f3`）。如果 headscale 那一侧
重写过历史（`arounyf/headscale` 上就有 `backup/pre-msg-rewrite`、
`backup/pre-rebase-20260409` 这类标签），共同祖先可能悄悄移位。

症状是：`git subtree pull` 产生大批牵涉到你根本没改过的文件的冲突。此时先核对

```sh
git merge-base hs-admin upstream/main     # 在 arounyf/headscale 那份检出里跑
```

是不是还指向一个合理的提交，再决定是否用 `git subtree pull` 的 `<onto>` 参数
显式指定基线。

## 改 headscale 代码

直接在 `headscale/` 里改，正常提交。两点注意：

- `headscale/` 自带 `.gitignore`，在里面 `make build` 产生的二进制不会被本仓库
  跟踪，不需要额外加规则。
- `headscale/.github/workflows/` 是**失效的** —— GitHub 只读仓库根目录下的
  `.github/workflows/`。那些工作流（包括原来负责发版的 `build-runyf.yml`）作为
  历史保留，删掉会让以后每次 subtree pull 都冲突，但它们不会运行。本仓库的
  `.github/workflows/main.yml` 才是实际生效的那一个。

## 发布

本仓库只有一条版本线：面板的 `v5.x`。镜像里内置的 headscale 版本就是那个 tag
对应的源码版本，不再单独给 headscale 打 tag。

`arounyf/headscale` 冻结：作为上游中转和历史归档保留。它的 `v0.29.4-hs` release
资产原地不动，还在引用那个下载 URL 的旧文档不会 404；但新的二进制不再从那里发布。
