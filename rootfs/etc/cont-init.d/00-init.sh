#!/command/with-contenv bash
set -e

CONTAINER_CONFIG_DIR="/etc/headscale"
INIT_DATA_APP_CONFIG="/data"
if [ -z "$(ls -A $CONTAINER_CONFIG_DIR 2>/dev/null)" ]; then
	echo "复制配置文件"
    cp -r $INIT_DATA_APP_CONFIG/etc/headscale /etc/
else
    echo "检测到headscale存在配置文件"
fi

CONTAINER_DB_DIR="/var/lib/headscale"
if [ -z "$(ls -A $CONTAINER_DB_DIR 2>/dev/null)" ]; then
	echo "将自动复制数据库文件"
	cp -r $INIT_DATA_APP_CONFIG/var /
else
    echo "检测到SQLITE已有数据"
fi

CADDY_DIR="/etc/caddy"
if [ -z "$(ls -A $CADDY_DIR 2>/dev/null)" ]; then
	echo "将自动复制Caddyfile"
	cp -r $INIT_DATA_APP_CONFIG/etc/caddy /etc/
else
    echo "检测到Caddyfile已存在"
fi