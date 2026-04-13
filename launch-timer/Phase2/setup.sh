#!/bin/bash
# RangeTrack OS — Fresh Pi Setup Script
# Run once on a fresh Raspberry Pi OS installation.
# Usage: bash setup.sh
#
# What this does:
#   1. Installs dependencies (python3, flask, requests, chromium)
#   2. Clones the repo (or updates if already present)
#   3. Prompts for timezone
#   4. Sets up autostart (server + chromium kiosk)
#   5. Sets up hourly auto-updater cron
#   6. Configures passwordless sudo for reboot
#   7. Installs unclutter (hides cursor)

set -e

REPO_URL="https://github.com/carsonmwolfe/LaunchTracker2D.git"
REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
BRANCH="Phase3"
SERVER_DIR="$REPO_DIR/launch-timer/Phase2"
LOG_FILE="/home/pi/setup.log"

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "=== RangeTrack OS Setup ==="

# ── 1. Dependencies ────────────────────────────────────────────────────────────
log "Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip chromium-browser xdotool git psmisc unclutter -qq
pip3 install flask requests --quiet
log "Dependencies installed"

# ── 2. Clone or update repo ────────────────────────────────────────────────────
if [ -d "$REPO_DIR/.git" ]; then
    log "Repo already exists — pulling latest..."
    cd "$REPO_DIR"
    git fetch origin "$BRANCH" --quiet
    git reset --hard "origin/$BRANCH"
else
    log "Cloning repo..."
    mkdir -p /home/pi/Desktop
    git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi

chmod +x "$SERVER_DIR/update.sh"
log "Repo ready at $REPO_DIR"

# ── 3. Timezone ────────────────────────────────────────────────────────────────
echo ""
echo "Select timezone:"
echo "  1) America/New_York      (Eastern)"
echo "  2) America/Chicago       (Central)"
echo "  3) America/Denver        (Mountain)"
echo "  4) America/Los_Angeles   (Pacific)"
echo "  5) America/Phoenix       (Arizona)"
echo "  6) Enter manually"
echo ""
read -rp "Choose [1-6]: " TZ_CHOICE
case "$TZ_CHOICE" in
    1) TZ_SET="America/New_York" ;;
    2) TZ_SET="America/Chicago" ;;
    3) TZ_SET="America/Denver" ;;
    4) TZ_SET="America/Los_Angeles" ;;
    5) TZ_SET="America/Phoenix" ;;
    6) read -rp "Enter timezone (e.g. Europe/London): " TZ_SET ;;
    *) TZ_SET="America/New_York" ;;
esac
sudo timedatectl set-timezone "$TZ_SET"
log "Timezone set to $TZ_SET"

# ── 4. Autostart ──────────────────────────────────────────────────────────────
log "Setting up autostart..."
AUTOSTART_DIR="/home/pi/.config/lxsession/LXDE-pi"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/autostart" << 'AUTOEOF'
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi

# Disable screen blanking
@xset s off
@xset -dpms
@xset s noblank

# Hide cursor
@unclutter -idle 0.1 -root

# Start RangeTrack server
@bash -c 'cd /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2 && nohup python3 server.py >> /home/pi/server.log 2>&1 &'

# Launch Chromium immediately with boot page — it auto-redirects when server is ready
@bash -c 'sleep 2 && chromium-browser --kiosk --noerrdialogs --disable-infobars --no-first-run file:///home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/static/boot.html'
AUTOEOF

log "Autostart configured"

# ── 5. Hourly updater cron ────────────────────────────────────────────────────
log "Setting up auto-updater cron..."
CRON_LINE="0 * * * * bash $SERVER_DIR/update.sh >> /home/pi/update.log 2>&1"
( crontab -l 2>/dev/null | grep -v "update.sh"; echo "$CRON_LINE" ) | crontab -
log "Cron installed — runs every hour"

# ── 6. Passwordless sudo for reboot ───────────────────────────────────────────
log "Configuring passwordless reboot..."
printf 'pi ALL=(ALL) NOPASSWD: /sbin/reboot\npi ALL=(ALL) NOPASSWD: /usr/bin/timedatectl\n' | sudo tee /etc/sudoers.d/rangetrack > /dev/null
log "Done"

# ── Done ──────────────────────────────────────────────────────────────────────
log ""
log "=== Setup complete — reboot to launch ==="
echo ""
echo "All done. Run: sudo reboot"
