# ensure executable
chmod +x start.sh

# add & commit (only if files changed)
git add start.sh cron/2fa-cron Dockerfile docker-compose.yml
git commit -m "Fix line endings, ensure start.sh executable, update cron path" || echo "no changes to commit"
git push origin main || echo "push failed - check network/auth"
