#!/usr/bin/env python3
"""
Phase 2 Backend Server
Fetches launch and weather data, serves it to the browser frontend.
Run this file to start the app — it will open your browser automatically.
"""

import threading
import webbrowser
import time
import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory
import os

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))

# ── Helpers ──────────────────────────────────────────────────────────────────

def _ts():
    return datetime.now().strftime("%H:%M:%S")


# ── Launch API ────────────────────────────────────────────────────────────────

def fetch_launches(num_launches=5):
    """Fetch upcoming launches from RocketLaunch.Live, filter completed ones."""
    url = f"https://fdo.rocketlaunch.live/json/launches/next/{num_launches}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        launches = response.json().get('result', [])

        upcoming = []
        skipped = 0
        for launch in launches:
            result  = launch.get('result')
            status_id = launch.get('status', {}).get('id', 0)
            if (result is not None and result > 0) or status_id == 3:
                skipped += 1
                continue
            upcoming.append(launch)

        print(f"[{_ts()}] Launches fetched: {len(upcoming)} upcoming"
              + (f", {skipped} skipped" if skipped else ""))
        for i, lv in enumerate(upcoming):
            t0      = lv.get('t0') or lv.get('win_open') or 'TBD'
            vehicle = lv.get('vehicle', {}).get('name', 'Unknown')
            status  = lv.get('status', {}).get('name', '?')
            marker  = ">>>" if i == 0 else "   "
            print(f"  {marker} [{i+1}] {lv.get('name', 'Unknown')}")
            print(f"         Vehicle: {vehicle} | Status: {status} | T0: {t0}")
        return upcoming
    except requests.exceptions.RequestException as e:
        print(f"[{_ts()}] ERROR fetching launches: {e}")
        return []


def get_countdown(launch_time_iso):
    """Return countdown dict or 'LAUNCHED' string."""
    if not launch_time_iso:
        return None
    try:
        launch_time = datetime.fromisoformat(launch_time_iso.replace('Z', '+00:00'))
        now   = datetime.now(timezone.utc)
        delta = launch_time - now
        if delta.total_seconds() < 0:
            return "LAUNCHED"
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        return {
            'days': days, 'hours': hours,
            'minutes': minutes, 'seconds': seconds,
            'total_seconds': delta.total_seconds()
        }
    except Exception:
        return None


# ── Weather API ───────────────────────────────────────────────────────────────

_WIND_DIRS = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
              'S','SSW','SW','WSW','W','WNW','NW','NNW']

_WMO_LABELS = {
    0:'Clear sky', 1:'Mainly clear', 2:'Partly cloudy', 3:'Overcast',
    45:'Foggy', 48:'Icy fog',
    51:'Light drizzle', 53:'Drizzle', 55:'Heavy drizzle',
    61:'Light rain', 63:'Rain', 65:'Heavy rain',
    80:'Light showers', 81:'Showers', 82:'Heavy showers',
    95:'Thunderstorm', 96:'Thunderstorm w/ hail', 99:'Thunderstorm w/ heavy hail',
}

_WMO_CONDITION = {
    0:'clear', 1:'clear', 2:'cloudy', 3:'cloudy',
    45:'fog', 48:'fog',
    51:'light_rain', 53:'light_rain', 55:'light_rain', 61:'light_rain',
    63:'rain', 65:'rain', 80:'rain', 81:'rain', 82:'rain',
    95:'thunderstorm', 96:'thunderstorm', 99:'thunderstorm',
}


def fetch_weather():
    """Fetch Cape Canaveral weather from Open-Meteo (free, no key, reliable)."""
    ts = _ts()
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=28.3922&longitude=-80.6077"
        "&current=temperature_2m,relative_humidity_2m,precipitation,"
        "weather_code,cloud_cover,wind_speed_10m,wind_direction_10m"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph"
        "&timezone=America%2FNew_York"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        c = r.json()['current']

        wmo_code  = c.get('weather_code', 0)
        wind_deg  = c.get('wind_direction_10m', 0)
        wind_dir  = _WIND_DIRS[int((wind_deg + 11.25) / 22.5) % 16]
        condition = _WMO_CONDITION.get(wmo_code, 'clear')
        label     = _WMO_LABELS.get(wmo_code, f'Code {wmo_code}')
        temp_f    = round(c['temperature_2m'], 1)

        info = {
            'temp_f':      temp_f,
            'temp_c':      round((temp_f - 32) * 5 / 9, 1),
            'condition':   condition,
            'label':       label,
            'weather_code': wmo_code,
            'humidity':    c.get('relative_humidity_2m', 0),
            'wind_speed':  round(c.get('wind_speed_10m', 0), 1),
            'wind_dir':    wind_dir,
            'precip':      c.get('precipitation', 0),
            'cloud_cover': c.get('cloud_cover', 0),
        }
        print(f"[{ts}] Weather | {label}, {temp_f}°F, "
              f"{info['wind_speed']} mph {wind_dir}, "
              f"{info['cloud_cover']}% cloud → {condition}")
        return info
    except requests.exceptions.Timeout:
        print(f"[{ts}] Weather timeout — using defaults")
    except requests.exceptions.ConnectionError:
        print(f"[{ts}] Weather connection error — using defaults")
    except Exception as e:
        print(f"[{ts}] Weather error: {e}")
    return {'condition': 'clear', 'label': 'Unknown', 'temp_f': 75,
            'temp_c': 24, 'humidity': 60, 'wind_speed': 10,
            'wind_dir': 'E', 'precip': 0, 'cloud_cover': 0}


