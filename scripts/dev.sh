#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
[ -f .env ] || { printf '%s\n' 'Run sh scripts/setup.sh first.' >&2; exit 1; }
docker compose -f compose.yaml -f compose.dev.yaml up --build --detach --wait --wait-timeout 240
docker compose -f compose.yaml -f compose.dev.yaml port nginx 80
