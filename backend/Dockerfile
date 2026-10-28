# syntax=docker/dockerfile:1

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app

# Platform + verticals (composition root expects sibling work/ and notify/)
COPY core/pyproject.toml core/uv.lock ./core/
COPY core/src ./core/src
COPY work/src ./work/src
COPY notify/src ./notify/src
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

WORKDIR /app/core

RUN uv sync --frozen --no-dev

RUN mkdir -p /app/core/var/uploads

ENV PATH="/app/core/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# main.app is lazy (None until attribute access); use the factory entrypoint.
CMD ["uvicorn", "main:build_app", "--factory", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
