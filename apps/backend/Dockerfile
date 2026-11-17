FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_NO_PROGRESS=1 UV_HTTP_TIMEOUT=120 UV_CONCURRENT_DOWNLOADS=4 \
    UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /uvx /bin/
RUN useradd --uid 10001 --create-home app
COPY pyproject.toml uv.lock ./

FROM base AS builder
RUN uv sync --frozen --no-install-project
COPY src ./src
COPY tests ./tests
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen

FROM builder AS development
USER app
CMD ["uvicorn", "support_agent.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

FROM builder AS production-dependencies
RUN uv sync --frozen --no-dev --no-editable --offline

FROM base AS production
COPY --from=production-dependencies /app/.venv /app/.venv
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
USER app
CMD ["uvicorn", "support_agent.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
