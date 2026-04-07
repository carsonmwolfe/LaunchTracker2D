#!/bin/bash
# Auto-updater: checks for new commits on GitHub once per hour via cron.
# If changes are found, pulls and restarts the server.
# Updates are included in the daily health digest (not sent immediately).
#
# Cron setup (crontab -e on Pi):
#   0 * * * * /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh >> /home/pi/update.log 2>&1

REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
BRANCH="Phase3"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"
UPDATE_LOG="/home/pi/.rangetrack_updates.json"

cd "$REPO_DIR" || { echo "$LOG_PREFIX ERROR: repo dir not found"; exit 1; }

# Stash any local changes so pull doesn't conflict
STASHED=0
if ! git diff --quiet || ! git diff --cached --quiet; then
    git stash && STASHED=1
fi

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
if [ "$STASHED" = "1" ]; then git stash pop 2>/dev/null; fi

# Restart server
echo "$LOG_PREFIX Restarting server..."
pkill -f "python3 server.py" 2>/dev/null
sleep 2
cd launch-timer/Phase2
nohup python3 server.py >> /home/pi/server.log 2>&1 &
SERVER_PID=$!
echo "$LOG_PREFIX Server restarted (PID $SERVER_PID)"

# Log the update so the daily digest can include it
SHORT=$(git log -1 --pretty="%s" 2>/dev/null)
TIME=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MSG="$SHORT" COMMIT_TIME="$TIME" COMMIT_FROM="$LOCAL" COMMIT_TO="$REMOTE" \
python3 - <<'PYEOF'
import json, os
log_file = os.environ['HOME'] + '/.rangetrack_updates.json'
entry = {
    'time':   os.environ.get('COMMIT_TIME', ''),
    'commit': os.environ.get('COMMIT_MSG',  ''),
    'from':   os.environ.get('COMMIT_FROM', ''),
    'to':     os.environ.get('COMMIT_TO',   ''),
}
try:
    with open(log_file) as f:
        updates = json.load(f)
except:
    updates = []
updates.append(entry)
updates = updates[-10:]
with open(log_file, 'w') as f:
    json.dump(updates, f)
print('Update logged.')
PYEOF

echo "$LOG_PREFIX Update logged: $SHORT"
