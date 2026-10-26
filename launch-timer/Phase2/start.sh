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

if [ "$MEM_MB" -gt 700 ] && [ -n "$CHROMIUM_BIN" ]; then
    USING_CHROMIUM=1
else
    USING_CHROMIUM=0
fi

# Browser output, overwritten on every launch so it can't grow without bound.
BROWSER_LOG="/home/pi/browser.log"

# Starts the browser and writes its PID to $BROWSER_PIDFILE. Prints nothing and
# must never be called as $(launch_browser): command substitution waits until
# every writer closes the pipe, and the backgrounded browser inherits it, so the
# caller blocks for as long as the browser lives. That is how this supervisor
# used to sit in pipe_read from boot and never run a single loop iteration.
launch_browser() {
    if [ "$USING_CHROMIUM" -eq 1 ]; then
        echo "[$(date '+%H:%M:%S')] Launching Chromium GPU (${MEM_MB}MB)" >> "$SERVER_LOG"
        rm -f /home/pi/.config/chromium/Singleton* 2>/dev/null
        "$CHROMIUM_BIN" $CHROMIUM_FLAGS --app="$APP_URL" > "$BROWSER_LOG" 2>&1 < /dev/null &
    else
        echo "[$(date '+%H:%M:%S')] Launching WebKit (${MEM_MB}MB)" >> "$SERVER_LOG"
        python3 "$APP_DIR/webkit_launch.py" "$APP_URL" > "$BROWSER_LOG" 2>&1 < /dev/null &
    fi
    echo $! > "$BROWSER_PIDFILE"
}

# Counts live renderer processes. A live browser PID does not mean the screen
# works: the renderer is a separate child, it is the biggest process, and the OOM
# killer takes it first while the parent keeps running with a frozen window.
# Patterns are anchored to the process itself so that no shell whose arguments
# merely mention the name can match (pgrep -f does match such shells).
renderer_count() {
    if [ "$USING_CHROMIUM" -eq 1 ]; then
        ps -eo args --no-headers | grep -cE '^/usr/lib/chromium[^ ]*/chromium[^ ]* --type=renderer'
    else
        ps -eo comm --no-headers | grep -c '^WebKitWebProc'
    fi
}

launch_browser
BROWSER_PID=$(cat "$BROWSER_PIDFILE" 2>/dev/null)
MISSING_RENDERER=0

# Supervisor: relaunch the browser if it dies or loses its renderer
# (systemd handles the server)
while true; do
    sleep 15
    FILE_PID=$(cat "$BROWSER_PIDFILE" 2>/dev/null)
    if [ -n "$FILE_PID" ] && kill -0 "$FILE_PID" 2>/dev/null; then
        BROWSER_PID="$FILE_PID"
    elif ! kill -0 "$BROWSER_PID" 2>/dev/null; then
        launch_browser
        BROWSER_PID=$(cat "$BROWSER_PIDFILE" 2>/dev/null)
        MISSING_RENDERER=0
        echo "[$(date '+%H:%M:%S')] Browser restarted (PID $BROWSER_PID)" >> "$SERVER_LOG"
        continue
    fi

    if [ "$(renderer_count)" -eq 0 ]; then
        MISSING_RENDERER=$((MISSING_RENDERER + 1))
    else
        MISSING_RENDERER=0
    fi
    # Two misses in a row (~30s) so a browser that is still starting up is left alone.
    if [ "$MISSING_RENDERER" -ge 2 ]; then
        echo "[$(date '+%H:%M:%S')] Renderer gone (PID $BROWSER_PID alive) — restarting browser" >> "$SERVER_LOG"
        kill "$BROWSER_PID" 2>/dev/null
        sleep 3
        kill -9 "$BROWSER_PID" 2>/dev/null
        launch_browser
        BROWSER_PID=$(cat "$BROWSER_PIDFILE" 2>/dev/null)
        MISSING_RENDERER=0
    fi
done
