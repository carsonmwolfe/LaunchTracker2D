#!/bin/bash
# LaunchTracker2D — One-time Pi setup script
# Run once on each new Pi: bash setup.sh
# Must be run from the repo root or Phase2 directory.

set -e

REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
PHASE2="$REPO_DIR/launch-timer/Phase2"
PASS_FILE="/home/pi/.rangetrack_gmail_pass"
BRANCH="Phase3"

echo ""
echo "========================================"
echo "  LAUNCHTRACKER2D — PI SETUP"
echo "========================================"
echo ""

# ── 1. Unit ID / hostname ─────────────────────────────────────────────────────
read -p "Enter Unit ID (e.g. CAPE-01, CUST-01): " UNIT_ID
UNIT_ID=$(echo "$UNIT_ID" | tr '[:lower:]' '[:upper:]' | tr ' ' '-')
if [ -z "$UNIT_ID" ]; then
  echo "ERROR: Unit ID cannot be empty."
  exit 1
fi

HOSTNAME=$(echo "rangetrack-$(echo $UNIT_ID | tr '[:upper:]' '[:lower:]')")
echo "Setting hostname to: $HOSTNAME"
echo "$HOSTNAME" | sudo tee /etc/hostname > /dev/null
sudo sed -i "s/127\.0\.1\.1.*/127.0.1.1\t$HOSTNAME/" /etc/hosts
sudo hostname "$HOSTNAME"

# ── 2. Gmail app password (yours — for sending health reports to yourself) ────
echo "Health reports are sent to rangetrack551@gmail.com (your account)."
read -s -p "Enter YOUR Gmail app password for rangetrack551@gmail.com: " GMAIL_PASS
echo ""
if [ -z "$GMAIL_PASS" ]; then
  echo "WARNING: No password entered — health emails will fail."
else
  echo "$GMAIL_PASS" > "$PASS_FILE"
  chmod 600 "$PASS_FILE"
  echo "Gmail password saved to $PASS_FILE"
fi

# ── 3. Write Unit ID to settings.json ────────────────────────────────────────
SETTINGS="$PHASE2/settings.json"
if [ -f "$SETTINGS" ]; then
  python3 -c "
import json
with open('$SETTINGS') as f:
    s = json.load(f)
s['unit_id'] = '$UNIT_ID'
with open('$SETTINGS', 'w') as f:
    json.dump(s, f)
print('Unit ID written to settings.json')
"
else
  echo "{\"brightness\": 40, \"temp_unit\": \"f\", \"site\": \"cape\", \"time_format\": \"utc\", \"unit_id\": \"$UNIT_ID\"}" > "$SETTINGS"
  echo "settings.json created with Unit ID: $UNIT_ID"
fi

# ── 4. Prevent data_cache.json git conflicts ──────────────────────────────────
cd "$REPO_DIR"
git update-index --assume-unchanged launch-timer/Phase2/data_cache.json 2>/dev/null && \
  echo "data_cache.json marked as assume-unchanged" || \
  echo "WARNING: Could not mark data_cache.json (git not ready?)"

# ── 5. Install Python dependencies ───────────────────────────────────────────
echo "Installing Python dependencies..."
pip3 install flask requests --quiet

# ── 6. Set up cron jobs ───────────────────────────────────────────────────────
echo "Setting up cron jobs..."
(crontab -l 2>/dev/null | grep -v 'rangetrack\|health.py\|update.sh\|server.py'; \
echo "# LaunchTracker2D"; \
echo "@reboot sleep 10 && cd $PHASE2 && nohup python3 server.py >> /home/pi/server.log 2>&1 &"; \
echo "@reboot sleep 12 && until curl -s http://localhost:5001 > /dev/null 2>&1; do sleep 1; done && sed -i 's/\"exited_cleanly\":false/\"exited_cleanly\":true/g;s/\"exit_type\":\"Crashed\"/\"exit_type\":\"Normal\"/g' /home/pi/.config/chromium/Default/Preferences 2>/dev/null && DISPLAY=:0 xset s off && DISPLAY=:0 xset -dpms && DISPLAY=:0 xset s noblank && DISPLAY=:0 chromium-browser --kiosk --noerrdialogs --disable-infobars --disable-features=TranslateUI --disable-component-update --check-for-update-interval=31536000 --password-store=basic http://localhost:5001 >> /home/pi/chromium.log 2>&1 &"; \
echo "0 * * * * $PHASE2/update.sh >> /home/pi/update.log 2>&1"; \
echo "0 8 * * * python3 $PHASE2/health.py digest >> /home/pi/health.log 2>&1"; \
echo "*/5 * * * * python3 $PHASE2/health.py check >> /home/pi/health.log 2>&1") | crontab -
echo "Cron jobs installed."

# ── 7. Log rotation ──────────────────────────────────────────────────────────
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/rangetrack > /dev/null <<'EOF'
/home/pi/server.log /home/pi/health.log /home/pi/update.log /home/pi/chromium.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    copytruncate
}
EOF
echo "Log rotation configured (weekly, keep 4 weeks)."

# ── 8. Configure git branch ───────────────────────────────────────────────────
cd "$REPO_DIR"
git fetch origin "$BRANCH" --quiet 2>/dev/null || true
git checkout "$BRANCH" 2>/dev/null || true
echo "Tracking branch: $BRANCH"

echo ""
echo "========================================"
echo "  SETUP COMPLETE"
echo "  Unit ID : $UNIT_ID"
echo "  Hostname: $HOSTNAME"
echo "  Reboot to start: sudo reboot"
echo "========================================"
echo ""
