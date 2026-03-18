# ============================================================
# BHIV Enforcement Gateway — Production Dockerfile
# Deterministic, clean service packaging
# ============================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---- Build stage: install dependencies ----
FROM base AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage ----
FROM base AS runtime

# Create non-root user for security
RUN groupadd --gid 1000 enforcement && \
    useradd --uid 1000 --gid enforcement --shell /bin/bash --create-home enforcement

WORKDIR /srv/enforcement-gateway

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code only (no tests, tools, docs)
COPY app/ ./app/
COPY policy_engine/ ./policy_engine/
COPY feedback/ ./feedback/

# Set ownership
RUN chown -R enforcement:enforcement /srv/enforcement-gateway

USER enforcement

EXPOSE 8000

# Health check — deterministic liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Entry point — enforcement gateway starts here
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
