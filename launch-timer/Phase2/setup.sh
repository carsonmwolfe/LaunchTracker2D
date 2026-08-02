#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# RangeTrack — THE RECIPE.
# Turns a FRESH "Raspberry Pi OS Lite (64-bit)" flash into a finished unit.
# Run ONCE on a fresh card. Everything a unit needs is here — nothing is ever
# hand-configured on a unit. To change a unit, change this recipe and re-image.
#
#   Usage:  bash setup.sh
#
# Packages/deps below were taken from a real working unit, not guessed.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_URL="https://github.com/carsonmwolfe/LaunchTracker2D.git"
BRANCH="release"
APP_DIR="/home/pi/Desktop/LaunchTracker2D"
PHASE2="$APP_DIR/launch-timer/Phase2"
WIFI_COUNTRY="US"
log(){ echo "[recipe] $*"; }

# 1. PACKAGES — the minimal set the app actually uses (verified from a live unit)
log "Installing packages..."
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    labwc \
    python3-flask python3-requests python3-gi gir1.2-webkit2-4.1 gir1.2-nm-1.0 \
    network-manager watchdog iw git curl

# 2. APP — clone once; it auto-updates itself over WiFi after this
log "Installing the app..."
if [ ! -d "$APP_DIR/.git" ]; then
    sudo -u pi git clone "$REPO_URL" "$APP_DIR"
fi
sudo -u pi git -C "$APP_DIR" checkout "$BRANCH"

# 3. PASSWORDLESS SUDO — appliance; provisioning + self-management must be
#    non-interactive. Validated before install so a typo can't lock out sudo.
echo 'pi ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/rangetrack.tmp >/dev/null
sudo visudo -c -f /etc/sudoers.d/rangetrack.tmp >/dev/null \
    && sudo mv /etc/sudoers.d/rangetrack.tmp /etc/sudoers.d/rangetrack \
    && sudo chmod 440 /etc/sudoers.d/rangetrack

# 4. FLASK SERVER — systemd service, restarts forever if it ever dies
sudo tee /etc/systemd/system/rangetrack-server.service >/dev/null <<UNIT
[Unit]
Description=RangeTrack countdown server
After=network.target
[Service]
User=pi
WorkingDirectory=$PHASE2
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=3
Nice=-10
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl enable rangetrack-server

# 5. KIOSK BROWSER — labwc autostart launches start.sh (waits for the server,
#    then the fullscreen browser). Boot straight to the app, no desktop chrome.
mkdir -p /home/pi/.config/labwc
cat > /home/pi/.config/labwc/autostart <<EOF
bash $PHASE2/start.sh &
(sleep 3 && pkill -f 'wf-panel-pi') &
EOF

# 6. AUTOLOGIN to the desktop session so the kiosk starts on boot, no login
sudo raspi-config nonint do_boot_behaviour B4

# 7. HARDWARE WATCHDOG — if the whole system ever freezes, it auto-reboots
sudo sed -i 's/^#*RuntimeWatchdogSec=.*/RuntimeWatchdogSec=15/' /etc/systemd/system.conf
grep -q '^dtparam=watchdog=on' /boot/firmware/config.txt \
    || echo 'dtparam=watchdog=on' | sudo tee -a /boot/firmware/config.txt >/dev/null

# 8. WIFI — country enables 5GHz; power-save off (persisted) stops random drops
sudo raspi-config nonint do_wifi_country "$WIFI_COUNTRY"
sudo tee /etc/NetworkManager/dispatcher.d/99-wifi-powersave-off >/dev/null <<'PS'
#!/bin/sh
case "$1" in wlan*) [ "$2" = "up" ] && /usr/sbin/iw dev "$1" set power_save off ;; esac
PS
sudo chmod 755 /etc/NetworkManager/dispatcher.d/99-wifi-powersave-off

# 9. FEWER SD WRITES (top cause of corruption): no swap; logs + tmp in RAM
sudo systemctl disable --now dphys-swapfile 2>/dev/null || true
grep -q ' /tmp ' /etc/fstab     || echo 'tmpfs /tmp     tmpfs defaults,noatime,size=64M 0 0' | sudo tee -a /etc/fstab >/dev/null
grep -q ' /var/log ' /etc/fstab || echo 'tmpfs /var/log tmpfs defaults,noatime,size=32M 0 0' | sudo tee -a /etc/fstab >/dev/null

# 10. SELF-MAINTENANCE — hourly update check + nightly 4am reboot (clears any
#     wedged state). Flask is watched by systemd, so no health.py cron needed.
( crontab -u pi -l 2>/dev/null | grep -v update.sh | grep -v 'nightly reboot'; \
  echo "0 * * * * bash $PHASE2/update.sh >> /home/pi/update.log 2>&1"; \
  echo "0 4 * * * sudo /sbin/reboot   # rangetrack nightly reboot" ) | sudo crontab -u pi -

# 11. QUIET BOOT — no rainbow, penguin, cursor, or scrolling text (idempotent)
grep -q 'logo.nologo' /boot/firmware/cmdline.txt || sudo sed -i \
    's/console=tty1/console=tty3/; s/$/ quiet loglevel=0 logo.nologo vt.global_cursor_default=0/' \
    /boot/firmware/cmdline.txt
grep -q 'disable_splash=1' /boot/firmware/config.txt \
    || echo 'disable_splash=1' | sudo tee -a /boot/firmware/config.txt >/dev/null

log "Done. Reboot to finish:  sudo reboot"
# NOTE (v2 hardening, not yet enabled): read-only overlay for full power-cut
# immunity. It must coexist with auto-updates (needs a small persistent area for
# wifi/settings), so it's added and tested after this base is proven.
