#!/bin/sh
set -e

echo "Starting cron..."
cron -f &

echo "Starting uvicorn..."
exec uvicorn app:app --host 0.0.0.0 --port 8080