# ── Simple in-memory cache ─────────────────────────────────────────────────────
# Avoids hammering APIs on every browser refresh.

_cache = {
    'launches':         [],
    'launches_fetched': 0,
    'weather':          None,
    'weather_fetched':  0,
}
LAUNCH_TTL  = 300   # seconds — refresh launch list every 5 minutes
WEATHER_TTL = 900   # seconds — refresh weather every 15 minutes


def _get_launches():
    now = time.time()
    if not _cache['launches'] or (now - _cache['launches_fetched']) > LAUNCH_TTL:
        _cache['launches']         = fetch_launches(5)
        _cache['launches_fetched'] = now
    return _cache['launches']


def _get_weather():
    now = time.time()
    if not _cache['weather'] or (now - _cache['weather_fetched']) > WEATHER_TTL:
        _cache['weather']         = fetch_weather()
        _cache['weather_fetched'] = now
    return _cache['weather']


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), path)


@app.route('/api/launches')
def api_launches():
    """Return upcoming launches with countdown pre-computed."""
    launches = _get_launches()
    result   = []
    for lv in launches:
        t0       = lv.get('t0') or lv.get('win_open')
        countdown = get_countdown(t0)
        result.append({
            'id':       lv.get('id'),
            'name':     lv.get('name', 'Unknown Mission'),
            'vehicle':  lv.get('vehicle', {}).get('name', 'Unknown'),
            'provider': lv.get('provider', {}).get('name', 'Unknown'),
            'pad':      lv.get('pad', {}).get('name', 'Unknown'),
            'location': lv.get('pad', {}).get('location', {}).get('name', 'Unknown'),
            'status':   lv.get('status', {}).get('name', 'TBD'),
            't0':       t0,
            'win_open': lv.get('win_open'),
            'countdown': countdown,
            'result':   lv.get('result'),
        })
    return jsonify({'launches': result, 'fetched_at': _ts()})


@app.route('/api/weather')
def api_weather():
    return jsonify(_get_weather())


@app.route('/api/launches/invalidate', methods=['POST'])
def invalidate_launches():
    """Force a fresh launch fetch on next request (called after a launch completes)."""
    _cache['launches_fetched'] = 0
    print(f"[{_ts()}] Launch cache invalidated")
    return jsonify({'ok': True})


# ── Entry point ───────────────────────────────────────────────────────────────

def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://localhost:5001')

import subprocess

@app.route('/wifi')
def wifi_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'wifi.html')

@app.route('/api/wifi/scan')
def wifi_scan():
    try:
        result = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan'], text=True)
        networks = []
        for line in result.split('\n'):
            if 'ESSID:' in line:
                ssid = line.split('ESSID:')[1].strip().strip('"')
                if ssid and ssid not in networks:
                    networks.append(ssid)
        return jsonify({'networks': networks})
    except Exception as e:
        return jsonify({'networks': [], 'error': str(e)})

@app.route('/api/wifi/connect', methods=['POST'])
def wifi_connect():
    data = request.get_json()
    ssid = data.get('ssid', '')
    password = data.get('password', '')
    try:
        config = f'\nnetwork={{\n    ssid="{ssid}"\n    psk="{password}"\n}}\n'
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a') as f:
            f.write(config)
        subprocess.Popen(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

if __name__ == '__main__':
    print(f"[{_ts()}] ══════════════════════════════════════")
    print(f"[{_ts()}]  Launch Countdown — Phase 2")
    print(f"[{_ts()}]  http://localhost:5001")
    print(f"[{_ts()}] ══════════════════════════════════════")
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
    