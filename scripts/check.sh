#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
uv run --project apps/backend --frozen python -m unittest discover -s tests
uv run --project apps/backend --frozen ruff check apps/backend
uv run --project apps/backend --frozen ruff format --check apps/backend
uv run --project apps/backend --frozen pytest apps/backend/tests
pnpm --dir apps/web check
