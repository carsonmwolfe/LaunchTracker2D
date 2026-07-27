#!/bin/bash
APP_DIR="/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2"
SERVER_LOG="/home/pi/server.log"
APP_URL="http://localhost:5001/"

export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

# Kill anything left from a previous run
pkill -f webkit_launch 2>/dev/null
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

# Start server
cd "$APP_DIR" || exit 1
nohup python3 server.py >> "$SERVER_LOG" 2>&1 &

# Wait for server (up to 60s)
for i in $(seq 1 60); do
    curl -s -o /dev/null "$APP_URL" --max-time 1 2>/dev/null && break
    sleep 1
done

# Launch browser
python3 "$APP_DIR/webkit_launch.py" "$APP_URL" &
BROWSER_PID=$!

# Supervisor: restart server or browser if either crashes
while true; do
    sleep 15

    if ! curl -s -o /dev/null "$APP_URL" --max-time 3 2>/dev/null; then
        if [ -e "/tmp/rangetrack_update.lock" ]; then
            echo "[$(date '+%H:%M:%S')] Server down — update in progress, waiting" >> "$SERVER_LOG"
        else
            echo "[$(date '+%H:%M:%S')] Server down — restarting" >> "$SERVER_LOG"
            fuser -k 5001/tcp 2>/dev/null || true
            nohup python3 server.py >> "$SERVER_LOG" 2>&1 &
            sleep 5
        fi
    fi

    if ! kill -0 $BROWSER_PID 2>/dev/null; then
        python3 "$APP_DIR/webkit_launch.py" "$APP_URL" &
        BROWSER_PID=$!
    fi
done
