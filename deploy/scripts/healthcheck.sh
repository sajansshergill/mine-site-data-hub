#!/usr/bin/env bash
# Quick stack health probe. Usage: healthcheck.sh [APP_ROOT]
set -euo pipefail

APP_ROOT="${1:-/opt/minehub}"
cd "${APP_ROOT}"

fail=0
check() {
  local name="$1" url="$2"
  if curl -fsS --max-time 5 "${url}" >/dev/null; then
    echo "ok  ${name}"
  else
    echo "FAIL ${name} (${url})"
    fail=1
  fi
}

check api       "http://127.0.0.1:8000/health"
check grafana   "http://127.0.0.1:3000/api/health"
check prometheus "http://127.0.0.1:9090/-/healthy"

# Compose service status
if ! docker compose ps --status running | grep -q timescaledb; then
  echo "FAIL timescaledb not running"
  fail=1
fi

exit "${fail}"
