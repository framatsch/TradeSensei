# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: builder — install uv and all dependencies into /app/.venv
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-alpine AS builder

# Install uv via the official installer script
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first (layer cache optimisation)
COPY pyproject.toml uv.lock* ./

# Sync all dependency groups (including dev) into the project venv.
# --frozen: never update the lockfile inside the image.
# --no-install-project: don't install the project itself yet.
RUN uv sync --frozen --no-install-project

# Copy application source code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install the project itself (editable-equivalent for a src layout)
RUN uv sync --frozen

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: development — extends builder with reload support
# ─────────────────────────────────────────────────────────────────────────────
FROM builder AS development

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: production — minimal runtime image, no build tooling
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-alpine AS production

ARG GITHUB_REPOSITORY
ENV GITHUB_REPOSITORY=${GITHUB_REPOSITORY}

# Copy only the installed virtual environment and application code
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Run as non-root user for security
LABEL org.opencontainers.image.source=https://github.com/${GITHUB_REPOSITORY}
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
