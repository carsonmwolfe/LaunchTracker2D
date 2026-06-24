#!/bin/bash
# RangeTrack OS — Startup & Supervisor
# Handles server start, health check, Chromium launch, and crash recovery.

APP_DIR="/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2"
SERVER_LOG="/home/pi/server.log"
# Support both chromium-browser (older Pi OS) and chromium (newer)
if [ -x "/usr/bin/chromium-browser" ]; then
    CHROMIUM="/usr/bin/chromium-browser"
else
    CHROMIUM="/usr/bin/chromium"
fi
APP_URL="http://localhost:5001/"
BOOT_URL="file://$APP_DIR/static/boot.html"

CHROMIUM_FLAGS="--kiosk --no-memcheck --noerrdialogs --disable-infobars \
  --disable-features=ChromeWhatsNew --no-default-browser-check \
  --disable-background-networking --disable-session-crashed-bubble \
  --enable-virtual-keyboard --window-size=800,480 \
  --disable-notifications --disable-popup-blocking \
  --no-first-run --use-angle=gles \
  --ozone-platform=wayland \
  --password-store=basic \
  --disable-renderer-accessibility \
  --enable-wayland-ime \
  --disable-extensions \
  --disable-sync \
  --disable-component-update \
  --renderer-process-limit=1 \
  --js-flags=--max-old-space-size=192"

# ── Ensure DISPLAY / WAYLAND_DISPLAY are set ─────────────────────────────────
export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

# ── Kill any stale Chromium + singleton lock ──────────────────────────────────
pkill -f chromium 2>/dev/null; sleep 2
rm -f /home/pi/.config/chromium/SingletonLock \
      /home/pi/.config/chromium/SingletonCookie \
      /home/pi/.config/chromium/SingletonSocket 2>/dev/null

# ── Clear screen to dark ──────────────────────────────────────────────────────
xsetroot -solid '#060a10' 2>/dev/null || true

# ── Kill anything already on port 5001 ───────────────────────────────────────
fuser -k 5001/tcp 2>/dev/null || kill $(fuser 5001/tcp 2>/dev/null) 2>/dev/null || true
sleep 1

# ── Start server ──────────────────────────────────────────────────────────────
cd "$APP_DIR" || exit 1
nohup python3 server.py >> "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

# ── Launch Chromium immediately to boot.html (hides desktop while server loads) ──
"$CHROMIUM" $CHROMIUM_FLAGS "$BOOT_URL" &
CHROMIUM_PID=$!

# ── Wait for server to be ready (max 30s) — boot.html will redirect when ready ──
for i in $(seq 1 20); do
    if curl -s -o /dev/null "$APP_URL" --max-time 1 2>/dev/null; then
        break
    fi
    sleep 1.5
done

# ── Supervisor loop — restart server if it crashes ───────────────────────────
_HTTP_FAILS=0
while true; do
    sleep 15

    # Use HTTP health check — more reliable than PID tracking across restarts
    if curl -s -o /dev/null http://localhost:5001/ --max-time 3 2>/dev/null; then
        _HTTP_FAILS=0
        # Re-acquire PID in case update.sh or health.py restarted the server
        NEW_PID=$(fuser 5001/tcp 2>/dev/null | awk '{print $1}')
        [ -n "$NEW_PID" ] && SERVER_PID=$NEW_PID
    else
        _HTTP_FAILS=$((_HTTP_FAILS + 1))
        if [ "$_HTTP_FAILS" -lt 2 ]; then
            echo "[$(date '+%H:%M:%S')] Server not responding (attempt $_HTTP_FAILS) — waiting..." >> "$SERVER_LOG"
        elif [ -e "/tmp/rangetrack_update.lock" ]; then
            echo "[$(date '+%H:%M:%S')] Server down but update in progress — skipping restart" >> "$SERVER_LOG"
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

    # If Chromium died too, relaunch it
    if ! kill -0 $CHROMIUM_PID 2>/dev/null; then
        rm -f /home/pi/.config/chromium/SingletonLock \
              /home/pi/.config/chromium/SingletonCookie \
              /home/pi/.config/chromium/SingletonSocket 2>/dev/null
        "$CHROMIUM" $CHROMIUM_FLAGS "$APP_URL" &
        CHROMIUM_PID=$!
    fi
done
