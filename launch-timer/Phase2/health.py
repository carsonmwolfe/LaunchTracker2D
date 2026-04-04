#!/usr/bin/env python3
"""
RangeTrack OS — Health Monitor
Handles both daily digest and immediate alerting.

Usage:
    python3 health.py digest   — send daily health report
    python3 health.py check    — check for alert conditions and send if triggered

Cron setup (run: crontab -e on Pi):
    0 8 * * * python3 /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/health.py digest >> /home/pi/health.log 2>&1
    */5 * * * * python3 /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/health.py check >> /home/pi/health.log 2>&1
"""

import smtplib
import sys
import os
import subprocess
import time
import json
from email.mime.text import MIMEText
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
UNIT_ID       = 'Unit-001'   # Change per Pi when shipping
FROM          = 'rangetrack551@gmail.com'
TO            = 'rangetrack551@gmail.com'
PASS_FILE     = '/home/pi/.rangetrack_gmail_pass'
SERVER_SCRIPT = 'server.py'
DATA_CACHE    = '/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/data_cache.json'
ALERT_STATE   = '/home/pi/.rangetrack_alert_state.json'  # tracks which alerts already fired

# Thresholds
TEMP_ALERT_C      = 80.0   # °C
LOS_ALERT_MINUTES = 15     # minutes since last API fetch
DISK_ALERT_PCT    = 90     # % disk used

# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(subject, body):
    try:
        with open(PASS_FILE) as f:
            password = f.read().strip()
        msg = MIMEText(body)
        msg['Subject'] = f'[{UNIT_ID}] {subject}'
        msg['From']    = FROM
        msg['To']      = TO
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(FROM, password)
        s.sendmail(FROM, TO, msg.as_string())
        s.quit()
        print(f'[{ts()}] Email sent: {subject}')
    except Exception as e:
        print(f'[{ts()}] Email error: {e}')

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ── System Stats ──────────────────────────────────────────────────────────────
def get_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            return int(f.read().strip()) / 1000.0
    except:
        return None

