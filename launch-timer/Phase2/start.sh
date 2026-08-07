#!/bin/bash
APP_DIR="/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2"
SERVER_LOG="/home/pi/server.log"
APP_URL="http://localhost:5001/"

export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/1000}

# Only one instance of start.sh should ever run
PIDFILE="/tmp/rangetrack_start.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "[$(date '+%H:%M:%S')] start.sh already running (PID $(cat "$PIDFILE")) — exiting" >> "$SERVER_LOG"
    exit 0
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

# Kill anything left from a previous run
pkill -f webkit_launch 2>/dev/null
pkill -f chromium 2>/dev/null
fuser -k 5001/tcp 2>/dev/null || true

# Corruption guard: if server.py is empty restore from backup, else bail
if [ ! -s "$APP_DIR/server.py" ]; then
    BACKUP="/home/pi/.rangetrack_server_backup.py"
    if [ -s "$BACKUP" ]; then
        cp "$BACKUP" "$APP_DIR/server.py"
        echo "[$(date '+%H:%M:%S')] server.py restored from backup" >> "$SERVER_LOG"
    else
        echo "[$(date '+%H:%M:%S')] FATAL: server.py missing and no backup" >> "$SERVER_LOG"
        exit 1
    fi
fi

cd "$APP_DIR" || exit 1
nohup python3 server.py >> "$SERVER_LOG" 2>&1 &

# Wait for server (up to 60s)
for i in $(seq 1 60); do
    curl -s -o /dev/null "$APP_URL" --max-time 1 2>/dev/null && break
    sleep 1
done

BROWSER_PIDFILE="/tmp/rangetrack_browser.pid"

# Choose browser: Chromium for Pis with enough RAM, WebKit2GTK for 512MB Pis
MEM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
CHROMIUM_BIN=$(command -v chromium-browser || command -v chromium 2>/dev/null)

# Proven GPU-accelerated Chromium flags — this is the exact config that ran
# smoothly on the 3B+ for months. --use-angle=gles + --ozone-platform=wayland
# are what enable GPU rendering; without them Chromium falls back to software.
CHROMIUM_FLAGS="--kiosk --no-memcheck --noerrdialogs --disable-infobars \
  --disable-features=ChromeWhatsNew,Translate --no-default-browser-check \
  --disable-background-networking --disable-session-crashed-bubble \
  --window-size=800,480 --disable-notifications --disable-popup-blocking \
  --no-first-run --use-angle=gles --ozone-platform=wayland \
  --password-store=basic --disable-renderer-accessibility \
  --disable-extensions --disable-sync --disable-component-update \
  --renderer-process-limit=1"

launch_browser() {
    if [ "$MEM_MB" -gt 700 ] && [ -n "$CHROMIUM_BIN" ]; then
        echo "[$(date '+%H:%M:%S')] Using Chromium GPU (${MEM_MB}MB RAM)" >> "$SERVER_LOG"
        rm -f /home/pi/.config/chromium/Singleton* 2>/dev/null
        "$CHROMIUM_BIN" $CHROMIUM_FLAGS --app="$APP_URL" &
    else
        echo "[$(date '+%H:%M:%S')] Using WebKit2GTK (${MEM_MB}MB RAM)" >> "$SERVER_LOG"
        python3 "$APP_DIR/webkit_launch.py" "$APP_URL" &
    fi
    echo $! > "$BROWSER_PIDFILE"
    echo $!
}

BROWSER_PID=$(launch_browser)

# Supervisor: restart server or browser if either crashes
while true; do
    sleep 15

    if ! curl -s -o /dev/null "$APP_URL" --max-time 20 2>/dev/null; then
        if [ -e "/tmp/rangetrack_update.lock" ]; then
            echo "[$(date '+%H:%M:%S')] Server down — update in progress, waiting" >> "$SERVER_LOG"
        else
            echo "[$(date '+%H:%M:%S')] Server down — restarting" >> "$SERVER_LOG"
            fuser -k 5001/tcp 2>/dev/null || true
            nohup python3 server.py >> "$SERVER_LOG" 2>&1 &
            sleep 5
        fi
    fi

    # Check PID file first — update.sh may have already restarted the browser
    FILE_PID=$(cat "$BROWSER_PIDFILE" 2>/dev/null)
    if [ -n "$FILE_PID" ] && kill -0 "$FILE_PID" 2>/dev/null; then
        BROWSER_PID="$FILE_PID"
    elif ! kill -0 "$BROWSER_PID" 2>/dev/null; then
        BROWSER_PID=$(launch_browser)
        echo "[$(date '+%H:%M:%S')] Browser restarted (PID $BROWSER_PID)" >> "$SERVER_LOG"
    fi
done
