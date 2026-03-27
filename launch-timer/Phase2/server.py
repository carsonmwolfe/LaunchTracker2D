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
import json
import subprocess
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory, request
import os
import base64
import urllib.parse

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)


SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

def _load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            'brightness': 40,
            'temp_unit': 'f',
            'site': 'all',
            'time_format': 'utc'
        }

def _save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
        return True
    except:
        return False

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
    

_location_cache = None

def _get_location():
    """Get approximate lat/lon from IP geolocation, cached."""
    global _location_cache
    if _location_cache:
        return _location_cache
    try:
        r = requests.get('https://ipapi.co/json/', timeout=5)
        d = r.json()
        lat = d.get('latitude', 28.3922)
        lon = d.get('longitude', -80.6077)
        _location_cache = (lat, lon)
        print(f"[{_ts()}] Location detected: {lat}, {lon} ({d.get('city', '?')}, {d.get('region', '?')})")
        return _location_cache
    except:
        print(f"[{_ts()}] Location detection failed — using Cape Canaveral default")
        return 28.3922, -80.6077
    
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
    lat, lon = _get_location()
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,"
        "weather_code,cloud_cover,wind_speed_10m,wind_direction_10m"
        "&daily=sunrise,sunset"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph"
        "&timezone=auto"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data    = r.json()
        c       = data['current']
        daily   = data.get('daily', {})

        wmo_code  = c.get('weather_code', 0)
        wind_deg  = c.get('wind_direction_10m', 0)
        wind_dir  = _WIND_DIRS[int((wind_deg + 11.25) / 22.5) % 16]
        condition = _WMO_CONDITION.get(wmo_code, 'clear')
        label     = _WMO_LABELS.get(wmo_code, f'Code {wmo_code}')
        temp_f    = round(c['temperature_2m'], 1)
        sunrise = daily.get('sunrise', [None])[0]
        sunset  = daily.get('sunset',  [None])[0]

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
            'sunrise': sunrise,
            'sunset':  sunset,
        }
        print(f"[{_ts()}] Weather | {label}, {temp_f}°F, "
              f"{info['wind_speed']} mph {wind_dir}, "
              f"{info['cloud_cover']}% cloud → {condition}")
        return info
    except requests.exceptions.Timeout:
        print(f"[{_ts()}] Weather timeout — using defaults")
    except requests.exceptions.ConnectionError:
        print(f"[{_ts()}] Weather connection error — using defaults")
    except Exception as e:
        print(f"[{_ts()}] Weather error: {e}")
    return {'condition': 'clear', 'label': 'Unknown', 'temp_f': 75,
            'temp_c': 24, 'humidity': 60, 'wind_speed': 10,
            'wind_dir': 'E', 'precip': 0, 'cloud_cover': 0}


# ── Simple in-memory cache ─────────────────────────────────────────────────────

_cache = {
    'launches':         [],
    'launches_fetched': 0,
    'weather':          None,
    'weather_fetched':  0,
}
LAUNCH_TTL  = 300
WEATHER_TTL = 900


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

def _auto_brightness():
    while True:
        try:
            wx = _get_weather()
            sunrise = wx.get('sunrise')
            sunset  = wx.get('sunset')
            if sunrise and sunset:
                now = datetime.now()
                sr  = datetime.fromisoformat(sunrise)
                ss  = datetime.fromisoformat(sunset)

                DAY_MAX   = 255
                NIGHT_MIN = 20
                FADE_MINS = 45
                fade_secs = FADE_MINS * 60

                secs_after_sunrise = (now - sr).total_seconds()
                secs_before_sunset = (ss - now).total_seconds()

                if secs_after_sunrise < 0 or secs_before_sunset < 0:
                    brightness = NIGHT_MIN
                elif secs_after_sunrise < fade_secs:
                    t = secs_after_sunrise / fade_secs
                    brightness = int(NIGHT_MIN + (DAY_MAX - NIGHT_MIN) * t)
                elif secs_before_sunset < fade_secs:
                    t = secs_before_sunset / fade_secs
                    brightness = int(NIGHT_MIN + (DAY_MAX - NIGHT_MIN) * t)
                else:
                    brightness = DAY_MAX

                try:
                    current = int(open('/sys/class/backlight/rpi_backlight/brightness').read().strip())
                    if abs(current - brightness) > 5:
                        with open('/sys/class/backlight/rpi_backlight/brightness', 'w') as f:
                            f.write(str(brightness))
                        print(f"[{_ts()}] Auto brightness → {brightness}")
                except:
                    pass

        except Exception as e:
            print(f"[{_ts()}] Auto brightness error: {e}")
        time.sleep(300)

