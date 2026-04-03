#!/usr/bin/env python3
"""
LaunchTracker2D — Backend Server
Single data source: Launch Library 2 (LL2)
Weather:           Open-Meteo (free, no rate limit)

One background thread refreshes all data every 5 minutes.
All pages read from /api/data — single source of truth.
"""

import threading
import webbrowser
import time
import requests
import json
import subprocess
import base64
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, send_from_directory, request
import os
import sys
import logging

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
logging.getLogger('werkzeug').setLevel(logging.ERROR)

SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
LL2_BASE      = 'https://ll.thespacedevs.com/2.3.0'
LL2_TIMEOUT   = 15


# ── Settings ──────────────────────────────────────────────────────────────────

def _load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {'brightness': 40, 'temp_unit': 'f', 'site': 'all', 'time_format': 'utc'}

def _save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
        return True
    except Exception:
        return False

def _ts():
    return datetime.now().strftime('%H:%M:%S')


# ── Location ──────────────────────────────────────────────────────────────────

SITE_COORDS = {
    'cape':       (28.3922, -80.6077),
    'vandenberg': (34.6321, -120.6110),
    'all':        (28.3922, -80.6077),
}
_location_cache = None

def _get_location():
    global _location_cache
    if _location_cache:
        return _location_cache
    site   = _load_settings().get('site', 'cape')
    coords = SITE_COORDS.get(site, SITE_COORDS['cape'])
    _location_cache = coords
    print(f'[{_ts()}] Location: {site} → {coords[0]}, {coords[1]}')
    return coords


# ── Weather ───────────────────────────────────────────────────────────────────

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

VERSION = 'v2.0.0'

_weather_cache = {'data': None, 'fetched': 0}
WEATHER_TTL = 900  # 15 min

