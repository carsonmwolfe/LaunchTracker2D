#!/usr/bin/env python3
"""
LaunchTracker2D — Backend Server
Single data source: Launch Library 2 (LL2)
Weather:           Open-Meteo (free, no rate limit)

One background thread refreshes all data every 5 minutes.
All pages read from /api/data — single source of truth.
"""

import threading
import time
import requests
import json
import subprocess
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, send_from_directory, request, redirect
import os
import sys
import logging
import signal
import atexit

def _log_exit(sig=None, frame=None):  # noqa: ARG001
    label = f'signal {sig}' if sig else 'normal exit'
    try:
        with open('/home/pi/server.log', 'a') as f:
            f.write(f'[{datetime.now().strftime("%H:%M:%S")}] Server process exiting ({label})\n')
    except Exception:
        pass
    if sig:
        sys.exit(0)

atexit.register(_log_exit)
for _s in (signal.SIGTERM, signal.SIGHUP):
    signal.signal(_s, _log_exit)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
logging.getLogger('werkzeug').setLevel(logging.ERROR)

@app.after_request
def _cors(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
LL2_BASE      = 'https://ll.thespacedevs.com/2.3.0'
LL2_TIMEOUT   = 15
RELAY_URL     = 'http://45.55.245.193'  # DO relay — Pi fetches from here instead of LL2 directly


# ── Settings ──────────────────────────────────────────────────────────────────

def _load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {'brightness': 40, 'temp_unit': 'f', 'site': 'cape', 'time_format': 'local', 'unit_id': '', 'auto_dim': True}

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

try:
    VERSION = subprocess.check_output(
        ['git', '-C', BASE_DIR, 'rev-parse', '--short', 'HEAD'],
        text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
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

_WEATHER_DEFAULT = {
    'condition': 'clear', 'label': 'Loading...', 'temp_f': 0, 'temp_c': 0,
    'humidity': 0, 'wind_speed': 0, 'wind_dir': '—', 'precip': 0, 'cloud_cover': 0,
}

def _get_weather():
    """Returns cached weather — never blocks on a live fetch. Background thread refreshes it."""
    return _weather_cache['data'] or _WEATHER_DEFAULT


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
        'landing_type':         _d(landing.get('type')).get('abbrev') or None,
        'pad_launches':         pad.get('total_launch_count'),
        'last_updated':         r.get('last_updated', ''),
        'patch_url':            patch_url,
    }

_TBD_NAMES = {'unknown', 'tbd', 'to be determined', 'to be confirmed', 'n/a', ''}
_DONE_STATUSES = {'launch successful', 'launch failure', 'partial failure', 'launch in flight', 'in flight'}

def _is_valid(launch):
    """Return False if this launch should be skipped (TBD vehicle, no time, past t0, or already launched)."""
    vehicle = (launch.get('vehicle') or '').strip().lower()
    t0      = (launch.get('t0') or '').strip()
    status  = (launch.get('status') or '').strip().lower()
    if vehicle in _TBD_NAMES:
        return False
    if not t0:
        return False
    if any(s in status for s in _DONE_STATUSES):
        return False
    # Drop launches whose T-0 has passed by more than 10 minutes (API may not have updated status yet)
    try:
        t0_dt = datetime.fromisoformat(t0.replace('Z', '+00:00'))
        if t0_dt < datetime.now(timezone.utc) - timedelta(minutes=10):
            return False
    except Exception:
        pass
    return True


# ── Central data cache ────────────────────────────────────────────────────────

CACHE_FILE    = os.path.join(BASE_DIR, 'data_cache.json')
T0_HIST_FILE  = os.path.join(BASE_DIR, 't0_history.json')
_cache_lock   = threading.Lock()   # guards all _data_cache mutations
_weather_lock = threading.Lock()   # guards _weather_cache reads/writes

def _load_t0_history():
    try:
        with open(T0_HIST_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def _save_t0_history(hist):
    try:
        with open(T0_HIST_FILE, 'w') as f:
            json.dump(hist, f)
    except Exception:
        pass

def _apply_t0_history(launches):
    """For each launch, record its first-seen T0. If T0 has slipped, attach original_t0."""
    hist = _load_t0_history()
    changed = False
    for l in launches:
        lid = str(l.get('id', ''))
        t0  = l.get('t0')
        if not lid or not t0:
            continue
        if lid not in hist:
            hist[lid] = t0
            changed = True
        else:
            orig = hist[lid]
            if orig != t0:
                l['original_t0'] = orig
    # Prune IDs older than 30 days to keep file small
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    hist = {k: v for k, v in hist.items() if v >= cutoff}
    if changed:
        _save_t0_history(hist)
    return launches

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
    """Fetch upcoming launches — tries DO relay first, falls back to LL2 directly."""
    try:
        relay_url = f'{RELAY_URL}/api/launches'
        r = requests.get(relay_url, timeout=8)
        if r.status_code == 200:
            results = r.json()
            if isinstance(results, list) and len(results) > 0:
                launches = []
                skipped  = 0
                for item in results:
                    norm = _normalize_launch(item)
                    if not _is_valid(norm):
                        skipped += 1
                        continue
                    launches.append(norm)
                    if len(launches) >= 5:
                        break
                print(f'[{_ts()}] Relay: {len(launches)} launches (fallback=off)')
                return launches
    except Exception as e:
        print(f'[{_ts()}] Relay unavailable ({e}) — falling back to LL2')
    try:
        url = f'{LL2_BASE}/launches/upcoming/?limit=10&ordering=net&format=json&hide_recent_previous=true'
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

def _fetch_ll2(url, label):
    """Generic LL2 GET — returns results list or None on error/rate-limit."""
    try:
        r = requests.get(url, timeout=LL2_TIMEOUT)
        if r.status_code == 429:
            print(f'[{_ts()}] LL2 rate limited ({label})')
            return None
        r.raise_for_status()
        payload = r.json()
        results = payload.get('results', []) if isinstance(payload, dict) else []
        print(f'[{_ts()}] {label}: {len(results)}')
        return results
    except Exception as e:
        print(f'[{_ts()}] Error fetching {label}: {e}')
        return None

def _fetch_year_launches():
    """Fetch all launches since Jan 1 of current year, paginating past LL2's 100-per-page cap."""
    year_str = datetime.now().strftime('%Y-01-01')
    base = f'{LL2_BASE}/launches/?window_start__gte={year_str}&limit=100&ordering=window_start&format=json'
    all_results = []
    url = base
    pages = 0
    while url and pages < 5:  # cap at 5 pages (500 launches) to protect rate limit
        try:
            r = requests.get(url, timeout=LL2_TIMEOUT)
            if r.status_code == 429:
                print(f'[{_ts()}] LL2 rate limited (year launches page {pages+1})')
                break
            r.raise_for_status()
            payload = r.json()
            all_results.extend(payload.get('results', []))
            url = payload.get('next')  # None when no more pages
            pages += 1
        except Exception as e:
            print(f'[{_ts()}] Error fetching year launches page {pages+1}: {e}')
            break
    print(f'[{_ts()}] year launches: {len(all_results)} across {pages} page(s)')
    return all_results if all_results else None

def _fetch_events():
    return _fetch_ll2(f'{LL2_BASE}/events/upcoming/?limit=5&format=json', 'events')

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
            launches = _apply_t0_history(launches)
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
    """Single background thread — refreshes all data and weather every 5 minutes.
    Switches to 60-second refresh when the next launch is within 10 minutes."""
    time.sleep(2)
    _refresh_all(force_hourly=True)   # full fetch on startup
    wx = _fetch_weather()             # weather on startup too — don't wait 5 min
    if wx:
        _weather_cache['data']    = wx
        _weather_cache['fetched'] = time.time()
    while True:
        # Adaptive interval: 60s when next launch is within 10 min (before or after T-0)
        interval = 300
        launches = _data_cache.get('launches') or []
        if launches:
            try:
                t0_str = (launches[0].get('t0') or '').strip()
                if t0_str:
                    t0_dt = datetime.fromisoformat(t0_str.replace('Z', '+00:00'))
                    diff  = (t0_dt - datetime.now(timezone.utc)).total_seconds()
                    if -300 <= diff <= 600:   # 10 min before → 5 min after
                        interval = 60
            except Exception:
                pass
        time.sleep(interval)
        _refresh_all()
        # Refresh weather in background so /api/data never blocks on a network call
        now = time.time()
        if now - _weather_cache['fetched'] >= WEATHER_TTL:
            data = _fetch_weather()
            with _weather_lock:
                _weather_cache['data']    = data
                _weather_cache['fetched'] = now

_UNIT_ID_FILE = '/home/pi/.rangetrack_unit_id'

def _get_unit_id():
    # Return cached ID if already resolved this session
    if hasattr(_get_unit_id, '_cached'):
        return _get_unit_id._cached
    # Try to load persisted ID first
    try:
        uid = open(_UNIT_ID_FILE).read().strip()
        if uid.startswith('LT-') and len(uid) > 4:
            _get_unit_id._cached = uid
            return uid
    except Exception:
        pass
    # Derive from MAC — retry up to 10 times in case net isn't up yet
    for _ in range(10):
        for iface in ['wlan0', 'eth0', 'wlan1', 'en0']:
            try:
                mac = open(f'/sys/class/net/{iface}/address').read().strip()
                if mac and mac != '00:00:00:00:00:00':
                    uid = 'LT-' + mac.replace(':', '')[-4:].upper()
                    try:
                        open(_UNIT_ID_FILE, 'w').write(uid)
                    except Exception:
                        pass
                    _get_unit_id._cached = uid
                    return uid
            except Exception:
                continue
        import time as _t; _t.sleep(2)
    uid = 'LT-UNKN'
    _get_unit_id._cached = uid
    return uid

def _ping_relay():
    """Ping the DO relay every 5 minutes."""
    while True:
        try:
            settings = _load_settings()
            unit_id  = _get_unit_id()
            wx       = _weather_cache.get('data') or {}
            requests.post(f'{RELAY_URL}/api/unit/ping', json={
                'unit_id':   unit_id,
                'version':   VERSION,
                'site':      settings.get('site', 'cape'),
                'condition': wx.get('condition', ''),
                'temp_f':    wx.get('temp_f', 0),
            }, timeout=5)
        except Exception:
            pass
        time.sleep(300)

def _poll_commands():
    """Poll DO relay for pending commands every 5 seconds."""
    while True:
        try:
            unit_id = _get_unit_id()
            r = requests.get(f'{RELAY_URL}/api/unit/commands/{unit_id}', timeout=5)
            for cmd in r.json():
                _execute_command(cmd.get('command', ''))
        except Exception:
            pass
        time.sleep(5)

def _execute_command(cmd):
    print(f'[{_ts()}] Remote command received: {cmd}')
    try:
        # Acknowledge to relay before executing (reboot won't be able to after)
        try:
            requests.post(f'{RELAY_URL}/api/unit/ack',
                          json={'unit_id': _get_unit_id(), 'command': cmd},
                          timeout=5)
        except Exception:
            pass
        # Queue on-screen notification for all pages (persisted to file to survive restart)
        if cmd == 'update':
            subprocess.Popen(['bash', '/home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/update.sh'])
        elif cmd == 'reboot':
            _notify_write('REBOOTING', 'System reboot in progress...')
            subprocess.Popen(['bash', '-c', 'sleep 2 && sudo /sbin/reboot'])
    except Exception as e:
        print(f'[{_ts()}] Command error: {e}')

threading.Thread(target=_background_thread, daemon=True).start()
threading.Thread(target=_ping_relay, daemon=True).start()
threading.Thread(target=_poll_commands, daemon=True).start()


# ── Auto brightness ───────────────────────────────────────────────────────────

def _backlight_path():
    """Return the first available backlight brightness path, or None."""
    import glob
    for p in glob.glob('/sys/class/backlight/*/brightness'):
        return p
    return None

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
                DAY_MAX, NIGHT_MIN, FADE_SECS = 255, 51, 45 * 60  # NIGHT_MIN=51 ≈ 20%
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
                    bp = _backlight_path()
                    if bp:
                        cur = int(open(bp).read().strip())
                        if abs(cur - brightness) > 5:
                            open(bp, 'w').write(str(brightness))
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
    if not os.path.exists(SETTINGS_FILE):
        return redirect('/settings?setup=1')
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    resp = send_from_directory(os.path.join(BASE_DIR, 'static'), path)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

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
    # Re-apply validity filter on cached data so status changes (e.g. "Launch in Flight")
    # are reflected immediately without waiting for the next LL2 fetch
    launches    = [l for l in _data_cache.get('launches', []) if _is_valid(l)]
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

    # Pre-compute provider counts once instead of O(n*m) per launch
    provider_counts = {}
    for y in past_year:
        name = (y.get('launch_service_provider') or {}).get('name', '')
        if name:
            provider_counts[name] = provider_counts.get(name, 0) + 1

    enriched = []
    for launch in launches:
        l        = dict(launch)
        provider = l.get('provider', '')
        l['orbital_year'] = orbital_year
        l['agency_year']  = provider_counts.get(provider, 0)
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
    with _weather_lock:
        _weather_cache['data']    = None
        _weather_cache['fetched'] = 0
    return jsonify({'ok': True, 'settings': settings})

@app.route('/api/settings/brightness', methods=['POST'])
def set_brightness():
    val    = max(20, min(100, int((request.get_json() or {}).get('value', 40))))
    mapped = int(val * 2.55)
    try:
        bp = _backlight_path()
        if not bp:
            return jsonify({'ok': False, 'error': 'no backlight'})
        open(bp, 'w').write(str(mapped))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    return jsonify({'ok': True})


@app.route('/api/osk')
def api_osk():
    """Show or hide squeekboard on-screen keyboard via D-Bus (Pi 2 / Wayland)."""
    show = request.args.get('show', '1') == '1'
    value = 'true' if show else 'false'
    try:
        env = os.environ.copy()
        env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=/run/user/1000/bus')
        subprocess.run(
            ['dbus-send', '--session', '--dest=sm.puri.OSK0',
             '/sm/puri/OSK0', 'sm.puri.OSK0.SetVisible', f'boolean:{value}'],
            timeout=2, env=env, capture_output=True)
    except Exception as e:
        print(f'[{_ts()}] OSK toggle error: {e}')
    return jsonify({'ok': True, 'visible': show})


@app.route('/api/settings/timezone', methods=['POST'])
def set_timezone():
    tz = (request.get_json() or {}).get('timezone', '')
    if not tz:
        return jsonify({'ok': False, 'error': 'no timezone'})
    try:
        subprocess.run(['sudo', 'timedatectl', 'set-timezone', tz], check=True)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


# ── Device info ───────────────────────────────────────────────────────────────

@app.route('/api/device')
def api_device():
    mac = '??:??:??:??:??:??'
    for iface in ['wlan0', 'eth0', 'end0', 'ens0']:
        try:
            m = open(f'/sys/class/net/{iface}/address').read().strip()
            if m and m != '00:00:00:00:00:00':
                mac = m
                break
        except Exception:
            continue
    auto_id = 'LT-' + mac.replace(':', '')[-4:].upper()
    unit_id = _load_settings().get('unit_id', '').strip() or auto_id
    try:
        temp_raw = int(open('/sys/class/thermal/thermal_zone0/temp').read().strip())
        temp = f'{temp_raw / 1000:.1f}°C'
    except Exception:
        temp = '—'
    def _rel(diff):
        if diff < 60:   return f'{diff}s ago'
        if diff < 3600: return f'{diff // 60}min ago'
        return f'{diff // 3600}h {(diff % 3600) // 60}min ago'
    try:
        import subprocess as _sp
        log = _sp.run(['git', '-C', os.path.dirname(os.path.abspath(__file__)), 'log', '-1', '--format=%at'], capture_output=True, text=True)
        from datetime import timezone
        diff = int(datetime.now(timezone.utc).timestamp()) - int(log.stdout.strip())
        last_deploy = _rel(diff)
    except Exception:
        last_deploy = '—'
    try:
        raw = open('/home/pi/.rangetrack_last_check').read().strip()
        from datetime import timezone
        ts = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        diff = int((datetime.now(timezone.utc) - ts).total_seconds())
        last_check = _rel(diff)
    except Exception:
        last_check = '—'
    return jsonify({'mac': mac, 'unit_id': unit_id, 'version': VERSION, 'temp': temp,
                    'last_update': last_deploy, 'last_check': last_check})


# ── Pi notification (shown on all pages) ──────────────────────────────────────

_NOTIFY_FILE = '/tmp/rangetrack_notify.json'
_NOTIFY_TTL  = 16  # seconds — just over the 15s display time; survives page reloads but doesn't bleed into next update

def _notify_write(title, msg):
    """Write notification to file with expiry so it survives server restarts and page reloads."""
    import json as _json
    entry = {'title': title, 'msg': msg, 'expires': time.time() + _NOTIFY_TTL}
    try:
        with open(_NOTIFY_FILE, 'w') as f:
            _json.dump([entry], f)
    except Exception:
        pass

@app.route('/api/notify')
def get_notify():
    import json as _json
    now = time.time()
    try:
        with open(_NOTIFY_FILE) as f:
            file_msgs = _json.load(f)
        live = [m for m in file_msgs if m.get('expires', 0) > now]
        if live:
            return jsonify([{'title': m['title'], 'msg': m['msg']} for m in live])
        os.remove(_NOTIFY_FILE)
    except Exception:
        pass
    return jsonify([])

@app.route('/api/notify-push', methods=['POST'])
def notify_push():
    data = request.get_json() or {}
    if data.get('title'):
        _notify_write(data['title'], data.get('msg', ''))
    return jsonify({'ok': True})

@app.route('/api/version')
def get_version():
    return jsonify({'version': VERSION})

# ── Reboot ────────────────────────────────────────────────────────────────────

@app.route('/api/reboot', methods=['POST'])
def reboot():
    threading.Thread(
        target=lambda: (time.sleep(1), subprocess.Popen(['sudo', '/sbin/reboot'])),
        daemon=True).start()
    return jsonify({'ok': True})

@app.route('/api/update', methods=['POST'])
def force_update():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'update.sh')
    def _run():
        with open('/home/pi/update.log', 'a') as f:
            subprocess.Popen(['bash', script], stdout=f, stderr=subprocess.STDOUT)
    threading.Thread(target=_run, daemon=True).start()
    _notify_write('UPDATE', 'Force update triggered from Mission Control')
    return jsonify({'ok': True})



# ── WiFi ──────────────────────────────────────────────────────────────────────

def _use_nmcli():
    """True if NetworkManager is managing wifi (Pi OS Trixie+)."""
    try:
        r = subprocess.run(['nmcli', '-t', '-f', 'STATE', 'g'],
                           capture_output=True, text=True, timeout=5)
        return 'connected' in r.stdout or 'disconnected' in r.stdout
    except Exception:
        return False

@app.route('/api/wifi/scan')
def wifi_scan():
    try:
        if _use_nmcli():
            subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'], capture_output=True, timeout=10)
            result = subprocess.check_output(
                ['nmcli', '-t', '-f', 'SSID', 'dev', 'wifi', 'list'],
                text=True, timeout=15)
            networks = []
            for line in result.strip().split('\n'):
                ssid = line.strip()
                if ssid and ssid not in networks:
                    networks.append(ssid)
        else:
            subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=False)
            time.sleep(1)
            result = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan'], text=True, timeout=15)
            networks = []
            for line in result.split('\n'):
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip().strip('"')
                    if ssid and ssid not in networks:
                        networks.append(ssid)
        return jsonify({'networks': networks})
    except Exception as e:
        return jsonify({'networks': [], 'error': str(e)})