threading.Thread(target=_auto_brightness, daemon=True).start()

_ll2_last_launch_key = [None]  # mutable container so prefetch thread can update it

def _ll2_prefetch():
    """Background thread — pre-fetches LL2 data on a schedule."""
    time.sleep(10)  # wait for server to fully start
    while True:
        now = time.time()

        # Every hour — fetch events + year launches
        events_cache = _ll2_cache.get('events', {})
        if not events_cache or now - events_cache.get('fetched', 0) > 3600:
            try:
                r = requests.get('https://ll.thespacedevs.com/2.3.0/events/upcoming/?limit=5&format=json', timeout=10)
                if r.status_code == 200:
                    results = r.json().get('results', [])
                    _ll2_cache['events'] = {'data': results, 'fetched': now}
                    print(f"[{_ts()}] Prefetch: events ({len(results)})")
                elif r.status_code == 429:
                    print(f"[{_ts()}] Prefetch: events rate limited, skipping")
            except Exception as e:
                print(f"[{_ts()}] Prefetch: events error {e}")
            time.sleep(30)  # space out requests

        year_cache = _ll2_cache.get('launches_year', {})
        if not year_cache or now - year_cache.get('fetched', 0) > 3600:
            try:
                r = requests.get('https://ll.thespacedevs.com/2.3.0/launches/?window_start__gte=2026-01-01&limit=100&ordering=window_start&format=json', timeout=10)
                if r.status_code == 200:
                    results = r.json().get('results', [])
                    _ll2_cache['launches_year'] = {'data': results, 'fetched': now}
                    print(f"[{_ts()}] Prefetch: year launches ({len(results)})")
                elif r.status_code == 429:
                    print(f"[{_ts()}] Prefetch: year launches rate limited, skipping")
            except Exception as e:
                print(f"[{_ts()}] Prefetch: year error {e}")
            time.sleep(30)

        # Every 5 minutes — fetch LL2 details for current next launch
        launches = _cache.get('launches', [])
        if launches:
            lv = launches[0]
            name = lv.get('name', '')
            launch_id = str(lv.get('id', ''))
            cache_key = launch_id or name

            # If the next launch has changed, purge the old LL2 cache entry
            if _ll2_last_launch_key[0] and _ll2_last_launch_key[0] != cache_key:
                old_key = _ll2_last_launch_key[0]
                if old_key in _ll2_cache:
                    del _ll2_cache[old_key]
                    print(f"[{_ts()}] Prefetch: purged stale LL2 cache for '{old_key}'")
            _ll2_last_launch_key[0] = cache_key

            cached = _ll2_cache.get(cache_key, {})
            if not cached or now - cached.get('fetched', 0) > 300:
                # Build search terms
                search_terms = [name]
                if '|' in name:
                    search_terms.append(name.split('|')[-1].strip())
                clean = name.replace('(','').replace(')','').strip()
                search_terms.append(clean)
                if 'starlink' in name.lower():
                    parts = clean.split()
                    if len(parts) >= 2:
                        search_terms.append(f"Starlink Group {parts[-1]}")
                search_terms = list(dict.fromkeys(search_terms))

                result = {}
                for term in search_terms:
                    try:
                        url = f"https://ll.thespacedevs.com/2.3.0/launches/upcoming/?search={urllib.parse.quote(term)}&limit=1&format=json"
                        r = requests.get(url, timeout=10)
                        if r.status_code == 429:
                            print(f"[{_ts()}] Prefetch: mission rate limited")
                            break
                        result = (r.json().get('results') or [{}])[0]
                        if result:
                            print(f"[{_ts()}] Prefetch: mission matched '{term}'")
                            break
                    except Exception as e:
                        print(f"[{_ts()}] Prefetch: mission error {e}")

                if result:
                    _ll2_cache[cache_key] = {'data': result, 'fetched': now}

        time.sleep(300)  # check every 5 minutes

threading.Thread(target=_ll2_prefetch, daemon=True).start()



# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), path)

@app.route('/api/device')
def api_device():
    try:
        mac = open('/sys/class/net/wlan0/address').read().strip()
    except:
        mac = '??:??:??:??:??:??'
    try:
        unit_id = 'LT-' + mac.replace(':','')[-4:].upper()
    except:
        unit_id = 'LT-???'
    lat, lon = _get_location()
    return jsonify({
        'mac':     mac,
        'unit_id': unit_id,
        'version': 'v1.0.0',
        'lat':     lat,
        'lon':     lon,
    })

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
            'win_close': lv.get('win_close'),
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


