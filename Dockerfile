# 第一阶段：构建阶段
FROM ubuntu:22.04 AS builder

# 创建一个工作目录
WORKDIR /init_data

# 更新包管理器并安装必要的工具
RUN apt-get update && \
    apt-get install pip wget -y && \
    pip3 install flask sqlalchemy flask_sqlalchemy wtforms captcha flask_migrate psutil flask_login requests apscheduler ruamel.yaml email_validator && \
    wget -O headscale https://github.com/juanfont/headscale/releases/download/v0.25.1/headscale_0.25.1_linux_amd64 

# 将当前目录下的内容复制到工作目录中
COPY . /init_data
RUN mv data-example.json data.json && \
    mv config-example.yaml config.yaml && \
    mv derp-example.yaml derp.yaml && \
    chmod u+x init.sh

# 第二阶段：运行阶段
FROM ubuntu:22.04

# 创建一个工作目录
WORKDIR /init_data

# 安装运行时依赖
RUN apt-get update && \
    apt-get install  tzdata net-tools iputils-ping python3  iproute2 -y && \
    apt-get clean

# 从构建阶段复制必要的文件
COPY --from=builder /init_data /init_data
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

CMD ["sh", "-c", "./init.sh 'python3 app.py'"]
    