def get_cpu_usage():
    try:
        result = subprocess.run(['top', '-bn1'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'Cpu(s)' in line or '%Cpu' in line:
                parts = line.split(',')
                idle = float([p for p in parts if 'id' in p][0].strip().split()[0])
                return round(100 - idle, 1)
    except:
        pass
    return None

def get_memory():
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        parts = lines[1].split()
        total, used = int(parts[1]), int(parts[2])
        return used, total, round(used / total * 100, 1)
    except:
        return None, None, None

def get_disk():
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        parts = result.stdout.strip().split('\n')[1].split()
        used, total, pct = parts[2], parts[1], int(parts[4].replace('%',''))
        return used, total, pct
    except:
        return None, None, None

def get_uptime():
    try:
        with open('/proc/uptime') as f:
            secs = float(f.read().split()[0])
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f'{h}h {m}m'
    except:
        return 'unknown'

def is_server_running():
    try:
        result = subprocess.run(['pgrep', '-f', SERVER_SCRIPT], capture_output=True)
        return result.returncode == 0
    except:
        return False

def has_internet():
    try:
        subprocess.run(['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                      capture_output=True, check=True)
        return True
    except:
        return False

def get_last_fetch_age():
    try:
        with open(DATA_CACHE) as f:
            data = json.load(f)
        fetched_at = data.get('fetched_at', 0)
        if fetched_at:
            age_min = (time.time() - fetched_at) / 60
            return round(age_min, 1)
    except:
        pass
    return None

# ── Alert State ───────────────────────────────────────────────────────────────
def load_alert_state():
    try:
        with open(ALERT_STATE) as f:
            return json.load(f)
    except:
        return {}

def save_alert_state(state):
    try:
        with open(ALERT_STATE, 'w') as f:
            json.dump(state, f)
    except:
        pass

# ── Digest ────────────────────────────────────────────────────────────────────
def send_digest():
    temp     = get_temp()
    cpu      = get_cpu_usage()
    mem_u, mem_t, mem_pct = get_memory()
    disk_u, disk_t, disk_pct = get_disk()
    uptime   = get_uptime()
    server   = is_server_running()
    internet = has_internet()
    los      = get_last_fetch_age()

    temp_str   = f'{temp:.1f}°C' if temp is not None else 'unknown'
    cpu_str    = f'{cpu}%' if cpu is not None else 'unknown'
    mem_str    = f'{mem_u}MB / {mem_t}MB ({mem_pct}%)' if mem_u else 'unknown'
    disk_str   = f'{disk_u} / {disk_t} ({disk_pct}%)' if disk_u else 'unknown'
    server_str = '✓ Running' if server else '✗ OFFLINE'
    net_str    = '✓ Connected' if internet else '✗ OFFLINE'
    los_str    = f'{los} min ago' if los is not None else 'unknown'

    body = f"""RangeTrack OS — Daily Health Report
{ts()}

UNIT:       {UNIT_ID}
UPTIME:     {uptime}

SYSTEM
  CPU Temp: {temp_str}
  CPU Load: {cpu_str}
  Memory:   {mem_str}
  Disk:     {disk_str}
  Internet: {net_str}

APP
  Server:   {server_str}
  Last API: {los_str}
"""
    send_email('Daily Health Report', body)

# ── Alert Check ───────────────────────────────────────────────────────────────
def check_alerts():
    state   = load_alert_state()
    alerts  = []
    cleared = []

    # Internet
    internet = has_internet()
    if not internet and not state.get('no_internet'):
        alerts.append('INTERNET LOST — Pi has no network connection.')
        state['no_internet'] = True
    elif internet and state.get('no_internet'):
        cleared.append('Internet connection restored.')
        state['no_internet'] = False

    # Temperature
    temp = get_temp()
    if temp is not None:
        if temp >= TEMP_ALERT_C and not state.get('high_temp'):
            alerts.append(f'HIGH TEMP — CPU at {temp:.1f}°C (limit {TEMP_ALERT_C}°C).')
            state['high_temp'] = True
        elif temp < TEMP_ALERT_C and state.get('high_temp'):
            cleared.append(f'Temperature back to normal ({temp:.1f}°C).')
            state['high_temp'] = False

    # Server
    server = is_server_running()
    if not server and not state.get('server_down'):
        alerts.append('SERVER CRASHED — server.py is not running.')
        state['server_down'] = True
    elif server and state.get('server_down'):
        cleared.append('Server is back online.')
        state['server_down'] = False

    # LOS
    los = get_last_fetch_age()
    if los is not None:
        if los >= LOS_ALERT_MINUTES and not state.get('los'):
            alerts.append(f'LOSS OF SIGNAL — No API data for {los:.0f} minutes.')
            state['los'] = True
        elif los < LOS_ALERT_MINUTES and state.get('los'):
            cleared.append(f'API signal restored ({los:.0f} min ago).')
            state['los'] = False

    # Disk
    _, _, disk_pct = get_disk()
    if disk_pct is not None:
        if disk_pct >= DISK_ALERT_PCT and not state.get('low_disk'):
            alerts.append(f'LOW DISK — {disk_pct}% used (limit {DISK_ALERT_PCT}%).')
            state['low_disk'] = True
        elif disk_pct < DISK_ALERT_PCT and state.get('low_disk'):
            cleared.append(f'Disk space OK ({disk_pct}% used).')
            state['low_disk'] = False

    save_alert_state(state)

    if alerts:
        body = f"RangeTrack OS — ALERT\n{ts()}\nUnit: {UNIT_ID}\n\n" + '\n'.join(f'⚠ {a}' for a in alerts)
        send_email('ALERT', body)

    if cleared:
        body = f"RangeTrack OS — Resolved\n{ts()}\nUnit: {UNIT_ID}\n\n" + '\n'.join(f'✓ {c}' for c in cleared)
        send_email('Alert Resolved', body)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'digest'
    if mode == 'digest':
        send_digest()
    elif mode == 'check':
        check_alerts()
    else:
        print(f'Usage: python3 health.py [digest|check]')