@app.route('/api/ll2/invalidate', methods=['POST'])
def invalidate_ll2():
    keys_to_delete = [k for k in _ll2_cache if k not in ('events', 'launches_year')]
    for k in keys_to_delete:
        del _ll2_cache[k]
    _ll2_last_launch_key[0] = None
    print(f"[{_ts()}] LL2 mission cache cleared ({len(keys_to_delete)} entries)")
    return jsonify({'ok': True, 'cleared': len(keys_to_delete)})

_ll2_cache = {}
LL2_TTL = 3600  # 1 hour
LL2_MIN_INTERVAL = 3600  # 1 hour between fetches = max 1/hour

@app.route('/api/ll2')
def api_ll2():
    name      = request.args.get('name', '')
    launch_id = request.args.get('id', '')
    cache_key = launch_id or name
    now       = time.time()

    if cache_key in _ll2_cache:
        cached = _ll2_cache[cache_key]
        if now - cached['fetched'] < LL2_MIN_INTERVAL:
            print(f"[{_ts()}] LL2 cache hit for: {cache_key}")
            return jsonify(cached['data'])

    # Try multiple search variations to maximize match chance
    search_terms = [name]
    # Strip provider prefix e.g. "Falcon 9 | Starlink 17-24" → also try "Starlink 17-24"
    if '|' in name:
        search_terms.append(name.split('|')[-1].strip())
    # Strip parentheses e.g. "Starlink (17-24)" → "Starlink 17-24"
    clean = name.replace('(','').replace(')','').strip()
    search_terms.append(clean)
    # Add "Group" for Starlink e.g. "Starlink 17-24" → "Starlink Group 17-24"
    if 'starlink' in name.lower():
        parts = clean.split()
        if len(parts) >= 2:
            search_terms.append(f"Starlink Group {parts[-1]}")
    # Deduplicate
    search_terms = list(dict.fromkeys(search_terms))

    result = {}
    for term in search_terms:
        try:
            url = f"https://ll.thespacedevs.com/2.3.0/launches/upcoming/?search={urllib.parse.quote(term)}&limit=1&format=json"
            r = requests.get(url, timeout=10)
            if r.status_code == 429:
                print(f"[{_ts()}] LL2 rate limited")
                break
            data = r.json()
            result = (data.get('results') or [{}])[0]
            if result:
                print(f"[{_ts()}] LL2 matched '{term}'")
                break
        except Exception as e:
            print(f"[{_ts()}] LL2 error: {e}")

    # Only try past if nothing found and not rate limited
    if not result:
        try:
            url2 = f"https://ll.thespacedevs.com/2.3.0/launches/?search={urllib.parse.quote(search_terms[0])}&limit=1&format=json"
            r2 = requests.get(url2, timeout=10)
            if r2.status_code != 429:
                result = (r2.json().get('results') or [{}])[0]
                if result:
                    print(f"[{_ts()}] LL2 matched past launch")
        except Exception as e:
            print(f"[{_ts()}] LL2 past error: {e}")

    if result:
        _ll2_cache[cache_key] = {'data': result, 'fetched': now}
    return jsonify(result or {})


@app.route('/api/events')
def api_events():
    now = time.time()
    cache_key = 'events'
    if cache_key in _ll2_cache:
        cached = _ll2_cache[cache_key]
        if now - cached['fetched'] < LL2_MIN_INTERVAL and cached['data']:
            print(f"[{_ts()}] Events cache hit")
            return jsonify(cached['data'])
    try:
        url = 'https://ll.thespacedevs.com/2.3.0/events/upcoming/?limit=5&format=json'
        r = requests.get(url, timeout=10)
        if r.status_code == 429:
            print(f"[{_ts()}] Events rate limited — retry later")
            # Return cached data if we have it, even if stale
            if cache_key in _ll2_cache:
                return jsonify(_ll2_cache[cache_key]['data'])
            return jsonify([])
        results = r.json().get('results', [])
        _ll2_cache[cache_key] = {'data': results, 'fetched': now}
        print(f"[{_ts()}] Events fetched: {len(results)}")
        return jsonify(results)
    except Exception as e:
        print(f"[{_ts()}] Events error: {e}")
        return jsonify([])
    
