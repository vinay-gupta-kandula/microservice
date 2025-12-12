#!/usr/bin/env sh
set -e

# make startup tolerant:
# 1) populate /data/seed.txt in the persistent volume if missing
# 2) ensure permissions are safe
# 3) start cron then start uvicorn

# copy seed into persistent volume if missing
if [ ! -s /data/seed.txt ] && [ -s /app/cron/data/seed.txt ]; then
  echo "Seed file missing in /data; copying initial seed into persistent volume"
  cp /app/cron/data/seed.txt /data/seed.txt
  chmod 600 /data/seed.txt || true
fi

# ensure cron log dir exists
mkdir -p /cron
chmod 755 /cron || true

# start cron (Debian/Ubuntu binary is 'cron')
# Use 'crontab' file already created during Dockerfile build
crond_command=""
if command -v cron >/dev/null 2>&1; then
  # system cron daemon
  cron || true
elif command -v crond >/dev/null 2>&1; then
  crond || true
elif command -v busybox >/dev/null 2>&1 && busybox crond >/dev/null 2>&1; then
  busybox crond -f -l 8 >/dev/null 2>&1 &
fi

# small sleep to allow cron to initialize
sleep 1

# finally start the app (uvicorn) in foreground
exec uvicorn app:app --host 0.0.0.0 --port 8080
