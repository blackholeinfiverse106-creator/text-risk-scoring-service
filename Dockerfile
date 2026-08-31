# ============================================================
# BHIV Rajya Enforcement Gateway — Production Dockerfile
# Deterministic, secure container packaging
# ============================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# ---- Build stage: install dependencies ----
FROM base AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage ----
FROM base AS runtime

# Install runtime utilities (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 enforcement && \
    useradd --uid 1000 --gid enforcement --shell /bin/bash --create-home enforcement

WORKDIR /srv/enforcement-gateway

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application modules and startup scripts
COPY app/ ./app/
COPY policy_engine/ ./policy_engine/
COPY feedback/ ./feedback/
COPY scripts/ ./scripts/

# Ensure start script is executable and transfer ownership
RUN chmod +x ./scripts/start.sh && \
    chown -R enforcement:enforcement /srv/enforcement-gateway

USER enforcement

EXPOSE 8000

# Health check — deterministic liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)" || exit 1

# Entry point — enforcement gateway starts here
CMD ["./scripts/start.sh"]
