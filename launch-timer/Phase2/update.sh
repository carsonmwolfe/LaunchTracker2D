#!/bin/bash
# Auto-updater: checks for new commits on GitHub once per hour via cron.
# If changes are found, pulls, restarts the server, and sends a Gmail notification.
#
# SETUP (run once on Pi):
#   chmod +x /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh
#   crontab -e
#   Add this line:
#   0 * * * * /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh >> /home/pi/update.log 2>&1

REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
BRANCH="Phase3"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

cd "$REPO_DIR" || { echo "$LOG_PREFIX ERROR: repo dir not found"; exit 1; }

# Stash any local changes to settings/cache so pull doesn't conflict
git stash -- data_cache.json settings.json 2>/dev/null

# Fetch remote without merging
git fetch origin "$BRANCH" --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$LOG_PREFIX Already up to date ($LOCAL)"
    exit 0
fi

echo "$LOG_PREFIX New commits found — pulling ($LOCAL → $REMOTE)"
git pull origin "$BRANCH" --quiet

# Restore stashed local files
git stash pop 2>/dev/null

# Restart server
echo "$LOG_PREFIX Restarting server..."
pkill -f "python3 server.py" 2>/dev/null
sleep 2
cd launch-timer/Phase2
nohup python3 server.py >> /home/pi/server.log 2>&1 &
SERVER_PID=$!
echo "$LOG_PREFIX Server restarted (PID $SERVER_PID)"

# Send Gmail notification
SHORT=$(git log -1 --pretty="%s" 2>/dev/null)
TIME=$(date '+%I:%M %p')
MSG="RangeTrack OS updated at $TIME — $SHORT"

python3 /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/notify.py "$MSG"
echo "$LOG_PREFIX Notification sent: $MSG"
