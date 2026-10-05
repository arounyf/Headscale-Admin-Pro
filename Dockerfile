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

# 参数与 headscale/.github/workflows/build-runyf.yml 里原来的发布构建一致。
# 那个 workflow 在面板仓库里是失效的（GitHub 只读仓库根目录的
# .github/workflows/），留着只是为了以后 subtree pull 上游时不冲突。
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /headscale ./cmd/headscale

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
