# 第一阶段：构建阶段
FROM ubuntu:24.04 AS builder

# 工作目录
WORKDIR /init_data

# 安装系统依赖（Ubuntu 24.04 自带 Python 3.12）
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        python3-pip \
        wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip3 install --break-system-packages \
    flask \
    wtforms \
    captcha \
    psutil \
    flask_login \
    requests \
    apscheduler \
    ruamel.yaml \
    email_validator

# 下载 headscale
RUN wget -O headscale https://pan.runyf.cn/directlink/downloads/headscale/headscale-v0.28.0-runyf

# 复制项目并初始化配置
COPY . /init_data
RUN mv data-example.json data.json && \
    mv config-example.yaml config.yaml && \
    mv derp-example.yaml derp.yaml && \
    sed -i 's/\r$//' init.sh && \
    chmod u+x init.sh

# 第二阶段：运行阶段
FROM ubuntu:24.04

# 工作目录
WORKDIR /init_data

# 安装运行时依赖（自带 Python3.12）
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
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

# 启动
CMD ["sh", "-c", "./init.sh 'python3 app.py'"]