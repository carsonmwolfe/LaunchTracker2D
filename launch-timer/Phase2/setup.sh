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
#   5. Sets up wallpaper and hides taskbar
#   6. Removes boot splash
#   7. Sets up hourly auto-updater cron
#   8. Configures passwordless sudo for reboot
#   9. Installs unclutter (hides cursor)

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
sudo apt-get install -y python3 python3-pip chromium xdotool git psmisc gir1.2-webkit2-4.1 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-nm-1.0 -qq
sudo apt-get install -y unclutter -qq 2>/dev/null || true
pip3 install flask requests --quiet --break-system-packages 2>/dev/null || pip3 install flask requests --quiet
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
chmod +x "$SERVER_DIR/start.sh"
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
read -rp "Choose [1-6]: " TZ_CHOICE </dev/tty
case "$TZ_CHOICE" in
    1) TZ_SET="America/New_York" ;;
    2) TZ_SET="America/Chicago" ;;
    3) TZ_SET="America/Denver" ;;
    4) TZ_SET="America/Los_Angeles" ;;
    5) TZ_SET="America/Phoenix" ;;
    6) read -rp "Enter timezone (e.g. Europe/London): " TZ_SET </dev/tty ;;
    *) TZ_SET="America/New_York" ;;
esac
sudo timedatectl set-timezone "$TZ_SET"
log "Timezone set to $TZ_SET"

# ── 4. Autostart ──────────────────────────────────────────────────────────────
log "Setting up autostart..."

# labwc (Wayland — newer Pi OS Bookworm/Trixie)
if [ -d "/home/pi/.config/labwc" ] || command -v labwc &>/dev/null; then
    mkdir -p /home/pi/.config/labwc
    cat > /home/pi/.config/labwc/autostart << LABWCEOF
bash $SERVER_DIR/start.sh &
(sleep 3 && pkill -f 'lwrespawn.*wf-panel' && pkill -f 'wf-panel-pi') &
(sleep 1 && pkill -f 'gnome-keyring-daemon') &
LABWCEOF
    log "labwc autostart configured"
fi

# lxsession (X11 — older Pi OS)
for SESSION in LXDE-pi rpd-x; do
    mkdir -p "/home/pi/.config/lxsession/$SESSION"
    echo "@bash $SERVER_DIR/start.sh" > "/home/pi/.config/lxsession/$SESSION/autostart"
done
log "lxsession autostart configured"

# ── 5. Wallpaper ──────────────────────────────────────────────────────────────
log "Setting wallpaper..."

# 'default' is the profile pcmanfm reads on Pi OS Trixie (Wayland/labwc)
mkdir -p /home/pi/.config/pcmanfm/default
cat > /home/pi/.config/pcmanfm/default/desktop-items-0.conf << PCEOF
[*]
wallpaper_mode=4
wallpaper=$SERVER_DIR/static/assets/BootLOGO.png
wallpaper_common=1
desktop_bg=#060a10
desktop_fg=#060a10
desktop_shadow=#060a10
show_documents=0
show_trash=0
show_mounts=0
show_desktop=0
PCEOF

# rpd-labwc and LXDE-pi profiles as fallback
for SESSION in rpd-labwc LXDE-pi; do
    mkdir -p "/home/pi/.config/pcmanfm/$SESSION"
    cat > "/home/pi/.config/pcmanfm/$SESSION/desktop-items-0.conf" << PCEOF
[*]
wallpaper_mode=4
wallpaper=$SERVER_DIR/static/assets/BootLOGO.png
wallpaper_common=1
desktop_bg=#060a10
desktop_fg=#060a10
desktop_shadow=#060a10
show_documents=0
show_trash=0
show_mounts=0
show_desktop=0
PCEOF
done
log "Wallpaper configured"

# Hide desktop icons (repo folder etc)
echo "LaunchTracker2D" > /home/pi/Desktop/.hidden

