#!/bin/bash
# Auto-updater for RangeTrack OS
# Runs hourly via cron. Pulls latest from GitHub, restarts server, clears cache.
#
# Cron setup (crontab -e on Pi):
#   0 * * * * /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh >> /home/pi/update.log 2>&1

REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
# Default to release branch — override by creating /home/pi/.rangetrack_branch
BRANCH="release"
if [ -f /home/pi/.rangetrack_branch ]; then
    BRANCH=$(cat /home/pi/.rangetrack_branch | tr -d '[:space:]')
fi
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
date -u '+%Y-%m-%dT%H:%M:%SZ' > /home/pi/.rangetrack_last_check

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

# Check we are on the right branch (or switch to it). Force the switch, discarding
# local changes to tracked files (e.g. settings.json the app writes) — we hard-reset
# to origin below anyway, so a dirty tree must not block a channel switch.
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "$LOG_PREFIX WARNING: on branch '$CURRENT_BRANCH', switching to '$BRANCH'"
    git fetch origin "$BRANCH" --quiet 2>/dev/null
    git checkout -f -B "$BRANCH" "origin/$BRANCH" --quiet || { echo "$LOG_PREFIX ERROR: cannot checkout $BRANCH"; exit 1; }
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

# Back up server.py BEFORE the reset so corruption recovery has a fallback
BACKUP_PY="/home/pi/.rangetrack_server_backup.py"
cp "$REPO_DIR/launch-timer/Phase2/server.py" "$BACKUP_PY" 2>/dev/null
# Ensure key files are owned by pi so server.py can write settings etc.
chown pi:pi "$REPO_DIR/launch-timer/Phase2/settings.json" 2>/dev/null
chown pi:pi "$REPO_DIR/launch-timer/Phase2/data_cache.json" 2>/dev/null

# Verify server.py wasn't corrupted (SD card write failure during power cut)
SERVER_PY="$REPO_DIR/launch-timer/Phase2/server.py"
if [ ! -s "$SERVER_PY" ]; then
    echo "$LOG_PREFIX ERROR: server.py is empty after git reset (SD card corruption?) — retrying fetch"
    git fetch origin "$BRANCH" --quiet
    git reset --hard "origin/$BRANCH"
    if [ ! -s "$SERVER_PY" ]; then
        echo "$LOG_PREFIX ERROR: server.py still empty after retry — aborting update"
        exit 1
    fi
    echo "$LOG_PREFIX server.py recovered successfully"
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

# ── Provision — sync system configs that may have changed in setup.sh ─────────
# This runs on every successful pull so existing Pis don't need reimaging.

PHASE2="$REPO_DIR/launch-timer/Phase2"

# Ensure health cron job and nightly WebKit restart are installed
CRON_TMP=$(mktemp)
crontab -l 2>/dev/null | grep -v "health.py" | grep -v "webkit_launch" > "$CRON_TMP"
echo "*/5 * * * * python3 $PHASE2/health.py >> /home/pi/health.log 2>&1" >> "$CRON_TMP"
echo "0 3 * * * pkill -f webkit_launch.py; sleep 3; XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 nohup python3 $PHASE2/webkit_launch.py http://localhost:5001/ >> /home/pi/server.log 2>&1 & echo \$! > /tmp/rangetrack_browser.pid" >> "$CRON_TMP"
crontab "$CRON_TMP" && echo "$LOG_PREFIX Cron jobs provisioned"
rm -f "$CRON_TMP"

# Ensure sudoers has all required NOPASSWD entries
printf 'pi ALL=(ALL) NOPASSWD: /sbin/reboot\npi ALL=(ALL) NOPASSWD: /usr/bin/timedatectl\npi ALL=(ALL) NOPASSWD: /usr/bin/nmcli\npi ALL=(ALL) NOPASSWD: /usr/sbin/ifconfig\npi ALL=(ALL) NOPASSWD: /usr/sbin/iwlist\npi ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart NetworkManager\npi ALL=(ALL) NOPASSWD: /usr/bin/raspi-config\npi ALL=(ALL) NOPASSWD: /usr/sbin/iw\npi ALL=(ALL) NOPASSWD: /usr/sbin/rfkill\n' | sudo tee /etc/sudoers.d/rangetrack > /dev/null
echo "$LOG_PREFIX sudoers updated"

# Ensure WiFi country is set — REQUIRED for 5GHz to work on Raspberry Pi.
# Without a regulatory country the radio refuses ALL 5GHz channels, so any
# 5GHz network fails to connect (and often mis-reports as a wrong password).
WIFI_COUNTRY="US"
CUR_REG=$(iw reg get 2>/dev/null | grep -m1 '^country' | awk '{print $2}' | tr -d ':')
if [ "$CUR_REG" != "$WIFI_COUNTRY" ]; then
    command -v raspi-config >/dev/null 2>&1 && sudo raspi-config nonint do_wifi_country "$WIFI_COUNTRY" 2>/dev/null
    sudo iw reg set "$WIFI_COUNTRY" 2>/dev/null || true
    sudo rfkill unblock wifi 2>/dev/null || true
    echo "$LOG_PREFIX WiFi country set to $WIFI_COUNTRY (enables 5GHz)"
