#!/usr/bin/env sh
set -e

# Ensure required directories exist
mkdir -p /data /cron
chmod 755 /data /cron || true

# Start cron daemon (Debian/Ubuntu)
cron

# Small delay to let cron initialize
sleep 1

# Start FastAPI application
exec uvicorn app:app --host 0.0.0.0 --port 8080
