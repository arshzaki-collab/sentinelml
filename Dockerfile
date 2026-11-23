# ==============================================================================
# BLIND BILLION 2.0 — BACKEND DOCKERFILE
# Multi-stage production container for FastAPI server with DuckDB cache
# ==============================================================================

# Build stage
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -e .

# Runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -s /bin/bash -m appuser

# Install application dependencies
COPY --from=builder /build/wheels /wheels
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* uvicorn[standard] && \
    rm -rf /wheels

# Copy application source and data foundation
COPY src/ /app/src/
COPY data/blindbillion.duckdb /app/data/blindbillion.duckdb
RUN pip install --no-cache-dir -e .

# Set up storage directories with proper permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    ANALYTICAL_DB_PATH=/app/data/blindbillion.duckdb \
    DATABASE_URL=sqlite:////app/data/multiplayer.db \
    ALLOWED_ORIGINS="http://localhost:5173,http://localhost:3000" \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "blindbillion.multiplayer.app:app", "--host", "0.0.0.0", "--port", "8000"]
