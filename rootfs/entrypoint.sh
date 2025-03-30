#!/bin/sh
set -e
CONTAINER_DB_DIR="/var/lib/headscale"
mkdir -p $CONTAINER_DB_DIR
if [ ! -f "$CONTAINER_DB_DIR/db.sqlite" ]; then
    echo "Initializing database..."
    python3 -m flask db init
    python3 -m flask db migrate
    python3 -m flask db upgrade
else
    echo "Database already initialized."
fi
exec /init "$@"