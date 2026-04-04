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
import subprocess
import time
import json
import os
import base64
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
UNIT_ID       = 'Unit-001'
FROM          = 'rangetrack551@gmail.com'
TO            = 'rangetrack551@gmail.com'
PASS_FILE     = '/home/pi/.rangetrack_gmail_pass'
SERVER_SCRIPT = 'server.py'
DATA_CACHE    = '/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/data_cache.json'
ALERT_STATE   = '/home/pi/.rangetrack_alert_state.json'
UPDATE_LOG    = '/home/pi/.rangetrack_updates.json'

TEMP_ALERT_C      = 80.0
LOS_ALERT_MINUTES = 15
DISK_ALERT_PCT    = 90

# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(subject, html):
    try:
        with open(PASS_FILE) as f:
            password = f.read().strip()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'[{UNIT_ID}] {subject}'
        msg['From']    = FROM
        msg['To']      = TO
        msg.attach(MIMEText(html, 'html'))
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

def take_screenshots():
    """Capture index, launches, and mission pages via headless Chromium.
    Returns dict of {label: base64_png_string} or empty dict on failure."""
    pages = [
        ('MAIN',     'http://localhost:5001/',          45),
        ('LAUNCHES', 'http://localhost:5001/launches',  45),
        ('MISSION',  'http://localhost:5001/mission',   90),
    ]
    results = {}
    tmp_dir = tempfile.mkdtemp()
    for label, url, timeout in pages:
        out = os.path.join(tmp_dir, f'{label}.png')
        try:
            subprocess.run([
                'chromium-browser',
                '--headless',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--window-size=800,480',
                '--virtual-time-budget=3000',
                f'--screenshot={out}',
                url
            ], timeout=timeout, capture_output=True)
            if os.path.exists(out):
                with open(out, 'rb') as f:
                    results[label] = base64.b64encode(f.read()).decode()
                os.remove(out)
        except Exception as e:
            print(f'[{ts()}] Screenshot error ({label}): {e}')
    try:
        os.rmdir(tmp_dir)
    except:
        pass
    return results

def get_recent_updates():
    try:
        with open(UPDATE_LOG) as f:
            updates = json.load(f)
        # Only return updates from the last 24 hours
        cutoff = time.time() - 86400
        recent = []
        for u in updates:
            try:
                t = datetime.strptime(u['time'], '%Y-%m-%d %H:%M:%S').timestamp()
                if t > cutoff:
                    recent.append(u)
            except:
                pass
        return recent
    except:
        return []

def clear_update_log():
    try:
        with open(UPDATE_LOG, 'w') as f:
            json.dump([], f)
    except:
        pass

def get_last_fetch_age():
    try:
        with open(DATA_CACHE) as f:
            data = json.load(f)
        fetched_at = data.get('fetched_at', 0)
        if fetched_at:
            return round((time.time() - fetched_at) / 60, 1)
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

# ── HTML Templates ────────────────────────────────────────────────────────────
PIXEL_FONT = "font-family: 'Courier New', monospace;"

def bar_html(pct, color):
    filled = int(pct / 100 * 20)
    empty  = 20 - filled
    return (
        f'<span style="color:{color};">{"█" * filled}</span>'
        f'<span style="color:#1a2a1a;">{"█" * empty}</span>'
        f' <span style="color:#aaa;">{pct}%</span>'
    )

def status_dot(ok):
    return (
        f'<span style="color:#00e87a;">&#9646; NOMINAL</span>' if ok
        else f'<span style="color:#ff4422;">&#9646; OFFLINE</span>'
    )

def temp_color(t):
    if t is None: return '#aaaaaa'
    if t >= 80:   return '#ff4422'
    if t >= 65:   return '#ffd93d'
    return '#00e87a'