def _fetch_weather():
    lat, lon = _get_location()
    url = (
        f'https://api.open-meteo.com/v1/forecast'
        f'?latitude={lat}&longitude={lon}'
        '&current=temperature_2m,relative_humidity_2m,precipitation,'
        'weather_code,cloud_cover,wind_speed_10m,wind_direction_10m'
        '&daily=sunrise,sunset'
        '&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto'
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data  = r.json()
        c     = data['current']
        daily = data.get('daily', {})
        wmo   = c.get('weather_code', 0)
        temp_f = round(c['temperature_2m'], 1)
        wind_deg = c.get('wind_direction_10m', 0)
        result = {
            'temp_f':      temp_f,
            'temp_c':      round((temp_f - 32) * 5 / 9, 1),
            'condition':   _WMO_CONDITION.get(wmo, 'clear'),
            'label':       _WMO_LABELS.get(wmo, f'Code {wmo}'),
            'weather_code': wmo,
            'humidity':    c.get('relative_humidity_2m', 0),
            'wind_speed':  round(c.get('wind_speed_10m', 0), 1),
            'wind_dir':    _WIND_DIRS[int((wind_deg + 11.25) / 22.5) % 16],
            'precip':      c.get('precipitation', 0),
            'cloud_cover': c.get('cloud_cover', 0),
            'sunrise':     (daily.get('sunrise') or [None])[0],
            'sunset':      (daily.get('sunset')  or [None])[0],
        }
        print(f'[{_ts()}] Weather: {result["label"]}, {temp_f}°F, '
              f'{result["wind_speed"]} mph {result["wind_dir"]}, '
              f'{result["cloud_cover"]}% cloud')
        return result
    except Exception as e:
        print(f'[{_ts()}] Weather error: {e}')
    return {
        'condition': 'clear', 'label': 'Unknown', 'temp_f': 75, 'temp_c': 24,
        'humidity': 60, 'wind_speed': 10, 'wind_dir': 'E', 'precip': 0, 'cloud_cover': 0,
    }

def _get_weather():
    """Always returns from in-memory cache synchronously. Background thread refreshes it."""
    return _weather_cache['data'] or _fetch_weather()


# ── LL2 data normalisation ────────────────────────────────────────────────────

def _d(val):
    """Return val if it's a dict, else {}. Guards against API fields that are
    sometimes None, a string, or any other non-dict type."""
    return val if isinstance(val, dict) else {}

def _normalize_launch(r):
    """Convert a raw LL2 launch object into our flat standard format."""
    rocket      = _d(r.get('rocket'))
    config      = _d(rocket.get('configuration'))
    stages      = rocket.get('launcher_stage')
    stages      = stages if isinstance(stages, list) else []
    stage       = _d(stages[0]) if stages else {}
    launcher    = _d(stage.get('launcher'))
    landing     = _d(stage.get('landing'))
    landing_loc = _d(landing.get('location'))

    mission  = _d(r.get('mission'))
    orbit    = _d(mission.get('orbit'))
    m_type   = _d(mission.get('type'))

    pad      = _d(r.get('pad'))
    pad_loc  = _d(pad.get('location'))
    lsp      = _d(r.get('launch_service_provider'))

    programs  = r.get('program')
    programs  = programs if isinstance(programs, list) else []
    program   = programs[0].get('name', '') if programs and isinstance(programs[0], dict) else ''

    patches   = r.get('mission_patches')
    patches   = patches if isinstance(patches, list) else []
    patch_url = patches[0].get('image_url') if patches and isinstance(patches[0], dict) else None

    prev_flight          = stage.get('previous_flight')
    booster_prev_mission = _d(prev_flight).get('name') if prev_flight else None

    t0 = r.get('net') or r.get('window_start') or ''

    return {
        'id':                   str(r.get('id', '')),
        'name':                 r.get('name', 'Unknown Mission'),
        'vehicle':              config.get('name') or '',
        'provider':             lsp.get('name', ''),
        'pad':                  pad.get('name', ''),
        'location':             pad_loc.get('name', ''),
        'pad_lat':              pad.get('latitude', ''),
        'pad_lon':              pad.get('longitude', ''),
        'status':               (r.get('status') or {}).get('name', 'TBD'),
        't0':                   t0,
        'win_open':             r.get('window_start') or t0,
        'win_close':            r.get('window_end') or '',
        'probability':          r.get('probability'),
        'mission_type':         m_type.get('name', ''),
        'mission_desc':         mission.get('description', ''),
        'orbit_abbrev':         orbit.get('abbrev', ''),
        'orbit_name':           orbit.get('name', ''),
        'program':              program,
        'booster_serial':       launcher.get('serial_number') or None,
        'booster_flight':       stage.get('turn_around_flight_count') or None,
        'booster_last_flight':  stage.get('previous_flight_date') or None,
        'booster_prev_mission': booster_prev_mission,
        'recovery_vessel':      landing_loc.get('name') or None,
        'pad_launches':         pad.get('total_launch_count'),
        'last_updated':         r.get('last_updated', ''),
        'patch_url':            patch_url,
    }

_TBD_NAMES = {'unknown', 'tbd', 'to be determined', 'to be confirmed', 'n/a', ''}
_DONE_STATUSES = {'launch successful', 'launch failure', 'partial failure'}

def _is_valid(launch):
    """Return False if this launch should be skipped (TBD vehicle, no time, or already launched)."""
    vehicle = (launch.get('vehicle') or '').strip().lower()
    t0      = (launch.get('t0') or '').strip()
    status  = (launch.get('status') or '').strip().lower()
    if vehicle in _TBD_NAMES:
        return False
    if not t0:
        return False
    if any(s in status for s in _DONE_STATUSES):
        return False
    return True


# ── Central data cache ────────────────────────────────────────────────────────

CACHE_FILE  = os.path.join(BASE_DIR, 'data_cache.json')
_cache_lock = threading.Lock()   # guards all _data_cache mutations

_data_cache = {
    'launches':       [],   # normalized + filtered upcoming launches
    'year_launches':  [],   # raw LL2 results (for leaderboard)
    'events':         [],   # raw LL2 events
    'fetched_at':     0,    # timestamp of last upcoming-launch fetch
    'hourly_fetched': 0,    # timestamp of last year/events fetch
}

def _load_cache():
    """Load persisted cache from disk on startup so data is available immediately."""
    try:
        with open(CACHE_FILE) as f:
            saved = json.load(f)
        all_launches = saved.get('launches', [])
        valid = [l for l in all_launches if _is_valid(l)]
        _data_cache['launches']       = valid
        _data_cache['year_launches']  = saved.get('year_launches', [])
        _data_cache['events']         = saved.get('events', [])
        _data_cache['fetched_at']     = saved.get('fetched_at', 0)
        _data_cache['hourly_fetched'] = saved.get('hourly_fetched', 0)
        skipped = len(all_launches) - len(valid)
        age = int(time.time() - _data_cache['fetched_at'])
        print(f'[{_ts()}] Loaded cache from disk — {len(valid)} launches, {age}s old'
              + (f', {skipped} stale filtered' if skipped else ''))
    except FileNotFoundError:
        print(f'[{_ts()}] No cache file yet — will fetch fresh data')
    except Exception as e:
        print(f'[{_ts()}] Cache load error: {e}')

def _save_cache():
    """Persist current cache to disk so reboots don't lose data."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({
                'launches':       _data_cache['launches'],
                'year_launches':  _data_cache['year_launches'],
                'events':         _data_cache['events'],
                'fetched_at':     _data_cache['fetched_at'],
                'hourly_fetched': _data_cache['hourly_fetched'],
            }, f)
    except Exception as e:
        print(f'[{_ts()}] Cache save error: {e}')

_load_cache()

def _fetch_upcoming():
    """Fetch upcoming launches from LL2, normalize, filter TBD ones out."""
    try:
        url = f'{LL2_BASE}/launches/upcoming/?limit=10&ordering=net&format=json'
        r   = requests.get(url, timeout=LL2_TIMEOUT)
        if r.status_code == 429:
            print(f'[{_ts()}] LL2 rate limited — keeping cached launches')
            return None
        r.raise_for_status()
        payload = r.json()
        if not isinstance(payload, dict):
            print(f'[{_ts()}] LL2 unexpected response: {str(payload)[:200]}')
            return None
        results  = payload.get('results', [])
        if not isinstance(results, list):
            print(f'[{_ts()}] LL2 results not a list: {str(results)[:200]}')
            return None
        launches = []
        skipped  = 0
        for item in results:
            norm = _normalize_launch(item)
            if not _is_valid(norm):
                skipped += 1
                print(f'[{_ts()}]   skip: {norm["name"]} '
                      f'(vehicle="{norm["vehicle"]}", t0="{norm["t0"]}")')
                continue
            launches.append(norm)
            if len(launches) >= 5:
                break
        print(f'[{_ts()}] Upcoming launches: {len(launches)} valid'
              + (f', {skipped} skipped (TBD)' if skipped else ''))
        for i, l in enumerate(launches):
            marker = '>>>' if i == 0 else '   '
            print(f'  {marker} [{i+1}] {l["name"]} | {l["vehicle"]} '
                  f'| {l["status"]} | T0: {l["t0"] or "TBD"}')
        return launches
    except Exception as e:
        print(f'[{_ts()}] Error fetching upcoming launches: {e}')
        return None

def _fetch_year_launches():
    try:
        year_str = datetime.now().strftime('%Y-01-01')
        url = (f'{LL2_BASE}/launches/'
               f'?window_start__gte={year_str}&limit=100&ordering=window_start&format=json')
        r = requests.get(url, timeout=LL2_TIMEOUT)
        if r.status_code == 429:
            print(f'[{_ts()}] LL2 rate limited (year launches)')
            return None
        r.raise_for_status()
        payload = r.json()
        results = payload.get('results', []) if isinstance(payload, dict) else []
        print(f'[{_ts()}] Year launches: {len(results)}')
        return results
    except Exception as e:
        print(f'[{_ts()}] Error fetching year launches: {e}')
        return None

def _fetch_events():
    try:
        url = f'{LL2_BASE}/events/upcoming/?limit=5&format=json'
        r   = requests.get(url, timeout=LL2_TIMEOUT)
        if r.status_code == 429:
            print(f'[{_ts()}] LL2 rate limited (events)')
            return None
        r.raise_for_status()
        payload = r.json()
        results = payload.get('results', []) if isinstance(payload, dict) else []
        print(f'[{_ts()}] Events: {len(results)}')
        return results
    except Exception as e:
        print(f'[{_ts()}] Error fetching events: {e}')
        return None

_refresh_in_progress = False

def _refresh_all(force_hourly=False):
    """Refresh upcoming launches. Refresh year/events when stale or forced."""
    global _refresh_in_progress
    if _refresh_in_progress:
        print(f'[{_ts()}] Refresh already in progress — skipping')
        return
    _refresh_in_progress = True
    try:
        launches = _fetch_upcoming()
        if launches is not None:
            with _cache_lock:
                _data_cache['launches']   = launches
                _data_cache['fetched_at'] = time.time()

        now = time.time()
        if force_hourly or (now - _data_cache.get('hourly_fetched', 0) > 3600):
            time.sleep(5)
            year = _fetch_year_launches()
            if year is not None:
                with _cache_lock:
                    _data_cache['year_launches'] = year
            time.sleep(5)
            events = _fetch_events()
            if events is not None:
                with _cache_lock:
                    _data_cache['events'] = events
            with _cache_lock:
                _data_cache['hourly_fetched'] = now

        _save_cache()
    finally:
        _refresh_in_progress = False

def _background_thread():
    """Single background thread — refreshes all data and weather every 5 minutes."""
    time.sleep(2)
    _refresh_all(force_hourly=True)   # full fetch on startup
    while True:
        time.sleep(300)               # every 5 minutes
        _refresh_all()
        # Refresh weather in background so /api/data never blocks on a network call
        now = time.time()
        if now - _weather_cache['fetched'] >= WEATHER_TTL:
            data = _fetch_weather()
            _weather_cache['data']    = data
            _weather_cache['fetched'] = now

threading.Thread(target=_background_thread, daemon=True).start()


# ── Auto brightness ───────────────────────────────────────────────────────────

def _auto_brightness():
    while True:
        try:
            wx      = _weather_cache.get('data') or {}
            sunrise = wx.get('sunrise')
            sunset  = wx.get('sunset')
            if sunrise and sunset:
                now  = datetime.now()
                sr   = datetime.fromisoformat(sunrise)
                ss   = datetime.fromisoformat(sunset)
                DAY_MAX, NIGHT_MIN, FADE_SECS = 255, 20, 45 * 60
                after_sr  = (now - sr).total_seconds()
                before_ss = (ss - now).total_seconds()
                if after_sr < 0 or before_ss < 0:
                    brightness = NIGHT_MIN
                elif after_sr < FADE_SECS:
                    brightness = int(NIGHT_MIN + (DAY_MAX - NIGHT_MIN) * after_sr / FADE_SECS)
                elif before_ss < FADE_SECS:
                    brightness = int(NIGHT_MIN + (DAY_MAX - NIGHT_MIN) * before_ss / FADE_SECS)
                else:
                    brightness = DAY_MAX
                try:
                    cur = int(open('/sys/class/backlight/rpi_backlight/brightness').read().strip())
                    if abs(cur - brightness) > 5:
                        open('/sys/class/backlight/rpi_backlight/brightness', 'w').write(str(brightness))
                        print(f'[{_ts()}] Auto brightness → {brightness}')
                except Exception:
                    pass
        except Exception as e:
            print(f'[{_ts()}] Auto brightness error: {e}')
        time.sleep(300)

threading.Thread(target=_auto_brightness, daemon=True).start()


# ── Flask page routes ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), path)

@app.route('/mission')
def mission_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'mission.html')

@app.route('/launches')
def launches_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'launches.html')

@app.route('/settings')
def settings_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'settings.html')

@app.route('/wifi')
def wifi_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'wifi.html')

@app.route('/positioner')
def positioner_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'asset-positioner.html')

@app.route('/api/assets')
def api_assets():
    assets_dir = os.path.join(BASE_DIR, 'static', 'assets')
    try:
        files = sorted([f for f in os.listdir(assets_dir) if f.lower().endswith('.png')])
    except Exception:
        files = []
    return jsonify(files)


# ── Primary data endpoint — all pages read from here ─────────────────────────

@app.route('/api/data')
def api_data():
    launches    = _data_cache.get('launches', [])
    year_raw    = _data_cache.get('year_launches', [])
    events      = _data_cache.get('events', [])
    weather     = _get_weather()
    settings    = _load_settings()
    age_seconds = int(time.time() - _data_cache.get('fetched_at', time.time()))

    # Compute year stats from cached year_launches
    now_dt    = datetime.now(timezone.utc)
    past_year = []
    for l in year_raw:
        ws = l.get('window_start') or l.get('net') or ''
        try:
            if ws and datetime.fromisoformat(ws.replace('Z', '+00:00')) < now_dt:
                past_year.append(l)
        except Exception:
            pass
    orbital_year = len(past_year)

    enriched = []
    for launch in launches:
        l        = dict(launch)
        provider = l.get('provider', '')
        l['orbital_year'] = orbital_year
        l['agency_year']  = sum(
            1 for y in past_year
            if (y.get('launch_service_provider') or {}).get('name', '') == provider
        )
        enriched.append(l)

    return jsonify({
        'launches':      enriched,
        'year_launches': year_raw,
        'events':        events,
        'weather':       weather,
        'settings':      settings,
        'age_seconds':   age_seconds,
    })


# ── Dev/test helper ──────────────────────────────────────────────────────────

@app.route('/api/test-launch')
def api_test_launch():
    """Inject a fake Falcon 9 launch with T-0 = now + ?secs=N (default 60).
    Prepends to /api/data response so the app treats it as the next launch."""
    secs = int(request.args.get('secs', 60))
    t0_dt = datetime.now(timezone.utc) + timedelta(seconds=secs)
    t0_str = t0_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    fake = {
        'id': 'test-9999',
        'name': 'TEST MISSION | TEST SAT-1',
        'vehicle': 'Falcon 9',
        'provider': 'SpaceX',
        'pad': 'SLC-40, Cape Canaveral',
        'location': 'Cape Canaveral, FL, USA',
        'pad_lat': '28.5618571',
        'pad_lon': '-80.577366',
        'status': 'Go for Launch',
        't0': t0_str,
        'win_open': t0_str,
        'win_close': '',
        'probability': 90,
        'mission_type': 'Communications',
        'mission_desc': 'A simulated test launch for development purposes.',
        'orbit_abbrev': 'LEO',
        'orbit_name': 'Low Earth Orbit',
        'program': 'TEST PROGRAM',
        'booster_serial': 'B1078',
        'booster_flight': 12,
        'booster_last_flight': '2024-11-15T00:00:00Z',
        'booster_prev_mission': 'Starlink Group 9-1',
        'recovery_vessel': 'A Shortfall of Gravitas',
        'pad_launches': 142,
        'last_updated': t0_str,
        'patch_url': None,
        'orbital_year': 0,
        'agency_year': 0,
    }
    weather  = _get_weather()
    settings = _load_settings()
    return jsonify({
        'launches':      [fake],
        'year_launches': _data_cache.get('year_launches', []),
        'events':        _data_cache.get('events', []),
        'weather':       weather,
        'settings':      settings,
        'age_seconds':   0,
        '_test_mode':    True,
    })


# ── Backward-compat shims (app.js still calls these) ─────────────────────────

@app.route('/api/launches')
def api_launches():
    """Thin wrapper over _data_cache — same data as /api/data.launches."""
    launches    = _data_cache.get('launches', [])
    age_seconds = int(time.time() - _data_cache.get('fetched_at', time.time()))
    return jsonify({'launches': launches, 'age_seconds': age_seconds})

@app.route('/api/weather')
def api_weather():
    return jsonify(_get_weather())

@app.route('/api/events')
def api_events():
    return jsonify(_data_cache.get('events', []))

@app.route('/api/launches/year')
def api_launches_year():
    return jsonify(_data_cache.get('year_launches', []))

@app.route('/api/launches/invalidate', methods=['POST'])
def invalidate_launches():
    """Force an immediate re-fetch on the background thread schedule."""
    _data_cache['fetched_at'] = 0
    threading.Thread(target=_refresh_all, daemon=True).start()
    print(f'[{_ts()}] Launch cache invalidated — refreshing now')
    return jsonify({'ok': True})


# ── Settings ──────────────────────────────────────────────────────────────────

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'GET':
        return jsonify(_load_settings())
    settings = _load_settings()
    settings.update(request.get_json() or {})
    _save_settings(settings)
    global _location_cache
    _location_cache = None
    # Flush weather so next request reflects new site immediately
    _weather_cache['data']    = None
    _weather_cache['fetched'] = 0
    return jsonify({'ok': True, 'settings': settings})

@app.route('/api/settings/brightness', methods=['POST'])
def set_brightness():
    val    = max(5, min(100, int((request.get_json() or {}).get('value', 40))))
    mapped = int(val * 2.55)
    try:
        subprocess.run(
            ['sudo', 'bash', '-c', f'echo {mapped} > /sys/class/backlight/rpi_backlight/brightness'],
            check=True)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    return jsonify({'ok': True})


# ── Device info ───────────────────────────────────────────────────────────────

@app.route('/api/device')
def api_device():
    try:
        mac = open('/sys/class/net/wlan0/address').read().strip()
    except Exception:
        mac = '??:??:??:??:??:??'
    unit_id = 'LT-' + mac.replace(':', '')[-4:].upper()
    lat, lon = _get_location()
    return jsonify({'mac': mac, 'unit_id': unit_id, 'version': VERSION, 'lat': lat, 'lon': lon})


# ── Reboot ────────────────────────────────────────────────────────────────────

@app.route('/api/reboot', methods=['POST'])
def reboot():
    threading.Thread(
        target=lambda: (time.sleep(1), subprocess.Popen(['sudo', 'reboot'])),
        daemon=True).start()
    return jsonify({'ok': True})


# ── Snapshot ──────────────────────────────────────────────────────────────────

_snapshot = None

@app.route('/api/snapshot', methods=['GET', 'POST'])
def api_snapshot():
    global _snapshot
    if request.method == 'POST':
        _snapshot = (request.get_json() or {}).get('data', '')
        return jsonify({'ok': True})
    if not _snapshot:
        return '', 404
    try:
        parts = _snapshot.split(',', 1)
        return app.response_class(base64.b64decode(parts[1]), mimetype='image/jpeg')
    except Exception:
        return '', 400


# ── WiFi ──────────────────────────────────────────────────────────────────────

@app.route('/api/wifi/scan')
def wifi_scan():
    try:
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=False)
        time.sleep(1)
        result   = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan'], text=True)
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
    data     = request.get_json() or {}
    ssid     = data.get('ssid', '')
    password = data.get('password', '')
    try:
        result = subprocess.run(
            ['sudo', 'wpa_cli', '-i', 'wlan0', 'add_network'],
            capture_output=True, text=True)
        net_id = result.stdout.strip()
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'set_network', net_id, 'ssid',     f'"{ssid}"'],     check=True)
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'set_network', net_id, 'psk',      f'"{password}"'], check=True)
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'select_network', net_id],          check=True)
        time.sleep(8)
        status    = subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'status'],
                                   capture_output=True, text=True)
        connected = (f'ssid={ssid}' in status.stdout and
                     'wpa_state=COMPLETED' in status.stdout)
        if connected:
            clean_config = (
                'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n'
                'update_config=1\ncountry=US\n\n'
                f'network={{\n    ssid="{ssid}"\n    psk="{password}"\n'
                '    key_mgmt=WPA-PSK\n}\n'
            )
            with open('/tmp/wpa_supplicant.conf', 'w') as f:
                f.write(clean_config)
            subprocess.run(['sudo', 'bash', '-c',
                            'cp /tmp/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf'],
                           check=True)
            _data_cache['fetched_at'] = 0
            return jsonify({'ok': True})
        else:
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'remove_network', net_id], check=True)
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'],             check=True)
            return jsonify({'ok': False, 'error': 'Could not connect — wrong password?'})
    except Exception as e:
        print(f'[{_ts()}] WiFi connect error: {e}')
        return jsonify({'ok': False, 'error': str(e)})


# ── Entry point ───────────────────────────────────────────────────────────────

def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    print(f'[{_ts()}] ══════════════════════════════════════')
    print(f'[{_ts()}]  LaunchTracker2D — Phase 2')
    print(f'[{_ts()}]  http://localhost:5001')
    print(f'[{_ts()}] ══════════════════════════════════════')
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
