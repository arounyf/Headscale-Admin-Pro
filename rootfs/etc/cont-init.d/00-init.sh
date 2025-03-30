#!/command/with-contenv bash
set -e
CONTAINER_DB_DIR="/var/lib/headscale"
mkdir -p $CONTAINER_DB_DIR
DATABASE_FILE="$CONTAINER_DB_DIR/db.sqlite"
if [ ! -f "$DATABASE_FILE" ]; then
    echo "Initializing database..."
    python3 -m flask db init
    python3 -m flask db migrate
    python3 -m flask db upgrade
fi
echo "Database initialized."