fi

# WiFi reliability: on every saved wifi profile, disable power-save and never
# give up reconnecting (NM's default gives up after 4 tries, leaving the unit
# offline until reboot). nmcli only — on these units sudo is passwordless ONLY
# for a whitelist (nmcli, systemctl restart NM, reboot...), so sudo tee/iw writes
# silently fail. Idempotent, so new profiles get fixed on the next update.
nmcli -t -f NAME,TYPE con show 2>/dev/null | awk -F: '$2=="802-11-wireless"{print $1}' | while read -r P; do
    sudo nmcli connection modify "$P" 802-11-wireless.powersave 2 connection.autoconnect-retries 0 2>/dev/null || true
done
echo "$LOG_PREFIX WiFi reliability applied to saved profiles (powersave off, infinite retries)"

# Ensure Tailscale restarts after failure and waits for NetworkManager
# (tailscaled starts before WiFi is connected at boot and fails silently)
TAILSCALE_OVERRIDE="/etc/systemd/system/tailscaled.service.d/rangetrack.conf"
if [ ! -f "$TAILSCALE_OVERRIDE" ] || ! grep -q "network-online" "$TAILSCALE_OVERRIDE" 2>/dev/null; then
    sudo mkdir -p "$(dirname "$TAILSCALE_OVERRIDE")"
    printf '[Unit]\nAfter=NetworkManager-wait-online.service\nWants=NetworkManager-wait-online.service\n\n[Service]\nRestart=on-failure\nRestartSec=10s\n' | sudo tee "$TAILSCALE_OVERRIDE" > /dev/null
    sudo systemctl daemon-reload
    echo "$LOG_PREFIX Tailscale systemd override installed"
fi

# Ensure gnome-keyring is permanently disabled
CHANGED_KR=0
for KR in gnome-keyring-secrets gnome-keyring-ssh gnome-keyring-pkcs11 gnome-keyring-gpg; do
    KR_FILE="/home/pi/.config/autostart/${KR}.desktop"
    if [ ! -f "$KR_FILE" ] || ! grep -q "Hidden=true" "$KR_FILE" 2>/dev/null; then
        mkdir -p /home/pi/.config/autostart
        printf '[Desktop Entry]\nType=Application\nHidden=true\n' > "$KR_FILE"
        CHANGED_KR=1
    fi
done
[ "$CHANGED_KR" -eq 1 ] && echo "$LOG_PREFIX gnome-keyring disabled"

# ── Clear cache + restart ──────────────────────────────────────────────────────

# Rotate server log — keep last 500 lines to prevent SD card fill
if [ -f /home/pi/server.log ]; then
    tail -500 /home/pi/server.log > /tmp/server.log.tmp && mv /tmp/server.log.tmp /home/pi/server.log
fi

# Rotate health log — keep last 1000 lines
if [ -f /home/pi/health.log ]; then
    tail -1000 /home/pi/health.log > /tmp/health.log.tmp && mv /tmp/health.log.tmp /home/pi/health.log
fi

# Restart Flask server
echo "$LOG_PREFIX Restarting server..."
pkill -f "python3 server.py" 2>/dev/null
fuser -k 5001/tcp 2>/dev/null || true
sleep 2
cd "$REPO_DIR/launch-timer/Phase2" || exit 1
nohup nice -n -10 python3 server.py >> /home/pi/server.log 2>&1 &
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

# Restart browser — same logic as start.sh: Chromium for >700MB RAM, WebKit2GTK otherwise
pkill -f webkit_launch.py 2>/dev/null
pkill -f chromium 2>/dev/null
sleep 2
MEM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
CHROMIUM_BIN=$(command -v chromium-browser || command -v chromium 2>/dev/null)
if [ "$MEM_MB" -gt 700 ] && [ -n "$CHROMIUM_BIN" ]; then
    rm -f /home/pi/.config/chromium/Singleton* 2>/dev/null
    XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 \
        nohup "$CHROMIUM_BIN" --kiosk --no-memcheck --noerrdialogs --disable-infobars \
        --disable-features=ChromeWhatsNew,Translate --no-default-browser-check \
        --disable-background-networking --disable-session-crashed-bubble \
        --window-size=800,480 --disable-notifications --disable-popup-blocking \
        --no-first-run --use-angle=gles --ozone-platform=wayland \
        --password-store=basic --disable-renderer-accessibility \
        --disable-extensions --disable-sync --disable-component-update \
        --renderer-process-limit=1 --app="http://localhost:5001/" \
        >> /home/pi/server.log 2>&1 &
    echo $! > /tmp/rangetrack_browser.pid
    echo "$LOG_PREFIX Chromium restarted (PID $!)"
else
    XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 \
        nohup python3 "$PHASE2/webkit_launch.py" http://localhost:5001/ \
        >> /home/pi/server.log 2>&1 &
    echo $! > /tmp/rangetrack_browser.pid
    echo "$LOG_PREFIX WebKit restarted (PID $!)"
fi

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
