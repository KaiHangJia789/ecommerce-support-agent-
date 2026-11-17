#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
docker info --format '{{.OSType}}' >/dev/null
python3 scripts/bootstrap.py
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
printf '%s\n' 'Ready. Start: sh scripts/dev.sh'