@app.route('/api/launches/year')
def api_launches_year():
    now = time.time()
    cache_key = 'launches_year'
    if cache_key in _ll2_cache:
        cached = _ll2_cache[cache_key]
        if now - cached['fetched'] < 3600 and cached['data']:
            return jsonify(cached['data'])
    try:
        url = 'https://ll.thespacedevs.com/2.3.0/launches/?window_start__gte=2026-01-01&limit=100&ordering=window_start&format=json'
        r = requests.get(url, timeout=10)
        if r.status_code == 429:
            print(f"[{_ts()}] Year launches rate limited — retry later")
            if cache_key in _ll2_cache:
                return jsonify(_ll2_cache[cache_key]['data'])
            return jsonify([])
        results = r.json().get('results', [])
        _ll2_cache[cache_key] = {'data': results, 'fetched': now}
        print(f"[{_ts()}] Year launches fetched: {len(results)}")
        return jsonify(results)
    except Exception as e:
        print(f"[{_ts()}] Year launches error: {e}")
        return jsonify([])
    
@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'GET':
        return jsonify(_load_settings())
    data = request.get_json()
    settings = _load_settings()
    settings.update(data)
    _save_settings(settings)
    return jsonify({'ok': True, 'settings': settings})
# ── Page routes ───────────────────────────────────────────────────────────────

@app.route('/api/settings/brightness', methods=['POST'])
def set_brightness():
    data = request.get_json()
    val = int(data.get('value', 40))
    val = max(5, min(100, val))
    # Map 0-100 to 0-255
    mapped = int(val * 2.55)
    try:
        subprocess.run(['sudo', 'bash', '-c', f'echo {mapped} > /sys/class/backlight/rpi_backlight/brightness'], check=True)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    return jsonify({'ok': True})

@app.route('/api/reboot', methods=['POST'])
def reboot():
    threading.Thread(target=lambda: (time.sleep(1), subprocess.Popen(['sudo', 'reboot']))).start()
    return jsonify({'ok': True})

# ── Snapshot ──────────────────────────────────────────────────────────────────

_snapshot = None

@app.route('/api/snapshot', methods=['GET', 'POST'])
def api_snapshot():
    global _snapshot
    if request.method == 'POST':
        _snapshot = request.get_json().get('data', '')
        return jsonify({'ok': True})
    if not _snapshot:
        return '', 404
   
    img_data = base64.b64decode(_snapshot.split(',')[1])
    return app.response_class(img_data, mimetype='image/jpeg')

@app.route('/mission')
def mission_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'mission.html')

@app.route('/launches')
def launches_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'launches.html')

@app.route('/settings')
def settings_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'settings.html')

# ── WiFi routes ───────────────────────────────────────────────────────────────

@app.route('/wifi')
def wifi_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'wifi.html')


@app.route('/api/wifi/scan')
def wifi_scan():
    try:
        # Bring interface up in case it's down
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=False)
        time.sleep(1)
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
        # Add new network slot in memory
        result = subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'add_network'],
                                capture_output=True, text=True)
        net_id = result.stdout.strip()
        print(f"[{_ts()}] WiFi: added network id={net_id}")

        # Configure it
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'set_network', net_id, 'ssid', f'"{ssid}"'], check=True)
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'set_network', net_id, 'psk', f'"{password}"'], check=True)
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'select_network', net_id], check=True)

        # Wait for connection
        time.sleep(8)

        # Check status
        status = subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'status'],
                                capture_output=True, text=True)
        print(f"[{_ts()}] WiFi status:\n{status.stdout}")

        connected = f'ssid={ssid}' in status.stdout and 'wpa_state=COMPLETED' in status.stdout

        if connected:
            # Save to config permanently
            clean_config = (
                'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n'
                'update_config=1\n'
                'country=US\n\n'
                'network={\n'
                f'    ssid="{ssid}"\n'
                f'    psk="{password}"\n'
                '    key_mgmt=WPA-PSK\n'
                '}\n'
            )
            with open('/tmp/wpa_supplicant.conf', 'w') as f:
                f.write(clean_config)
            subprocess.run(['sudo', 'bash', '-c', 'cp /tmp/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
            _cache['launches_fetched'] = 0
            _cache['weather_fetched'] = 0
            return jsonify({'ok': True})
        else:
            # Remove failed network and reconnect to old
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'remove_network', net_id], check=True)
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True)
            return jsonify({'ok': False, 'error': 'Could not connect — wrong password?'})

    except Exception as e:
        print(f"[{_ts()}] WiFi connect error: {e}")
        return jsonify({'ok': False, 'error': str(e)})
#lol

# ── Entry point ───────────────────────────────────────────────────────────────

def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    print(f"[{_ts()}] ══════════════════════════════════════")
    print(f"[{_ts()}]  LaunchTracker2D — Phase 3")
    print(f"[{_ts()}]  http://localhost:5001")
    print(f"[{_ts()}] ══════════════════════════════════════")
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
