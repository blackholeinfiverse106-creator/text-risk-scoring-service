#!/usr/bin/env bash
# ============================================================
# BHIV Enforcement Gateway — Startup Script
# Deterministic enforcement service launcher
# ============================================================

set -euo pipefail

HOST="${GATEWAY_HOST:-0.0.0.0}"
PORT="${GATEWAY_PORT:-8000}"
WORKERS="${GATEWAY_WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "============================================================"
echo "  BHIV Enforcement Gateway"
echo "  Host:     ${HOST}"
echo "  Port:     ${PORT}"
echo "  Workers:  ${WORKERS}"
echo "  LogLevel: ${LOG_LEVEL}"
echo "============================================================"

exec uvicorn app.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --log-level "${LOG_LEVEL}"
