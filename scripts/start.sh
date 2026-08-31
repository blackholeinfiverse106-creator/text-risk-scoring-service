#!/usr/bin/env bash
# ============================================================
# BHIV Rajya Enforcement Gateway — Startup Script
# Deterministic enforcement service launcher with signal trapping
# ============================================================

set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-${GATEWAY_PORT:-8000}}"
WORKERS="${WORKERS:-${GATEWAY_WORKERS:-1}}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "============================================================"
echo "  🚀 BHIV Rajya Enforcement Gateway Starting"
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
