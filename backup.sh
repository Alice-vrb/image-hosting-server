#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CONTAINER="postgres_container"
BACKUP_DIR="backups"
LOG_FILE="logs/app.log"
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR" logs

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" \
        || echo "Warning: could not write to $LOG_FILE" >&2
}

if docker exec "$CONTAINER" sh -c \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
    > "$BACKUP_FILE"; then
    log "Success: database backup created: ${BACKUP_FILE}"
    echo "Backup created: ${BACKUP_FILE}"
    find "$BACKUP_DIR" -name 'backup_*.sql' -mtime +"$KEEP_DAYS" -delete
else
    rm -f "$BACKUP_FILE"
    log "Error: database backup failed (container: ${CONTAINER})"
    echo "Backup failed" >&2
    exit 1
fi