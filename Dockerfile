# 第一阶段：构建 headscale 二进制
#
# 源码是仓库里的 headscale/ 子树，不再从 GitHub Release 下载。这样镜像里的
# headscale 和面板代码永远出自同一个 commit —— 以前那个 pin 的 URL 一旦忘了
# 跟着改，面板发了新的 CreateUserRequest 字段而二进制还是旧的，注册接口就会
# 直接 400，而且报的是 protojson 的 unknown field，看不出是版本没对齐。
#
# 这棵子树怎么来的、上游怎么同步，见 headscale/MERGING-UPSTREAM.md。
FROM golang:1.26.5 AS hs-builder

WORKDIR /src

# 先只拷依赖清单：Go 模块层和源码层分开缓存，改面板代码不会让这一层失效。
# 镜像 tag 与 go.mod 的 go 指令同为 1.26.5，构建时不需要再联网取工具链。
COPY headscale/go.mod headscale/go.sum ./
RUN go mod download

COPY headscale/ ./

# 这一层只为把 GOCACHE 填满，产出丢进 /dev/null。它**必须待在下面那两行 ARG 之前**，
# 因为 BuildKit 会把 ARG 的值算进 RUN 那层的缓存键 —— HS_BUILD_TIME 每次 CI 都不一样，
# 带 stamp 的那次编译因此永远命不中缓存。实测（2026-10-05）：源码一个字不动、只把
# HS_BUILD_TIME 挪一秒，上面 `COPY headscale/` 是 CACHED，带 -ldflags 的那次照样
# 重编 44.7s。
#
# 有了这一层，链接那次拿到的是内容寻址的编译缓存：-ldflags 只影响链接，包编译与它
# 无关。实测 headscale 源码没改时，带 stamp 的那次从 44.7s 降到 2.4s，产物 sha256
# 与不加这一步逐字节相同；源码改了也只是多这一次暖层（~45s），总代价 +3s 左右。
#
# CGO_ENABLED 必须和下面那次显式一致：编译缓存的键含编译环境，不一致就全落空，
# 变成白编一遍。
RUN CGO_ENABLED=0 go build -o /dev/null ./cmd/headscale

# 二进制要报的 commit 和 build time。CI（.github/workflows/main.yml）从
# github.sha 和构建那一刻取；直接 docker build 不传就是 unknown —— 构建上下文
# 里没有 .git，没得可查，unknown 是诚实的答案。
ARG HS_COMMIT=unknown
ARG HS_BUILD_TIME=unknown

# 参数 -s -w 与 headscale/.github/workflows/build-runyf.yml 里原来的发布构建一致。
# 那个 workflow 在面板仓库里是失效的（GitHub 只读仓库根目录的
# .github/workflows/），留着只是为了以后 subtree pull 上游时不冲突。
#
# 版本号继承上游：CHANGELOG.md 顶部那个 `## x.y.z` 就是上游最新一次发布，
# `git subtree pull` 之后它自动就是对的，没有需要手工维护的版本号。后面缀
# `-hs`：这棵树里的 headscale 是改过的（多用户路由隔离、users 表扩展列等），
# 面板一直用 `vX.Y.Z-hs` 把这个先后关系标出来。