# ── Disable gnome-keyring (prevents "choose password" dialog on first boot) ───
log "Disabling gnome-keyring..."
mkdir -p /home/pi/.config/autostart
for KR in gnome-keyring-secrets gnome-keyring-ssh gnome-keyring-pkcs11 gnome-keyring-gpg; do
    cat > /home/pi/.config/autostart/${KR}.desktop << KREOF
[Desktop Entry]
Type=Application
Hidden=true
KREOF
done
log "gnome-keyring disabled"

# ── 6. Hide taskbar (lxsession only — labwc taskbar killed via autostart) ──────
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

# ── 7. Remove boot splash ──────────────────────────────────────────────────────
log "Removing boot splash..."
if [ -f /boot/firmware/cmdline.txt ]; then
    sudo sed -i 's/ splash//g; s/splash //g' /boot/firmware/cmdline.txt
    log "Splash removed from /boot/firmware/cmdline.txt"
elif [ -f /boot/cmdline.txt ]; then
    sudo sed -i 's/ splash//g; s/splash //g' /boot/cmdline.txt
    log "Splash removed from /boot/cmdline.txt"
fi

# ── 7b. Suppress Chromium low-RAM warning dialog (Pi 3 A+ / 512MB) ────────────
# The Pi OS chromium wrapper shows a zenity dialog if RAM < 1GB before launch.
# On a kiosk with no keyboard this blocks startup permanently — patch it out.
if [ -f /usr/bin/chromium ]; then
    if grep -qi 'memory\|zenity\|1024\|512' /usr/bin/chromium 2>/dev/null; then
        sudo sed -i '/zenity/d; /low.mem\|less.than.*[Mm][Bb]\|insufficient/Id' /usr/bin/chromium 2>/dev/null && \
            log "Chromium low-RAM dialog patched out" || log "Chromium patch skipped (already clean)"
    fi
fi

# ── 7c. Low-RAM optimisations (safe on all Pi models, beneficial on 512MB) ────
log "Applying low-RAM optimisations..."

# Reduce GPU memory reservation to 16MB (we run headless-ish, don't need much)
CONFIG_FILE="/boot/firmware/config.txt"
[ -f "$CONFIG_FILE" ] || CONFIG_FILE="/boot/config.txt"
if ! grep -q "^gpu_mem=16" "$CONFIG_FILE" 2>/dev/null; then
    sudo sed -i '/^gpu_mem=/d' "$CONFIG_FILE"
    echo "gpu_mem=16" | sudo tee -a "$CONFIG_FILE" > /dev/null
    log "GPU memory set to 16MB"
fi

# Increase swap to 512MB (default is 100MB — not enough with Chromium on 512MB RAM)
if [ -f /etc/dphys-swapfile ]; then
    sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
    sudo dphys-swapfile setup > /dev/null 2>&1
    sudo dphys-swapfile swapon > /dev/null 2>&1
    log "Swap set to 512MB"
fi

# ── 8. Cron jobs ─────────────────────────────────────────────────────────────
log "Setting up cron jobs..."
( crontab -l 2>/dev/null | grep -v "update.sh" | grep -v "health.py"; \
  echo "0 * * * * bash $SERVER_DIR/update.sh >> /home/pi/update.log 2>&1"; \
  echo "*/5 * * * * python3 $SERVER_DIR/health.py >> /home/pi/health.log 2>&1" \
) | crontab -
log "Cron installed — updater hourly, health check every 5min"

# ── 9. Passwordless sudo for reboot ───────────────────────────────────────────
log "Configuring passwordless reboot..."
printf 'pi ALL=(ALL) NOPASSWD: /sbin/reboot\npi ALL=(ALL) NOPASSWD: /usr/bin/timedatectl\npi ALL=(ALL) NOPASSWD: /usr/bin/nmcli\npi ALL=(ALL) NOPASSWD: /usr/sbin/ifconfig\npi ALL=(ALL) NOPASSWD: /usr/sbin/iwlist\n' | sudo tee /etc/sudoers.d/rangetrack > /dev/null
log "Done"

# ── Done ──────────────────────────────────────────────────────────────────────
log ""
log "=== Setup complete — reboot to launch ==="
echo ""
echo "All done. Run: sudo reboot"
