#!/bin/bash
# Auto-updater: checks for new commits on GitHub once per hour via cron.
# If changes are found, pulls, restarts the server, and sends a text message.
#
# SETUP (run once on Pi):
#   chmod +x /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh
#   crontab -e
#   Add this line:
#   0 * * * * /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh >> /home/pi/update.log 2>&1

REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
BRANCH="Phase2"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"
SMS_TO="rangetrack551@gmail.com"
FROM="rangetrack551@gmail.com"
GMAIL_PASS=$(cat /home/pi/.rangetrack_gmail_pass 2>/dev/null)

send_text() {
    python3 - <<EOF
import smtplib
from email.mime.text import MIMEText
msg = MIMEText("$1")
msg['Subject'] = 'RangeTrack OS'
msg['From']    = '$FROM'
msg['To']      = '$SMS_TO'
try:
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login('$FROM', '$GMAIL_PASS')
    s.sendmail('$FROM', '$SMS_TO', msg.as_string())
    s.quit()
except Exception as e:
    print(f'Email error: {e}')
EOF
}

cd "$REPO_DIR" || { echo "$LOG_PREFIX ERROR: repo dir not found"; exit 1; }

# Stash any local changes to settings/cache so pull doesn't conflict
git stash -- data_cache.json settings.json 2>/dev/null

# Fetch remote without merging
git fetch origin "$BRANCH" --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$LOG_PREFIX Already up to date ($LOCAL)"
    exit 0
fi

echo "$LOG_PREFIX New commits found — pulling ($LOCAL → $REMOTE)"
git pull origin "$BRANCH" --quiet

# Restore stashed local files
git stash pop 2>/dev/null

# Restart server
echo "$LOG_PREFIX Restarting server..."
pkill -f "python3 server.py" 2>/dev/null
sleep 2
cd launch-timer/Phase2
nohup python3 server.py >> /home/pi/server.log 2>&1 &
SERVER_PID=$!
echo "$LOG_PREFIX Server restarted (PID $SERVER_PID)"

# Send text notification
SHORT=$(git log -1 --pretty="%s" 2>/dev/null)
TIME=$(date '+%I:%M %p')
send_text "RangeTrack OS updated at $TIME — $SHORT"
echo "$LOG_PREFIX Text sent to $SMS_TO"
