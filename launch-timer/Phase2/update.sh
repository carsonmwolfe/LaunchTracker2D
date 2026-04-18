#!/bin/bash
# Auto-updater for RangeTrack OS
# Runs hourly via cron. Pulls latest from GitHub, restarts server, clears cache.
#
# Cron setup (crontab -e on Pi):
#   0 * * * * /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh >> /home/pi/update.log 2>&1

REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
BRANCH="Phase3"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"
UPDATE_LOG="/home/pi/.rangetrack_updates.json"
LOCK_FILE="/tmp/rangetrack_update.lock"

# ── Lock — prevent supervisor and cron colliding ───────────────────────────────
if [ -e "$LOCK_FILE" ]; then
    echo "$LOG_PREFIX Already running (lock exists) — skipping"
    exit 0
fi
trap 'rm -f "$LOCK_FILE"' EXIT
touch "$LOCK_FILE"

# ── Sanity checks ──────────────────────────────────────────────────────────────

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "$LOG_PREFIX ERROR: $REPO_DIR is not a git repo — aborting"
    exit 1
fi

cd "$REPO_DIR" || { echo "$LOG_PREFIX ERROR: cannot cd to $REPO_DIR"; exit 1; }

# Check git is working
if ! git status --short > /dev/null 2>&1; then
    echo "$LOG_PREFIX ERROR: git not working in $REPO_DIR — aborting"
    exit 1
fi

# Check we are on the right branch (or switch to it)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "$LOG_PREFIX WARNING: on branch '$CURRENT_BRANCH', switching to '$BRANCH'"
    git checkout "$BRANCH" --quiet || { echo "$LOG_PREFIX ERROR: cannot checkout $BRANCH"; exit 1; }
fi

# ── Fetch ──────────────────────────────────────────────────────────────────────

echo "$LOG_PREFIX Fetching origin/$BRANCH..."
if ! git fetch origin "$BRANCH" --quiet 2>&1; then
    echo "$LOG_PREFIX ERROR: git fetch failed — no internet? Skipping update."
    exit 1
fi

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null)

if [ -z "$REMOTE" ]; then
    echo "$LOG_PREFIX ERROR: could not resolve origin/$BRANCH — skipping"
    exit 1
fi

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$LOG_PREFIX Already up to date ($LOCAL)"
    exit 0
fi

echo "$LOG_PREFIX Update available: $LOCAL → $REMOTE"

# ── Apply update ───────────────────────────────────────────────────────────────

# Hard reset — always matches remote exactly, no conflicts possible
git reset --hard "origin/$BRANCH"
RESET_EXIT=$?

if [ $RESET_EXIT -ne 0 ]; then
    echo "$LOG_PREFIX ERROR: git reset --hard failed (exit $RESET_EXIT) — aborting"
    exit 1
fi

# Verify we actually got to the right commit
NEW_HEAD=$(git rev-parse HEAD)
if [ "$NEW_HEAD" != "$REMOTE" ]; then
    echo "$LOG_PREFIX ERROR: after reset, HEAD=$NEW_HEAD but expected $REMOTE — something is wrong"
    exit 1
fi

echo "$LOG_PREFIX Successfully updated to $NEW_HEAD"

# Re-apply execute permission (lost on every git reset --hard)
chmod +x "$REPO_DIR/launch-timer/Phase2/update.sh"
chmod +x "$REPO_DIR/launch-timer/Phase2/start.sh"

# ── Clear cache + restart ──────────────────────────────────────────────────────

# Wipe Chromium cache so all pages get fresh files (not just current tab)
rm -rf /home/pi/.cache/chromium/Default/Cache/* 2>/dev/null
echo "$LOG_PREFIX Chromium cache cleared"

# Restart Flask server
echo "$LOG_PREFIX Restarting server..."
pkill -f "python3 server.py" 2>/dev/null
fuser -k 5001/tcp 2>/dev/null || true
sleep 2
cd "$REPO_DIR/launch-timer/Phase2" || exit 1
nohup python3 server.py >> /home/pi/server.log 2>&1 &
SERVER_PID=$!

# Wait for server to actually respond before reloading Chromium (max 20s)
for i in $(seq 1 13); do
    if curl -s -o /dev/null http://localhost:5001/ --max-time 1 2>/dev/null; then
        echo "$LOG_PREFIX Server ready (PID $SERVER_PID)"
        break
    fi
    sleep 1.5
done
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "$LOG_PREFIX ERROR: server failed to start — check server.log"
fi

# Client reloads itself via /api/version polling — no xdotool needed
echo "$LOG_PREFIX Server updated — client will reload on next version poll"

# ── Log the update ─────────────────────────────────────────────────────────────

SHORT=$(git -C "$REPO_DIR" log -1 --pretty="%s" 2>/dev/null)
TIME=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MSG="$SHORT" COMMIT_TIME="$TIME" COMMIT_FROM="$LOCAL" COMMIT_TO="$NEW_HEAD" \
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
except Exception:
    updates = []
updates.append(entry)
updates = updates[-20:]
with open(log_file, 'w') as f:
    json.dump(updates, f)
print('Update logged.')
PYEOF

echo "$LOG_PREFIX Done: $SHORT"
curl -s -X POST http://localhost:5001/api/notify-push \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"UPDATE COMPLETE\",\"msg\":\"$SHORT\"}" > /dev/null 2>&1
