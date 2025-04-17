FROM registry.cn-hangzhou.aliyuncs.com/dubux/hs-admin:latest AS builder


FROM alpine:latest

ENV BASE_PATH="/etc/s6-overlay/s6-rc.d" \
    S6_OVERLAY_VERSION="3.2.0.2" \
    SERVER_NET="eth0" \
    FLASK_APP=/app/app.py 

COPY --chmod=755 ./rootfs /
COPY --from=builder ${BASE_PATH}/caddy/caddy ${BASE_PATH}/caddy/caddy

ARG ARCH="amd64"

RUN apk update && apk add --no-cache tzdata net-tools iputils gcc python3-dev musl-dev linux-headers python3 py3-pip wget bash && \
    ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    pip3 install --no-cache-dir --break-system-packages pyyaml psutil flask sqlalchemy flask_sqlalchemy wtforms captcha flask_migrate psutil flask_login requests apscheduler

RUN if [ "$ARCH" = "arm64" ]; then S6_ARCH="aarch64"; else S6_ARCH="x86_64"; fi && \
    wget -O /tmp/s6-overlay-noarch.tar.xz https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz && \
    tar -C / -Jxf /tmp/s6-overlay-noarch.tar.xz && \
    rm -f /tmp/s6-overlay-noarch.tar.xz && \
    wget -O /tmp/s6-overlay-${S6_ARCH}.tar.xz https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${S6_ARCH}.tar.xz && \
    tar -C / -Jxf /tmp/s6-overlay-${S6_ARCH}.tar.xz && \
    rm -f /tmp/s6-overlay-${S6_ARCH}.tar.xz

HEALTHCHECK --interval=10s --timeout=5s CMD /healthcheck.sh

ENTRYPOINT ["/init"]