@app.route('/api/wifi/current')
def wifi_current():
    try:
        if _use_nmcli():
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'],
                capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if line.startswith('yes:'):
                    return jsonify({'ssid': line.split(':', 1)[1].strip()})
            return jsonify({'ssid': ''})
        else:
            result = subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'status'],
                                    capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if line.startswith('ssid='):
                    return jsonify({'ssid': line.split('=', 1)[1].strip()})
            return jsonify({'ssid': ''})
    except Exception:
        return jsonify({'ssid': ''})

@app.route('/api/wifi/connect', methods=['POST'])
def wifi_connect():
    data     = request.get_json() or {}
    ssid     = data.get('ssid', '')
    password = data.get('password', '')
    try:
        if _use_nmcli():
            # Delete any existing saved connection with this SSID first
            subprocess.run(['nmcli', 'con', 'delete', ssid],
                           capture_output=True, timeout=5)
            if password:
                result = subprocess.run(
                    ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
                    capture_output=True, text=True, timeout=30)
            else:
                result = subprocess.run(
                    ['nmcli', 'dev', 'wifi', 'connect', ssid],
                    capture_output=True, text=True, timeout=30)
            connected = result.returncode == 0 and 'successfully activated' in result.stdout
            if connected:
                _data_cache['fetched_at'] = 0
                return jsonify({'ok': True})
            else:
                err = result.stderr.strip() or result.stdout.strip()
                return jsonify({'ok': False, 'error': err or 'Could not connect — wrong password?'})
        else:
            result = subprocess.run(
                ['sudo', 'wpa_cli', '-i', 'wlan0', 'add_network'],
                capture_output=True, text=True, timeout=5)
            net_id = result.stdout.strip()
            if not net_id.isdigit():
                return jsonify({'ok': False, 'error': 'Failed to create network profile'})
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'set_network', net_id, 'ssid', f'"{ssid}"'], check=True, timeout=5)
            if password:
                subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'set_network', net_id, 'psk', f'"{password}"'], check=True, timeout=5)
            else:
                subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'set_network', net_id, 'key_mgmt', 'NONE'], check=True, timeout=5)
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'select_network', net_id], check=True, timeout=5)
            time.sleep(8)
            status    = subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'status'],
                                       capture_output=True, text=True, timeout=5)
            connected = (f'ssid={ssid}' in status.stdout and
                         'wpa_state=COMPLETED' in status.stdout)
            if connected:
                if password:
                    net_block = f'    ssid="{ssid}"\n    psk="{password}"\n    key_mgmt=WPA-PSK\n'
                else:
                    net_block = f'    ssid="{ssid}"\n    key_mgmt=NONE\n'
                clean_config = (
                    'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n'
                    'update_config=1\ncountry=US\n\n'
                    f'network={{\n{net_block}}}\n'
                )
                with open('/tmp/wpa_supplicant.conf', 'w') as f:
                    f.write(clean_config)
                subprocess.run(['sudo', 'bash', '-c',
                                'cp /tmp/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf'],
                               check=True, timeout=5)
                _data_cache['fetched_at'] = 0
                return jsonify({'ok': True})
            else:
                subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'remove_network', net_id], timeout=5)
                subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], timeout=5)
                return jsonify({'ok': False, 'error': 'Could not connect — wrong password?'})
    except Exception as e:
        print(f'[{_ts()}] WiFi connect error: {e}')
        return jsonify({'ok': False, 'error': str(e)})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f'[{_ts()}] ══════════════════════════════════════')
    print(f'[{_ts()}]  LaunchTracker2D — Phase 2')
    print(f'[{_ts()}]  http://localhost:5001')
    print(f'[{_ts()}] ══════════════════════════════════════')
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
