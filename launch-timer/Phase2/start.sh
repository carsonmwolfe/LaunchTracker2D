#!/bin/bash
# RangeTrack OS — Startup & Supervisor
# Handles server start, health check, WebKit launch, and crash recovery.

APP_DIR="/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2"
SERVER_LOG="/home/pi/server.log"
APP_URL="http://localhost:5001/"

WEBKIT="python3 $APP_DIR/webkit_launch.py"

# ── Ensure Wayland display is set ────────────────────────────────────────────
export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

# ── Kill stale browser + server ───────────────────────────────────────────────
pkill -f webkit_launch 2>/dev/null
sleep 2

# ── Kill anything on port 5001 ────────────────────────────────────────────────
fuser -k 5001/tcp 2>/dev/null || true
sleep 1

# ── Sanity check: server.py must not be empty (SD corruption guard) ──────────
BACKUP_PY="/home/pi/.rangetrack_server_backup.py"
if [ ! -s "$APP_DIR/server.py" ]; then
    echo "[$(date '+%H:%M:%S')] CRITICAL: server.py empty — SD card corruption detected" >> "$SERVER_LOG"

    # Layer 1: try git recovery (needs internet)
    cd /home/pi/Desktop/LaunchTracker2D 2>/dev/null
    git fetch origin Phase2 --quiet 2>>"$SERVER_LOG" && \
    git reset --hard origin/Phase2 2>>"$SERVER_LOG"

    if [ -s "$APP_DIR/server.py" ]; then
        echo "[$(date '+%H:%M:%S')] Recovered via git" >> "$SERVER_LOG"
        chown pi:pi "$APP_DIR/settings.json" "$APP_DIR/data_cache.json" 2>/dev/null

    # Layer 2: restore from local backup (works offline)
    elif [ -s "$BACKUP_PY" ]; then
        cp "$BACKUP_PY" "$APP_DIR/server.py"
        chown pi:pi "$APP_DIR/settings.json" "$APP_DIR/data_cache.json" 2>/dev/null
        echo "[$(date '+%H:%M:%S')] Recovered from local backup (offline)" >> "$SERVER_LOG"

    else
        echo "[$(date '+%H:%M:%S')] Recovery failed — no git, no backup. Manual intervention needed." >> "$SERVER_LOG"
        exit 1
    fi
fi

# After successful start, save backup so offline recovery always has latest version
_save_backup() {
    sleep 30
    if curl -s -o /dev/null http://localhost:5001/ --max-time 3 2>/dev/null; then
        cp "$APP_DIR/server.py" "$BACKUP_PY" 2>/dev/null
    fi
}
_save_backup &

# ── Start server ──────────────────────────────────────────────────────────────
cd "$APP_DIR" || exit 1
nohup python3 server.py >> "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

# ── Wait for server to be ready (up to 60s) ──────────────────────────────────
for i in $(seq 1 40); do
    if curl -s -o /dev/null "$APP_URL" --max-time 1 2>/dev/null; then
        break
    fi
    sleep 1.5
done

# ── Launch WebKit browser ─────────────────────────────────────────────────────
$WEBKIT "$APP_URL" &
BROWSER_PID=$!

# ── Supervisor loop ───────────────────────────────────────────────────────────
_HTTP_FAILS=0
while true; do
    sleep 15

    if curl -s -o /dev/null http://localhost:5001/ --max-time 3 2>/dev/null; then
        _HTTP_FAILS=0
        NEW_PID=$(fuser 5001/tcp 2>/dev/null | awk '{print $1}')
        [ -n "$NEW_PID" ] && SERVER_PID=$NEW_PID
    else
        _HTTP_FAILS=$((_HTTP_FAILS + 1))
        if [ "$_HTTP_FAILS" -lt 2 ]; then
            echo "[$(date '+%H:%M:%S')] Server not responding — waiting..." >> "$SERVER_LOG"
        elif [ -e "/tmp/rangetrack_update.lock" ]; then
            echo "[$(date '+%H:%M:%S')] Server down — update in progress" >> "$SERVER_LOG"
        else
            echo "[$(date '+%H:%M:%S')] Server crashed — restarting..." >> "$SERVER_LOG"
            fuser -k 5001/tcp 2>/dev/null || true
            sleep 1
            cd "$APP_DIR"
            nohup python3 server.py >> "$SERVER_LOG" 2>&1 &
            SERVER_PID=$!
            _HTTP_FAILS=0
            sleep 5
        fi
    fi

    # Relaunch browser if it died
    if ! kill -0 $BROWSER_PID 2>/dev/null; then
        $WEBKIT "$APP_URL" &
        BROWSER_PID=$!
    fi

    # Memory watchdog — restart WebKit before OOM freezes the whole Pi
    MEM_FREE=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
    if [ "$MEM_FREE" -lt 60 ]; then
        echo "[$(date '+%H:%M:%S')] Low memory (${MEM_FREE}MB) — restarting WebKit to prevent freeze" >> "$SERVER_LOG"
        kill $BROWSER_PID 2>/dev/null
        sleep 2
        $WEBKIT "$APP_URL" &
        BROWSER_PID=$!
    fi
done