def digest_html(temp, cpu, mem_u, mem_t, mem_pct, disk_u, disk_t, disk_pct, uptime, server, internet, los, updates, screenshots):
    tc    = temp_color(temp)
    ts_   = ts()
    cpu_  = cpu if cpu is not None else 0
    mem_  = mem_pct if mem_pct is not None else 0
    disk_ = disk_pct if disk_pct is not None else 0

    if screenshots:
        shots = ''.join(
            f'<div style="margin-bottom:12px;">'
            f'<div style="color:#4a9ede; font-size:6px; letter-spacing:2px; margin-bottom:4px;">{lbl}</div>'
            f'<img src="data:image/png;base64,{b64}" style="width:100%; border:1px solid #1a2a1a; display:block;">'
            f'</div>'
            for lbl, b64 in screenshots.items()
        )
        screenshots_section = f'''
    <div class="section">
      <div class="section-label">VISUAL CHECK</div>
      {shots}
    </div>'''
    else:
        screenshots_section = ''

    if updates:
        rows = ''.join(
            f'<div style="border-left:3px solid #4a9ede; padding:6px 10px; margin-bottom:6px;">'
            f'<div style="color:#ffd93d; font-size:6px;">{u["time"]}</div>'
            f'<div style="color:#fff; font-size:7px; margin-top:3px;">{u["commit"]}</div>'
            f'</div>'
            for u in reversed(updates)
        )
        updates_section = f'''
    <div class="section">
      <div class="section-label">UPDATES ({len(updates)} IN LAST 24H)</div>
      {rows}
    </div>'''
    else:
        updates_section = ''

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
  body {{ background:#0a0e14; margin:0; padding:20px; {PIXEL_FONT} }}
  .card {{ background:#0d1620; border:2px solid #00e87a; max-width:520px; margin:0 auto; padding:0; }}
  .header {{ background:#00e87a; padding:12px 18px; }}
  .header-title {{ color:#0a0e14; font-size:11px; letter-spacing:2px; margin:0; }}
  .header-sub {{ color:#0a4a2a; font-size:7px; margin-top:4px; }}
  .body {{ padding:18px; }}
  .unit-row {{ display:flex; justify-content:space-between; border-bottom:1px solid #1a2a1a; padding-bottom:10px; margin-bottom:14px; }}
  .unit-id {{ color:#ffd93d; font-size:9px; }}
  .uptime {{ color:#4a9ede; font-size:7px; margin-top:4px; }}
  .timestamp {{ color:#444; font-size:6px; text-align:right; }}
  .section-label {{ color:#00e87a; font-size:6px; letter-spacing:3px; margin-bottom:10px; border-left:3px solid #00e87a; padding-left:8px; }}
  .row {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
  .label {{ color:#4a9ede; font-size:7px; min-width:90px; }}
  .value {{ color:#fff; font-size:7px; text-align:right; }}
  .bar-row {{ margin-bottom:12px; }}
  .bar-label {{ color:#4a9ede; font-size:7px; margin-bottom:4px; }}
  .section {{ margin-bottom:18px; }}
  .footer {{ border-top:1px solid #1a2a1a; padding:8px 18px; text-align:center; color:#1e3048; font-size:6px; }}
  .scanline {{ background:repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.15) 2px, rgba(0,0,0,0.15) 4px); position:fixed; top:0;left:0;right:0;bottom:0; pointer-events:none; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-title">&#9632; RANGETRACK OS</div>
    <div class="header-sub">DAILY HEALTH REPORT // {ts_}</div>
  </div>
  <div class="body">

    <div class="unit-row">
      <div>
        <div class="unit-id">&#9632; {UNIT_ID}</div>
        <div class="uptime">UPTIME: {uptime}</div>
      </div>
      <div class="timestamp">{ts_}</div>
    </div>

    <div class="section">
      <div class="section-label">SYSTEM</div>

      <div class="row">
        <div class="label">CPU TEMP</div>
        <div class="value" style="color:{tc};">{f'{temp:.1f}°C' if temp else '—'}</div>
      </div>

      <div class="bar-row">
        <div class="bar-label">CPU LOAD</div>
        {bar_html(int(cpu_), '#4a9ede')}
      </div>

      <div class="bar-row">
        <div class="bar-label">MEMORY &nbsp;{f'{mem_u}MB / {mem_t}MB' if mem_u else '—'}</div>
        {bar_html(int(mem_), '#ffd93d')}
      </div>

      <div class="bar-row">
        <div class="bar-label">DISK &nbsp;&nbsp;&nbsp;{f'{disk_u} / {disk_t}' if disk_u else '—'}</div>
        {bar_html(int(disk_), '#00e87a')}
      </div>

      <div class="row">
        <div class="label">INTERNET</div>
        <div class="value">{status_dot(internet)}</div>
      </div>
    </div>

    <div class="section">
      <div class="section-label">APPLICATION</div>
      <div class="row">
        <div class="label">SERVER</div>
        <div class="value">{status_dot(server)}</div>
      </div>
      <div class="row">
        <div class="label">LAST API FETCH</div>
        <div class="value" style="color:{'#00e87a' if los and los < 10 else '#ffd93d' if los and los < 20 else '#ff4422'};">
          {f'{los} MIN AGO' if los is not None else '— UNKNOWN'}
        </div>
      </div>
    </div>

  </div>
  {screenshots_section}
  {updates_section}
  <div class="footer">RANGETRACK OS v2.0 // {UNIT_ID} // AUTO HEALTH MONITOR</div>
</div>
</body>
</html>
"""

def alert_html(alerts, resolved=False):
    color  = '#00e87a' if resolved else '#ff4422'
    title  = 'ALERT RESOLVED' if resolved else 'SYSTEM ALERT'
    icon   = '&#10003;' if resolved else '&#9888;'
    items  = ''.join(
        f'<div style="border-left:3px solid {color}; padding:8px 12px; margin-bottom:8px; color:#fff; font-size:7px;">'
        f'{icon} {a}</div>'
        for a in alerts
    )
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ background:#0a0e14; margin:0; padding:20px; font-family:'Courier New',monospace; }}
  .card {{ background:#0d1620; border:2px solid {color}; max-width:520px; margin:0 auto; }}
  .header {{ background:{color}; padding:12px 18px; }}
  .header-title {{ color:#0a0e14; font-size:11px; letter-spacing:2px; margin:0; }}
  .header-sub {{ color:rgba(0,0,0,0.5); font-size:7px; margin-top:4px; }}
  .body {{ padding:18px; }}
  .footer {{ border-top:1px solid #1a2a1a; padding:8px 18px; text-align:center; color:#333; font-size:6px; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-title">&#9632; RANGETRACK OS — {title}</div>
    <div class="header-sub">{UNIT_ID} // {ts()}</div>
  </div>
  <div class="body">
    {items}
  </div>
  <div class="footer">RANGETRACK OS v2.0 // AUTO HEALTH MONITOR</div>
</div>
</body>
</html>
"""

# ── Digest ────────────────────────────────────────────────────────────────────
def send_digest():
    temp                      = get_temp()
    cpu                       = get_cpu_usage()
    mem_u, mem_t, mem_pct     = get_memory()
    disk_u, disk_t, disk_pct  = get_disk()
    uptime                    = get_uptime()
    server                    = is_server_running()
    internet                  = has_internet()
    los                       = get_last_fetch_age()
    updates                   = get_recent_updates()
    print(f'[{ts()}] Taking screenshots...')
    screenshots               = take_screenshots()
    print(f'[{ts()}] Got {len(screenshots)} screenshots')
    html = digest_html(temp, cpu, mem_u, mem_t, mem_pct, disk_u, disk_t, disk_pct, uptime, server, internet, los, updates, screenshots)
    send_email('Daily Health Report', html)
    clear_update_log()  # reset after digest so updates don't stack up

# ── Alert Check ───────────────────────────────────────────────────────────────
def check_alerts():
    state   = load_alert_state()
    alerts  = []
    cleared = []

    internet = has_internet()
    if not internet and not state.get('no_internet'):
        alerts.append('INTERNET LOST — Pi has no network connection.')
        state['no_internet'] = True
    elif internet and state.get('no_internet'):
        cleared.append('Internet connection restored.')
        state['no_internet'] = False

    temp = get_temp()
    if temp is not None:
        if temp >= TEMP_ALERT_C and not state.get('high_temp'):
            alerts.append(f'HIGH TEMP — CPU at {temp:.1f}C (limit {TEMP_ALERT_C}C).')
            state['high_temp'] = True
        elif temp < TEMP_ALERT_C and state.get('high_temp'):
            cleared.append(f'Temperature back to normal ({temp:.1f}C).')
            state['high_temp'] = False

    server = is_server_running()
    if not server and not state.get('server_down'):
        alerts.append('SERVER CRASHED — server.py is not running.')
        state['server_down'] = True
    elif server and state.get('server_down'):
        cleared.append('Server is back online.')
        state['server_down'] = False

    los = get_last_fetch_age()
    if los is not None:
        if los >= LOS_ALERT_MINUTES and not state.get('los'):
            alerts.append(f'LOSS OF SIGNAL — No API data for {los:.0f} minutes.')
            state['los'] = True
        elif los < LOS_ALERT_MINUTES and state.get('los'):
            cleared.append(f'API signal restored ({los:.0f} min ago).')
            state['los'] = False

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
        send_email('ALERT', alert_html(alerts, resolved=False))
    if cleared:
        send_email('Alert Resolved', alert_html(cleared, resolved=True))

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'digest'
    if mode == 'digest':
        send_digest()
    elif mode == 'check':
        check_alerts()
    else:
        print('Usage: python3 health.py [digest|check]')
