#!/usr/bin/env sh
set -e

# ensure UTC in runtime
export TZ=UTC
export PYTHONUNBUFFERED=1

# start cron (if available) in background, silence harmless errors
crond || true

# small sleep to let cron start
sleep 1

# start the FastAPI server (uvicorn) as PID 1 process
# adjust the module: uvicorn app:app if your app entry is app.py -> app
exec uvicorn app:app --host 0.0.0.0 --port 8080
