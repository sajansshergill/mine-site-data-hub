#!/usr/bin/env bash
# Restore from a backup tarball. Usage: restore.sh <backup.tgz> [APP_ROOT]
set -euo pipefail

ARCHIVE="${1:?usage: restore.sh <minehub_YYYYMMDD.tgz> [APP_ROOT]}"
APP_ROOT="${2:-/opt/minehub}"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

tar -xzf "${ARCHIVE}" -C "${TMP}"
SRC="$(find "${TMP}" -maxdepth 1 -type d -name 'minehub_*' | head -n1)"
DUMP="$(find "${SRC}" -name 'minehub.dump' | head -n1)"

[[ -n "${DUMP}" ]] || { echo "no dump found in archive"; exit 1; }

cd "${APP_ROOT}"
docker compose up -d timescaledb
sleep 5

# Drop/recreate and restore
docker compose exec -T timescaledb pg_restore -U "${POSTGRES_USER:-minehub}" -d "${POSTGRES_DB:-minehub}" \
  --clean --if-exists < "${DUMP}" || true

echo "restore complete from ${ARCHIVE}"
