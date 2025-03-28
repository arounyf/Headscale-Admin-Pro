FROM alpine:latest

ENV BASE_PATH="/etc/s6-overlay/s6-rc.d" \
    S6_OVERLAY_VERSION="3.2.0.2"

COPY --chmod=755 ./rootfs /

RUN apk update && \
    apk add --no-cache \
        bash \
        curl \
        iputils \
        net-tools \
        tzdata \
        python3 \
        py3-pip \
        wget \
        gcc p3-dev musl-dev linux-headers

RUN python3 -m venv /venv
RUN /venv/bin/pip install --no-cache-dir \
        flask \
        sqlalchemy \
        flask_sqlalchemy \
        wtforms \
        captcha \
        flask_migrate \
        psutil \
        flask_login \
        requests \
        apscheduler

RUN cd ${BASE_PATH}/headscale \
    wget -O headscale https://github.com/juanfont/headscale/releases/download/v0.25.1/headscale_0.25.1_linux_amd64 \
    chmod u+x headscale

RUN wget -O /tmp/s6-overlay-noarch.tar.xz https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz \
    && tar -C / -Jxf /tmp/s6-overlay-noarch.tar.xz \
    && rm -f /tmp/s6-overlay-noarch.tar.xz \
    && wget -O /tmp/s6-overlay-x86_64.tar.xz https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz \
    && tar -C / -Jxf /tmp/s6-overlay-x86_64.tar.xz \
    && rm -f /tmp/s6-overlay-x86_64.tar.xz \
    && ln -sf /run /var/run

HEALTHCHECK --interval=10s --timeout=5s CMD /healthcheck.sh

ENTRYPOINT ["/init"]