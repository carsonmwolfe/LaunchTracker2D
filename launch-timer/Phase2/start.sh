#!/bin/bash
# Launches the kiosk browser only. Flask is owned by systemd
# (rangetrack-server.service, Restart=always), so this script no longer starts
# or supervises the server — it just waits for it and runs the browser.
APP_DIR="/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2"
SERVER_LOG="/home/pi/server.log"
APP_URL="http://localhost:5001/"

export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/1000}

# Only one instance of start.sh should ever run
PIDFILE="/tmp/rangetrack_start.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "[$(date '+%H:%M:%S')] start.sh already running — exiting" >> "$SERVER_LOG"
    exit 0
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

# Clean up any leftover browser from a previous run (do NOT touch the server)
pkill -f webkit_launch 2>/dev/null
pkill -f chromium 2>/dev/null

# Wait for the systemd-managed server to respond (up to 60s)
for i in $(seq 1 60); do
    curl -s -o /dev/null "$APP_URL" --max-time 1 2>/dev/null && break
    sleep 1
done

BROWSER_PIDFILE="/tmp/rangetrack_browser.pid"

# Browser choice is a real hardware trade-off, not gratuitous complexity:
# Chromium is GPU-accelerated and smooth but needs ~1GB RAM; WebKit is light
# enough for 512MB but renders in software (laggy on the animation). So: Chromium
# where there's RAM for it, WebKit as the fallback for 512MB units.
MEM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
CHROMIUM_BIN=$(command -v chromium-browser || command -v chromium 2>/dev/null)
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
        echo "[$(date '+%H:%M:%S')] Launching Chromium GPU (${MEM_MB}MB)" >> "$SERVER_LOG"
        rm -f /home/pi/.config/chromium/Singleton* 2>/dev/null
        "$CHROMIUM_BIN" $CHROMIUM_FLAGS --app="$APP_URL" &
    else
        echo "[$(date '+%H:%M:%S')] Launching WebKit (${MEM_MB}MB)" >> "$SERVER_LOG"
        python3 "$APP_DIR/webkit_launch.py" "$APP_URL" &
    fi
    echo $! > "$BROWSER_PIDFILE"
    echo $!
}

BROWSER_PID=$(launch_browser)

# Supervisor: relaunch the browser if it dies (systemd handles the server)
while true; do
    sleep 15
    FILE_PID=$(cat "$BROWSER_PIDFILE" 2>/dev/null)
    if [ -n "$FILE_PID" ] && kill -0 "$FILE_PID" 2>/dev/null; then
        BROWSER_PID="$FILE_PID"
    elif ! kill -0 "$BROWSER_PID" 2>/dev/null; then
        BROWSER_PID=$(launch_browser)
        echo "[$(date '+%H:%M:%S')] Browser restarted (PID $BROWSER_PID)" >> "$SERVER_LOG"
    fi
done
