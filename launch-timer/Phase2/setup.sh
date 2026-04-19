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
sudo apt-get install -y python3 python3-pip chromium xdotool git psmisc swaybg -qq
# unclutter not always available, skip if missing
sudo apt-get install -y unclutter -qq 2>/dev/null || true
pip3 install flask requests --quiet --break-system-packages 2>/dev/null || pip3 install flask requests --quiet
log "Dependencies installed (chromium pkg: $CHROMIUM_PKG)"

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

# Detect compositor: newer Pi OS (Bookworm/Trixie) uses labwc (Wayland),
# older uses lxsession (LXDE). Write to all locations to cover both.

# labwc (Wayland — newer Pi OS Bookworm/Trixie)
if [ -d "/home/pi/.config/labwc" ] || command -v labwc &>/dev/null; then
    mkdir -p /home/pi/.config/labwc
    cat > /home/pi/.config/labwc/autostart << LABWCEOF
swaybg -c '#060a10' &
bash $SERVER_DIR/start.sh &
(sleep 5 && DESKTOP_SESSION=rpd-labwc pcmanfm --desktop --reconfigure) &
LABWCEOF
    log "labwc autostart configured (swaybg wallpaper + start.sh)"

    # Configure wf-panel-pi to autohide — do NOT remove it, removing breaks the session
    mkdir -p /home/pi/.config
    cat > /home/pi/.config/wf-panel-pi.ini << WPEOF
[panel]
autohide=1
WPEOF
    log "wf-panel-pi set to autohide"

    # Wallpaper for labwc/rpd-labwc session (pcmanfm fallback)
    for SESSION in rpd-labwc LXDE-pi; do
        mkdir -p "/home/pi/.config/pcmanfm/$SESSION"
        cat > "/home/pi/.config/pcmanfm/$SESSION/desktop-items-0.conf" << PCEOF
[*]
wallpaper_mode=color
wallpaper_common=1
desktop_bg=#060a10
desktop_fg=#060a10
desktop_shadow=#060a10
show_documents=0
show_trash=0
show_mounts=0
PCEOF
    done
    log "Wallpaper set to #060a10 (labwc sessions)"
fi

# lxsession (X11 — older Pi OS) — write to both session names
for SESSION in LXDE-pi rpd-x; do
    mkdir -p "/home/pi/.config/lxsession/$SESSION"
    echo "@bash $SERVER_DIR/start.sh" > "/home/pi/.config/lxsession/$SESSION/autostart"
done
log "lxsession autostart configured (LXDE-pi + rpd-x)"

# Desktop wallpaper for lxsession
mkdir -p /home/pi/.config/pcmanfm/LXDE-pi
cat > /home/pi/.config/pcmanfm/LXDE-pi/desktop-items-0.conf << PCEOF
[*]
wallpaper_mode=color
wallpaper_common=1
desktop_bg=#060a10
desktop_fg=#060a10
desktop_shadow=#060a10
show_documents=0
show_trash=0
show_mounts=0
PCEOF
log "Wallpaper set to dark (#060a10)"

# Hide taskbar for lxsession
mkdir -p /home/pi/.config/lxpanel/LXDE-pi/panels
if [ ! -f /home/pi/.config/lxpanel/LXDE-pi/panels/panel ]; then
    cat > /home/pi/.config/lxpanel/LXDE-pi/panels/panel << PEOF
Global {
  edge=bottom
  autohide=1
  heightwhenhidden=0
  height=28
}
PEOF
fi
log "Taskbar set to auto-hide"

log "Autostart configured"

# ── 5. Hourly updater cron ────────────────────────────────────────────────────
log "Setting up auto-updater cron..."
CRON_LINE="0 * * * * bash $SERVER_DIR/update.sh >> /home/pi/update.log 2>&1"
( crontab -l 2>/dev/null | grep -v "update.sh"; echo "$CRON_LINE" ) | crontab -
log "Cron installed — runs every hour"

# ── 6. Remove boot splash ─────────────────────────────────────────────────────
log "Removing boot splash..."
if [ -f /boot/firmware/cmdline.txt ]; then
    sudo sed -i 's/ splash//g; s/splash //g' /boot/firmware/cmdline.txt
    log "Splash removed from /boot/firmware/cmdline.txt"
elif [ -f /boot/cmdline.txt ]; then
    sudo sed -i 's/ splash//g; s/splash //g' /boot/cmdline.txt
    log "Splash removed from /boot/cmdline.txt"
fi

# ── 7. Passwordless sudo for reboot ───────────────────────────────────────────
log "Configuring passwordless reboot..."
printf 'pi ALL=(ALL) NOPASSWD: /sbin/reboot\npi ALL=(ALL) NOPASSWD: /usr/bin/timedatectl\n' | sudo tee /etc/sudoers.d/rangetrack > /dev/null
log "Done"

# ── Done ──────────────────────────────────────────────────────────────────────
log ""
log "=== Setup complete — reboot to launch ==="
echo ""
echo "All done. Run: sudo reboot"
