#!/bin/bash
# Entrypoint for the ERP image.
# Renders /etc/odoo/odoo.conf from ODOO_* environment variables, waits for
# PostgreSQL, optionally initialises a fresh database, then starts Odoo.
set -euo pipefail

: "${ODOO_DB_HOST:=db}"
: "${ODOO_DB_PORT:=5432}"
: "${ODOO_DB_USER:=odoo}"
: "${ODOO_DB_PASSWORD:?ODOO_DB_PASSWORD is required}"
: "${ODOO_DB_NAME:=erp}"
: "${ODOO_ADMIN_PASSWORD:?ODOO_ADMIN_PASSWORD is required}"
: "${ODOO_WORKERS:=3}"
: "${ODOO_MAX_CRON_THREADS:=1}"
: "${ODOO_LIMIT_MEMORY_SOFT:=671088640}"   # 640 MB per worker
: "${ODOO_LIMIT_MEMORY_HARD:=805306368}"   # 768 MB per worker
: "${ODOO_LIMIT_TIME_CPU:=600}"
: "${ODOO_LIMIT_TIME_REAL:=1200}"
: "${ODOO_PROXY_MODE:=True}"
: "${ODOO_LIST_DB:=False}"
: "${ODOO_LOG_LEVEL:=info}"
: "${ODOO_INIT_MODULES:=}"
: "${ODOO_LOAD_LANGUAGE:=id_ID,en_US}"

CONF="${ODOO_RC:-/etc/odoo/odoo.conf}"

cat > "$CONF" <<EOF
[options]
addons_path = /opt/odoo/custom-addons
data_dir = /var/lib/odoo
admin_passwd = ${ODOO_ADMIN_PASSWORD}
db_host = ${ODOO_DB_HOST}
db_port = ${ODOO_DB_PORT}
db_user = ${ODOO_DB_USER}
db_password = ${ODOO_DB_PASSWORD}
db_name = ${ODOO_DB_NAME}
dbfilter = ^${ODOO_DB_NAME}\$
list_db = ${ODOO_LIST_DB}
proxy_mode = ${ODOO_PROXY_MODE}
http_port = 8069
gevent_port = 8072
workers = ${ODOO_WORKERS}
max_cron_threads = ${ODOO_MAX_CRON_THREADS}
limit_memory_soft = ${ODOO_LIMIT_MEMORY_SOFT}
limit_memory_hard = ${ODOO_LIMIT_MEMORY_HARD}
limit_time_cpu = ${ODOO_LIMIT_TIME_CPU}
limit_time_real = ${ODOO_LIMIT_TIME_REAL}
log_level = ${ODOO_LOG_LEVEL}
without_demo = all
EOF
chmod 600 "$CONF"

wait-for-psql.py --db_host="$ODOO_DB_HOST" --db_port="$ODOO_DB_PORT" \
    --db_user="$ODOO_DB_USER" --db_password="$ODOO_DB_PASSWORD" --timeout=60

# First start on an empty server: create the database and install modules.
if [ -n "$ODOO_INIT_MODULES" ]; then
    export PGPASSWORD="$ODOO_DB_PASSWORD"
    if ! psql -h "$ODOO_DB_HOST" -p "$ODOO_DB_PORT" -U "$ODOO_DB_USER" -d postgres -tAc \
            "SELECT 1 FROM pg_database WHERE datname = '${ODOO_DB_NAME}'" | grep -q 1; then
        echo "Database '${ODOO_DB_NAME}' not found: installing ${ODOO_INIT_MODULES}"
        odoo -d "$ODOO_DB_NAME" -i "$ODOO_INIT_MODULES" \
            --load-language="$ODOO_LOAD_LANGUAGE" --stop-after-init --workers=0
    fi
    unset PGPASSWORD
fi

case "${1:-odoo}" in
    odoo | -*)
        [ "${1:-}" = "odoo" ] && shift
        exec odoo "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
