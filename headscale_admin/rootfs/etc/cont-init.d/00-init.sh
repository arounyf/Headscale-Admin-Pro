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