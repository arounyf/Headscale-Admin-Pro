FROM ubuntu:18.04

ENV BASE_PATH="/etc/s6-overlay/s6-rc.d" \
    S6_OVERLAY_VERSION="3.2.0.2"

COPY --chmod=755 ./rootfs /

ENV FLASK_APP=/app/app.py
ENV DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# 你的其他指令...
RUN apt-get update && apt-get install -y \
    tzdata \
    net-tools \
    iputils-ping \
    python3 \
    python3-pip \
    python3-dev \  
    build-essential \ 
    libjpeg-dev \ 
    zlib1g-dev \ 
    wget \
    && rm -rf /var/lib/apt/lists/*


# 安装flask
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade flask
RUN pip3 install sqlalchemy
RUN pip3 install flask_sqlalchemy
RUN pip3 install wtforms
RUN pip3 install captcha
RUN pip3 install flask_migrate
RUN pip3 install psutil
RUN pip3 install flask_login
RUN pip3 install requests
RUN pip3 install apscheduler

# 下载headscale二进制文件
RUN cd ${BASE_PATH}/headscale && \
    wget -O headscale https://github.com/juanfont/headscale/releases/download/v0.25.1/headscale_0.25.1_linux_amd64 && \
    chmod +x headscale

# 下载并解压s6-overlay
RUN wget -O /tmp/s6-overlay-noarch.tar.xz https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz && \
    tar -C / -Jxf /tmp/s6-overlay-noarch.tar.xz && \
    rm -f /tmp/s6-overlay-noarch.tar.xz && \
    wget -O /tmp/s6-overlay-x86_64.tar.xz https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz && \
    tar -C / -Jxf /tmp/s6-overlay-x86_64.tar.xz && \
    rm -f /tmp/s6-overlay-x86_64.tar.xz && \
    ln -sf /run /var/run

HEALTHCHECK --interval=10s --timeout=5s CMD /healthcheck.sh

ENTRYPOINT ["/init"]