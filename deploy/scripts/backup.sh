#!/usr/bin/env bash
# Backup TimescaleDB + critical configs. Usage: backup.sh [APP_ROOT] [BACKUP_DIR] [RETAIN_DAYS]
set -euo pipefail

APP_ROOT="${1:-/opt/minehub}"
BACKUP_DIR="${2:-/var/backups/minehub}"
RETAIN_DAYS="${3:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/minehub_${STAMP}"

mkdir -p "${OUT}"

cd "${APP_ROOT}"
# Dump database from the timescaledb container
docker compose exec -T timescaledb pg_dump -U "${POSTGRES_USER:-minehub}" -d "${POSTGRES_DB:-minehub}" -Fc \
  > "${OUT}/minehub.dump"

# Snapshot config and env (redact nothing here — protect BACKUP_DIR permissions)
cp -a config "${OUT}/config" 2>/dev/null || true
cp -a .env "${OUT}/env.snapshot" 2>/dev/null || true

tar -C "${BACKUP_DIR}" -czf "${OUT}.tgz" "$(basename "${OUT}")"
rm -rf "${OUT}"

# Retention
find "${BACKUP_DIR}" -name 'minehub_*.tgz' -mtime "+${RETAIN_DAYS}" -delete

# Optional metric stamp for BackupMissed alert (Redis or file)
echo "$(date +%s)" > "${BACKUP_DIR}/last_success.unixtime"
echo "backup ok: ${OUT}.tgz"
