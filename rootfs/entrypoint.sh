#!/bin/bash
set -e
export FLASK_APP=/app/app.py
CONTAINER_DB_DIR="/var/lib/headscale"
mkdir -p $CONTAINER_DB_DIR
if [ -z "$(ls -A $CONTAINER_DB_DIR 2>/dev/null)" ]; then
    echo "Initializing database..."
    python3 -m flask db init
    python3 -m flask db migrate
    python3 -m flask db upgrade
else
    echo "Database already initialized."
fi
exec /init "$@"