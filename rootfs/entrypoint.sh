#!/bin/sh
set -e
CONTAINER_DB_DIR="/var/lib/headscale"
DEFAULT_DATA_PATH="/app/default_data"
mkdir -p $CONTAINER_DB_DIR

if [ ! -f "$CONTAINER_DB_DIR/db.sqlite" ]; then
    echo "Copying default data to volume..."
    cp -r $DEFAULT_DATA_PATH/* $CONTAINER_DB_DIR/
fi

if [ ! -f "$CONTAINER_DB_DIR/db.sqlite" ]; then
    echo "Initializing database..."
    python3 -m flask db init
    python3 -m flask db migrate
    python3 -m flask db upgrade
else
    echo "Database already initialized."
fi
exec /init "$@"