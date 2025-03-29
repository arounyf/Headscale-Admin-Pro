#!/command/with-contenv bash
set -e
CONTAINER_DB_DIR="/var/lib/headscale"
mkdir -p $CONTAINER_DB_DIR
if [ -z "$(ls -A $CONTAINER_DB_DIR 2>/dev/null)" ]; then
	echo "init database"
	python3 -m flask db init
	python3 -m flask db migrate
	python3 -m flask db upgrade
else
    echo "init database skipped, database already exists"
fi

APP_PY_PATH="/app/config.py"
sed -i '/^SERVER_HOST/d' "$APP_PY_PATH"
echo "SERVER_HOST='$SERVER_HOST'" >> "$APP_PY_PATH"

sed -i '/^TAILSCALE_UP_URL/d' "$APP_PY_PATH"
echo "TAILSCALE_UP_URL='$TAILSCALE_UP_URL'" >> "$APP_PY_PATH"