# 这三个值非用 -ldflags 打进去不可：构建上下文里没有 .git（.dockerignore 排掉了），
# Go 的 VCS stamping 什么都拿不到，ReadBuildInfo 只报 (devel)，二进制于是
# 自称 dev、commit 和 build time 都是 unknown，而 headscale 对 dev 是跳过数据库
# 版本校验的 —— 那道校验会一直睡着。
#
# 末尾三行 grep 是自检。链接器对打不中的 -X 是静默忽略的（headscale 的
# Makefile:45 就有一个这样的死参数），不验一下就会悄悄退回「镜像里的二进制
# 自称 dev」。用 -x 而不是 -q，免得 commit 那种短值匹配到别的行上去。
RUN VERSION=$(sed -nE 's/^## ([0-9]+\.[0-9]+\.[0-9]+).*/\1/p' CHANGELOG.md | head -1) \
    && test -n "$VERSION" \
    && test -n "$HS_COMMIT" \
    && test -n "$HS_BUILD_TIME" \
    && PKG=github.com/juanfont/headscale/hscontrol/types \
    && HS_VERSION="v$VERSION-hs" \
    && echo "headscale $HS_VERSION, commit $HS_COMMIT, built $HS_BUILD_TIME" \
    && CGO_ENABLED=0 go build \
        -ldflags="-s -w -X $PKG.Version=$HS_VERSION -X $PKG.Commit=$HS_COMMIT -X $PKG.BuildTime=$HS_BUILD_TIME" \
        -o /headscale ./cmd/headscale \
    && /headscale version > /tmp/stamp \
    && grep -qx "headscale version $HS_VERSION" /tmp/stamp \
    && grep -qx "commit: $HS_COMMIT" /tmp/stamp \
    && grep -qx "build time: $HS_BUILD_TIME" /tmp/stamp

# 只用来把上面那个二进制原样取出来的空壳阶段，CI 挂在 Release 上：
#
#   docker buildx build --target hs-binary --output type=local,dest=dist .
#
# 走这条路而不是在 workflow 里另写一段 go build，是为了让「版本号怎么取、
# -ldflags 怎么拼」只有这一处定义 —— 发到 Release 上的 headscale 和镜像里跑的
# 那个必然是同一次构建。scratch 阶段里只有这一个文件，所以 type=local 导出的
# 就是它一个，不会把整个 golang 基础镜像的文件系统拖出来。
#
# **这一段必须留在最终的面板镜像阶段之前**：Dockerfile 的最后一个 FROM 就是
# 默认构建目标，挪到文件末尾会让不带 --target 的 `docker build` 转去构建它。
#
# 导出的是 runner 的架构（CI 上是 linux/amd64），和镜像一致 —— 镜像本身也没做
# 多架构。真要出多架构镜像时，这里得跟着改成每个平台各导一份。
FROM scratch AS hs-binary
COPY --from=hs-builder /headscale /headscale

# 第二阶段：构建阶段
FROM ubuntu:24.04 AS builder

# 工作目录
WORKDIR /init_data

# 安装系统依赖（Ubuntu 24.04 自带 Python 3.12）
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip3 install --break-system-packages \
    flask \
    flask-wtf \
    wtforms \
    captcha \
    psutil \
    flask_login \
    requests \
    apscheduler \
    ruamel.yaml \
    email_validator \
    waitress

# 复制项目并初始化配置
COPY . /init_data
# 删掉 COPY 进来的 headscale/ 源码目录：它只在上面那个阶段有用，留下会被
# init.sh 的 cp -r 带进 /app，也会顺带把源码暴露给运行时。
RUN rm -rf /init_data/headscale && \
    mv data-example.json data.json && \
    mv config-example.yaml config.yaml && \
    mv derp-example.yaml derp.yaml && \
    sed -i 's/\r$//' init.sh && \
    chmod u+x init.sh

# 二进制放在 /init_data/headscale（而不是 /usr/bin）：init.sh 会把 /init_data/*
# 拷进 /app，再 `cp headscale /usr/bin`。保持这个位置，init.sh 一行都不用改，
# 12 和生产上「把新二进制 scp 到 /app/headscale 再重启」的升级方式也原样可用。
# 必须放在上面 rm -rf 之后，否则会和同名的源码目录撞上。
COPY --from=hs-builder /headscale /init_data/headscale

# 第三阶段：运行阶段
FROM ubuntu:24.04

# 工作目录
WORKDIR /init_data

# 安装运行时依赖（自带 Python3.12）
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        ca-certificates \
        tzdata \
        net-tools \
        iputils-ping \
        iproute2 \
        python3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段复制文件
COPY --from=builder /init_data /init_data
COPY --from=builder /usr/local/lib/python3.12/dist-packages /usr/local/lib/python3.12/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

ENV PYTHONUNBUFFERED=1

# 启动
CMD ["sh", "-c", "./init.sh 'python3 app.py'"]
