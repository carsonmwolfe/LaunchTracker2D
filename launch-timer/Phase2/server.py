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
    response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
LL2_BASE      = 'https://ll.thespacedevs.com/2.3.0'
LL2_TIMEOUT   = 15
RELAY_URL     = 'http://45.55.245.193'  # DO relay — Pi fetches from here instead of LL2 directly
_wake_until   = 0  # Unix timestamp set by /api/wake — holds brightness after tap-to-wake

# ── Email alerts ──────────────────────────────────────────────────────────────
ALERT_TO      = 'carzspam001@gmail.com'
ALERT_MIN_GAP = 7200      # minimum seconds between alerts (2 hours)
_alert_state  = {'last_sent': 0, 'fail_count': 0}
try:
    _ecfg      = json.load(open(os.path.join(BASE_DIR, 'email_config.json')))
    ALERT_FROM = _ecfg.get('from', '')
    ALERT_PASS = _ecfg.get('pass', '')
except Exception:
    ALERT_FROM = ''
    ALERT_PASS = ''

def _send_alert(subject, body):
    """Send an email alert; rate-limited to once per ALERT_MIN_GAP seconds."""
    if not ALERT_FROM or not ALERT_PASS:
        return  # not configured
    now = time.time()
    if now - _alert_state['last_sent'] < ALERT_MIN_GAP:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg['Subject'] = f'[LaunchTracker] {subject}'
        msg['From']    = ALERT_FROM
        msg['To']      = ALERT_TO
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as s:
            s.login(ALERT_FROM, ALERT_PASS)
            s.sendmail(ALERT_FROM, [ALERT_TO], msg.as_string())
        _alert_state['last_sent'] = now
        print(f'[{_ts()}] Alert sent: {subject}')
    except Exception as e:
        print(f'[{_ts()}] Alert failed: {e}')


# ── Settings ──────────────────────────────────────────────────────────────────

_SCREEN_MODE_MAP = {
    'auto':      {'auto_dim': True,  'display_mode': 'auto'},
    'always_on': {'auto_dim': False, 'display_mode': 'bright'},
    'sleep':     {'auto_dim': True,  'display_mode': 'night'},
}

def _load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
        # Derive screen_mode from legacy fields if not present
        if 'screen_mode' not in s:
            dm = s.get('display_mode', 'auto')
            ad = s.get('auto_dim', True)
            if dm == 'night':   s['screen_mode'] = 'sleep'
            elif not ad:        s['screen_mode'] = 'always_on'
            else:               s['screen_mode'] = 'auto'
        return s
    except Exception:
        return {'brightness': 40, 'temp_unit': 'f', 'site': 'cape', 'time_format': 'local',
                'unit_id': '', 'auto_dim': True, 'display_mode': 'auto', 'screen_mode': 'auto'}

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
    # Use next launch's pad coordinates if available — weather should match the mission site
    launches = _data_cache.get('launches', [])
    if launches:
        try:
            lat = float(launches[0].get('pad_lat') or '')
            lon = float(launches[0].get('pad_lon') or '')
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except (ValueError, TypeError):
            pass
    # Fall back to static site setting
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
    """Fetch weather — relay first (shared across all Pis), direct open-meteo fallback."""
    # Try relay — all Pis share the same weather this way
    try:
        r = requests.get(f'{RELAY_URL}/api/weather', timeout=8)
        if r.status_code == 200:
            wx = r.json()
            if wx and wx.get('temp_f') is not None:
                print(f'[{_ts()}] Weather (relay): {wx.get("label")}, {wx.get("temp_f")}°F')
                return wx
    except Exception as e:
        print(f'[{_ts()}] Relay weather unavailable ({e}) — falling back to open-meteo')
    # Fallback: fetch directly from open-meteo using local pad coords
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
        print(f'[{_ts()}] Weather (direct): {result["label"]}, {temp_f}°F, '
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

LIFTOFF_WX_TTL = 1800  # 30 min

def _fetch_liftoff_weather():
    """Fetch Open-Meteo hourly forecast for the T-0 hour of the next launch."""
    launches = _data_cache.get('launches', [])
    if not launches:
        return None
    t0 = launches[0].get('t0')
    if not t0:
        return None
    try:
        t0_dt = datetime.fromisoformat(t0.replace('Z', '+00:00'))
        diff_h = (t0_dt - datetime.now(timezone.utc)).total_seconds() / 3600
        if diff_h < 0 or diff_h > 168:  # only forecast up to 7 days out
            return None
    except Exception:
        return None
    lat, lon = _get_location()
    try:
        r = requests.get('https://api.open-meteo.com/v1/forecast', params={
            'latitude': lat, 'longitude': lon,
            'hourly': 'weather_code,wind_speed_10m,cloud_cover,precipitation',
            'wind_speed_unit': 'mph',
            'timezone': 'UTC',
            'forecast_days': 7,
        }, timeout=10)
        r.raise_for_status()
        data   = r.json()
        hourly = data.get('hourly', {})
        times  = hourly.get('time', [])
        prefix = t0_dt.strftime('%Y-%m-%dT%H')
        idx    = next((i for i, t in enumerate(times) if t.startswith(prefix)), None)
        if idx is None:
            return None
        wmo   = (hourly.get('weather_code') or [])[idx] if idx < len(hourly.get('weather_code') or []) else 0
        wind  = round((hourly.get('wind_speed_10m') or [])[idx], 1) if idx < len(hourly.get('wind_speed_10m') or []) else 0
        cloud = (hourly.get('cloud_cover') or [])[idx] if idx < len(hourly.get('cloud_cover') or []) else 0
        precip= (hourly.get('precipitation') or [])[idx] if idx < len(hourly.get('precipitation') or []) else 0
        result = {
            'condition':    _WMO_CONDITION.get(wmo, 'clear'),
            'label':        _WMO_LABELS.get(wmo, f'Code {wmo}'),
            'weather_code': wmo,
            'wind_speed':   wind,
            'cloud_cover':  cloud,
            'precip':       precip,
            't0_hour':      times[idx],
        }
        print(f'[{_ts()}] Liftoff wx @ {times[idx]}: {result["label"]}, {wind}mph, {cloud}% cloud')
        return result
    except Exception as e:
        print(f'[{_ts()}] Liftoff weather error: {e}')
        return None

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

CACHE_FILE      = os.path.join(BASE_DIR, 'data_cache.json')
T0_HIST_FILE    = os.path.join(os.path.expanduser('~'), '.rangetrack_t0_history.json')
T0_HIST_SEED    = os.path.join(BASE_DIR, 't0_history_seed.json')
_cache_lock   = threading.Lock()   # guards all _data_cache mutations
_weather_lock = threading.Lock()   # guards _weather_cache reads/writes

def _load_t0_history():
    hist = {}
    # Merge seed file first so Pis pick up known slips without having observed them
    try:
        with open(T0_HIST_SEED) as f:
            hist.update(json.load(f))
    except Exception:
        pass
    # Local history overwrites seed — local observations take precedence
    try:
        with open(T0_HIST_FILE) as f:
            hist.update(json.load(f))
    except Exception:
        pass
    return hist

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
    'launches':         [],   # normalized + filtered upcoming launches
    'year_launches':    [],   # raw LL2 results (for leaderboard)
    'events':           [],   # raw LL2 events
    'liftoff_wx':       None, # hourly forecast for T-0 hour
    'liftoff_wx_at':    0,    # timestamp of last liftoff weather fetch
    'fetched_at':       0,    # timestamp of last upcoming-launch fetch
    'hourly_fetched':   0,    # timestamp of last year/events fetch
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
            msg = str(payload)[:200]
            print(f'[{_ts()}] LL2 unexpected response: {msg}')
            _send_alert('API format changed', f'LL2 returned unexpected type: {msg}')
            return None
        results  = payload.get('results', [])
        if not isinstance(results, list):
            msg = str(results)[:200]
            print(f'[{_ts()}] LL2 results not a list: {msg}')
            _send_alert('API format changed', f'LL2 "results" field is not a list: {msg}')
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
    """Fetch year launches — relay first, LL2 direct fallback."""
    try:
        r = requests.get(f'{RELAY_URL}/api/launches/year', timeout=10)
        if r.status_code == 200:
            results = r.json()
            if isinstance(results, list) and results:
                print(f'[{_ts()}] Year launches (relay): {len(results)}')
                return results
    except Exception as e:
        print(f'[{_ts()}] Relay year launches unavailable ({e}) — falling back to LL2')
    # Direct LL2 fallback with pagination
    year_str = datetime.now().strftime('%Y-01-01')
    base = f'{LL2_BASE}/launches/?window_start__gte={year_str}&limit=100&ordering=window_start&format=json'
    all_results = []
    url = base
    pages = 0
    interrupted = False
    while url and pages < 5:
        try:
            r = requests.get(url, timeout=LL2_TIMEOUT)
            if r.status_code == 429:
                print(f'[{_ts()}] LL2 rate limited (year launches page {pages+1})')
                interrupted = True
                break
            r.raise_for_status()
            payload = r.json()
            all_results.extend(payload.get('results', []))
            url = payload.get('next')
            pages += 1
        except Exception as e:
            print(f'[{_ts()}] Error fetching year launches page {pages+1}: {e}')
            interrupted = True
            break
    print(f'[{_ts()}] year launches: {len(all_results)} across {pages} page(s)'
          + (' (interrupted)' if interrupted else ''))
    if not all_results:
        return None
    cached = _data_cache.get('year_launches', [])
    if interrupted and len(all_results) < len(cached):
        print(f'[{_ts()}] Keeping cached year launches ({len(cached)}) over partial fetch ({len(all_results)})')
        return None
    return all_results

def _fetch_events():
    """Fetch events — relay first, LL2 direct fallback."""
    try:
        r = requests.get(f'{RELAY_URL}/api/events', timeout=8)
        if r.status_code == 200:
            results = r.json()
            if isinstance(results, list):
                print(f'[{_ts()}] Events (relay): {len(results)}')
                return results
    except Exception as e:
        print(f'[{_ts()}] Relay events unavailable ({e}) — falling back to LL2')
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
            _alert_state['fail_count'] = 0  # reset on success
        else:
            _alert_state['fail_count'] = _alert_state.get('fail_count', 0) + 1
            if _alert_state['fail_count'] >= 3:
                _send_alert('API down', 'Both relay and LL2 failed 3 consecutive fetches. Pi is serving stale data.')

        now = time.time()
        if force_hourly or (now - _data_cache.get('hourly_fetched', 0) > 3600):
            time.sleep(5)
            year = _fetch_year_launches()
            if year is not None:
                cached_year = _data_cache.get('year_launches', [])
                if len(year) < len(cached_year):
                    print(f'[{_ts()}] Keeping cached year launches ({len(cached_year)}) over fetch ({len(year)})')
                else:
                    with _cache_lock:
                        _data_cache['year_launches'] = year
            time.sleep(5)
            events = _fetch_events()
            if events is not None:
                with _cache_lock:
                    _data_cache['events'] = events
            with _cache_lock:
                _data_cache['hourly_fetched'] = now

        # Liftoff weather — refresh every 30 min or when launch changes
        if now - _data_cache.get('liftoff_wx_at', 0) >= LIFTOFF_WX_TTL:
            liftoff_wx = _fetch_liftoff_weather()
            with _cache_lock:
                if liftoff_wx:
                    _data_cache['liftoff_wx'] = liftoff_wx
                _data_cache['liftoff_wx_at'] = now

        _save_cache()
    finally:
        _refresh_in_progress = False

def _background_thread():
    """Single background thread — refreshes all data and weather every 5 minutes.
    Switches to 60-second refresh when the next launch is within 10 minutes."""
    time.sleep(2)
    # Fetch weather first — it's fast so /api/data has real values during the slow LL2 fetch
    wx = _fetch_weather()
    if wx:
        with _weather_lock:
            _weather_cache['data']    = wx
            _weather_cache['fetched'] = time.time()
    _refresh_all(force_hourly=True)   # full fetch on startup (can take many seconds)
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

def _get_tailscale_ip():
    """Return Tailscale IPv4 address if Tailscale is running, else None."""
    try:
        r = subprocess.run(['tailscale', 'ip', '-4'],
                           capture_output=True, text=True, timeout=3)
        ip = r.stdout.strip()
        if r.returncode == 0 and ip:
            return ip
    except Exception:
        pass
    return None

def _get_cpu_temp():
    try:
        return round(int(open('/sys/class/thermal/thermal_zone0/temp').read().strip()) / 1000, 1)
    except Exception:
        return None

def _get_disk_pct():
    try:
        r = subprocess.run(['df', '/'], capture_output=True, text=True, timeout=3)
        return int(r.stdout.splitlines()[1].split()[4].replace('%', ''))
    except Exception:
        return None

def _get_mem_mb():
    try:
        lines = open('/proc/meminfo').readlines()
        mem = {l.split(':')[0]: int(l.split()[1]) for l in lines if ':' in l}
        free = (mem.get('MemAvailable') or mem.get('MemFree') or 0) // 1024
        total = (mem.get('MemTotal') or 0) // 1024
        return {'free': free, 'total': total}
    except Exception:
        return None

def _ping_relay():
    """Ping the DO relay every 60 seconds with health data."""
    _ts_ip = _get_tailscale_ip()
    _ping_count = 0
    while True:
        try:
            _ping_count += 1
            if _ts_ip is None or _ping_count % 10 == 0:
                _ts_ip = _get_tailscale_ip()
            settings = _load_settings()
            unit_id  = _get_unit_id()
            wx       = _weather_cache.get('data') or {}
            mem      = _get_mem_mb() or {}
            data_age = int(time.time() - _data_cache.get('fetched_at', 0))
            requests.post(f'{RELAY_URL}/api/unit/ping', json={
                'unit_id':      unit_id,
                'version':      VERSION,
                'site':         settings.get('site', 'cape'),
                'condition':    wx.get('condition', ''),
                'temp_f':       wx.get('temp_f', 0),
                'tailscale_ip': _ts_ip,
                'cpu_temp':     _get_cpu_temp(),
                'disk_pct':     _get_disk_pct(),
                'mem_free_mb':  mem.get('free'),
                'mem_total_mb': mem.get('total'),
                'data_age':        data_age,
                'brightness':      settings.get('brightness', 40),
                'display_mode':    settings.get('display_mode', 'auto'),
                'current_launch':  (_data_cache.get('launches') or [{}])[0].get('name', ''),
                'current_t0':      (_data_cache.get('launches') or [{}])[0].get('t0', ''),
            }, timeout=5)
        except Exception:
            pass
        time.sleep(60)

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
        elif cmd == 'refresh':
            _data_cache['fetched_at'] = 0
            threading.Thread(target=_refresh_all, daemon=True).start()
            print(f'[{_ts()}] Remote refresh triggered')
        elif cmd.startswith('set_brightness:'):
            try:
                val = max(20, min(100, int(cmd.split(':', 1)[1])))
                mapped = int(val * 2.55)
                bp = _backlight_path()
                if bp:
                    open(bp, 'w').write(str(mapped))
                s = _load_settings()
                s['brightness'] = val
                _save_settings(s)
                print(f'[{_ts()}] Brightness set to {val}% via relay')
            except Exception as e:
                print(f'[{_ts()}] set_brightness error: {e}')
        elif cmd.startswith('notify:'):
            parts = cmd.split(':', 1)[1].split('|', 1)
            title = parts[0] if parts else 'MISSION CONTROL'
            msg   = parts[1] if len(parts) > 1 else ''
            _notify_write(title, msg)
            print(f'[{_ts()}] Notification pushed via relay: {title}')
        elif cmd.startswith('set_mode:'):
            mode = cmd.split(':', 1)[1].strip()
            if mode in ('auto', 'always_on'):
                s = _load_settings()
                s['screen_mode'] = mode
                mapped = {'auto': {'auto_dim': True, 'display_mode': 'auto'},
                          'always_on': {'auto_dim': False, 'display_mode': 'bright'},
                          'sleep': {'auto_dim': True, 'display_mode': 'night'}}.get(mode, {})
                s.update(mapped)
                _save_settings(s)
                print(f'[{_ts()}] Display mode set to {mode} via relay')
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
            settings = _load_settings()
            display_mode = settings.get('display_mode', 'auto')

            # screen_mode drives all brightness decisions
            SLEEP_MIN    = 51
            screen_mode  = settings.get('screen_mode', 'auto')
            display_mode = settings.get('display_mode', 'auto')
            manual_pct   = int(settings.get('brightness', 40))
            manual_raw   = int(manual_pct * 2.55)

            # Wake override — user tapped screen, hold manual brightness until sunrise
            if _wake_until and time.time() < _wake_until:
                brightness = manual_raw
            elif screen_mode == 'always_on' or display_mode == 'bright':
                # Manual control — don't touch the backlight at all
                time.sleep(300)
                continue
            elif display_mode == 'night':
                # Sleep: respect manual pref but floor at SLEEP_MIN, cap at 40%
                brightness = max(SLEEP_MIN, min(manual_raw, 102))
            elif not settings.get('auto_dim', True):
                time.sleep(300)
                continue
            else:
                # Day: use manual brightness preference. Night (10pm-7am): dim to minimum.
                NIGHT_MIN = 51
                hour = datetime.now().hour
                if hour >= 22 or hour < 7:
                    brightness = NIGHT_MIN
                else:
                    brightness = manual_raw  # respect user's set brightness during the day

            if brightness is not None:
                print(f'[{_ts()}] Auto brightness → {brightness} (mode={display_mode})')
                try:
                    bp = _backlight_path()
                    if bp:
                        cur = int(open(bp).read().strip())
                        if abs(cur - brightness) > 5:
                            open(bp, 'w').write(str(brightness))
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

@app.route('/dashboard')
def dashboard_page():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'dashboard.html')

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
    fetched = _data_cache.get('fetched_at', 0); age_seconds = int(time.time() - fetched) if fetched > 0 else 0

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
        'liftoff_wx':    _data_cache.get('liftoff_wx'),
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
    fetched = _data_cache.get('fetched_at', 0); age_seconds = int(time.time() - fetched) if fetched > 0 else 0
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
    changed  = request.get_json() or {}
    settings = _load_settings()
    settings.update(changed)
    # Translate screen_mode → auto_dim + display_mode
    if 'screen_mode' in changed:
        mapped = _SCREEN_MODE_MAP.get(changed['screen_mode'], {})
        settings.update(mapped)
    _save_settings(settings)
    # Only clear weather cache when site changes
    if 'site' in changed:
        global _location_cache
        _location_cache = None
        with _weather_lock:
            _weather_cache['data']    = None
            _weather_cache['fetched'] = 0
    # Only touch backlight if screen_mode or brightness was explicitly in this request
    if 'screen_mode' in changed or 'brightness' in changed:
        sm  = settings.get('screen_mode', 'auto')
        pct = int(settings.get('brightness', 40))
        manual_raw = int(pct * 2.55)
        bp = _backlight_path()
        if bp:
            try:
                if sm == 'sleep':
                    open(bp, 'w').write(str(max(51, min(manual_raw, 102))))
                else:  # auto or always_on — restore manual preference
                    open(bp, 'w').write(str(manual_raw))
            except Exception:
                pass
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


@app.route('/api/log')
def api_log():
    """Return last N lines of server.log for Mission Control log viewer."""
    n = min(int(request.args.get('n', 80)), 200)
    try:
        lines = open('/home/pi/server.log').readlines()
        return jsonify({'lines': [l.rstrip() for l in lines[-n:]]})
    except Exception as e:
        return jsonify({'lines': [], 'error': str(e)})


# ── Wake override — tells auto_brightness to hold manual brightness after tap ──

@app.route('/api/wake', methods=['POST'])
def set_wake():
    global _wake_until
    _wake_until = float((request.get_json() or {}).get('until', 0))
    return jsonify({'ok': True})


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

def _nm_client():
    """Return a libnm NM.Client instance, or None if unavailable."""
    try:
        import gi
        gi.require_version('NM', '1.0')
        from gi.repository import NM
        return NM.Client.new(None)
    except Exception:
        return None

def _nm_wifi_device(client=None):
    """Return the first WiFi device from NM client."""
    try:
        import gi
        gi.require_version('NM', '1.0')
        from gi.repository import NM
        c = client or _nm_client()
        if not c: return None
        for dev in c.get_devices():
            if dev.get_device_type() == NM.DeviceType.WIFI:
                return dev
    except Exception:
        pass
    return None

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
        import gi
        gi.require_version('NM', '1.0')
        from gi.repository import NM
        client = NM.Client.new(None)
        dev = _nm_wifi_device(client)
        if not dev:
            return jsonify({'networks': [], 'error': 'No WiFi device'})
        dev.request_scan(None)
        time.sleep(4)
        networks = []
        seen = set()
        for ap in sorted(dev.get_access_points(), key=lambda a: -a.get_strength()):
            raw = ap.get_ssid()
            if not raw: continue
            try: ssid = raw.get_data().decode('utf-8', errors='replace').strip()
            except: continue
            if not ssid or ssid in seen: continue
            seen.add(ssid)
            freq = ap.get_frequency()
            rsn  = ap.get_rsn_flags()
            wpa  = ap.get_wpa_flags()
            KEY_MGMT_8021X = 0x200  # NM_80211_AP_SEC_KEY_MGMT_802_1X
            if (rsn & KEY_MGMT_8021X) or (wpa & KEY_MGMT_8021X):
                sec = 'Enterprise'
            elif rsn or wpa:
                sec = 'WPA2'
            else:
                sec = 'Open'
            networks.append({'ssid': ssid, 'band': '5GHz' if freq >= 5000 else '2.4GHz', 'security': sec})
        return jsonify({'networks': networks})
    except Exception as e:
        # Fallback to nmcli
        try:
            subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'], capture_output=True, timeout=10)
            result = subprocess.check_output(['nmcli', '-t', '-f', 'SSID,FREQ,SECURITY', 'dev', 'wifi', 'list'], text=True, timeout=15)
            networks = []
            seen = set()
            for line in result.strip().split('\n'):
                parts = line.split(':')
                ssid = parts[0].strip() if parts else ''
                if not ssid or ssid in seen: continue
                seen.add(ssid)
                freq = parts[1].strip() if len(parts) > 1 else ''
                sec  = parts[2].strip() if len(parts) > 2 else ''
                networks.append({'ssid': ssid, 'band': '5GHz' if freq.startswith('5') else '2.4GHz', 'security': sec})
            return jsonify({'networks': networks})
        except Exception as e2:
            return jsonify({'networks': [], 'error': str(e2)})

@app.route('/api/wifi/current')
def wifi_current():
    try:
        import gi
        gi.require_version('NM', '1.0')
        from gi.repository import NM
        client = NM.Client.new(None)
        active = client.get_primary_connection()
        if active and active.get_connection_type() == '802-11-wireless':
            dev = active.get_devices()
            if dev:
                wifi_dev = dev[0]
                ap = wifi_dev.get_active_access_point()
                if ap and ap.get_ssid():
                    ssid = ap.get_ssid().get_data().decode('utf-8', errors='replace').strip()
                    return jsonify({'ssid': ssid})
        return jsonify({'ssid': ''})
    except Exception:
        # Fallback to nmcli
        try:
            result = subprocess.run(['nmcli', '-t', '-f', 'NAME,TYPE,STATE', 'con', 'show', '--active'],
                                    capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                parts = line.split(':')
                if len(parts) >= 3 and '802-11-wireless' in parts[1] and 'activated' in parts[2]:
                    info = subprocess.run(['nmcli', '-t', '-f', '802-11-wireless.ssid', 'con', 'show', parts[0]],
                                          capture_output=True, text=True, timeout=5)
                    for s in info.stdout.split('\n'):
                        if '802-11-wireless.ssid:' in s:
                            return jsonify({'ssid': s.split(':', 1)[1].strip()})
        except Exception:
            pass
        return jsonify({'ssid': ''})

@app.route('/api/wifi/restart', methods=['POST'])
def wifi_restart():
    """Restart NetworkManager — clears stuck state without full reboot."""
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', 'NetworkManager'],
                       timeout=15, check=True)
        print(f'[{_ts()}] NetworkManager restarted via WiFi page')
        return jsonify({'ok': True})
    except Exception as e:
        print(f'[{_ts()}] NetworkManager restart failed: {e}')
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/wifi/connect', methods=['POST'])
def wifi_connect():
    data      = request.get_json() or {}
    ssid      = data.get('ssid', '')
    password  = data.get('password', '')
    is_open   = data.get('open', False)
    is_hidden = data.get('hidden', False)
    print(f'[{_ts()}] WiFi connect: ssid="{ssid}" pw_len={len(password)} open={is_open} hidden={is_hidden}')

    if not ssid:
        return jsonify({'ok': False, 'error': 'No network selected'})
    if not is_open and not password:
        return jsonify({'ok': False, 'error': 'No password provided'})

    try:
        import gi
        gi.require_version('NM', '1.0')
        from gi.repository import NM, GLib

        client = NM.Client.new(None)
        dev = _nm_wifi_device(client)
        if not dev:
            return jsonify({'ok': False, 'error': 'No WiFi device found'})

        # Build connection object
        conn = NM.SimpleConnection.new()

        s_con = NM.SettingConnection.new()
        s_con.set_property(NM.SETTING_CONNECTION_ID, 'rangetrack-wifi')
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, '802-11-wireless')
        s_con.set_property(NM.SETTING_CONNECTION_AUTOCONNECT, True)
        conn.add_setting(s_con)

        s_wifi = NM.SettingWireless.new()
        s_wifi.set_property(NM.SETTING_WIRELESS_SSID, GLib.Bytes.new(ssid.encode('utf-8')))
        s_wifi.set_property(NM.SETTING_WIRELESS_MODE, 'infrastructure')
        if is_hidden:
            s_wifi.set_property(NM.SETTING_WIRELESS_HIDDEN, True)
        conn.add_setting(s_wifi)

        if not is_open:
            s_sec = NM.SettingWirelessSecurity.new()
            s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, 'wpa-psk')
            s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, password)
            conn.add_setting(s_sec)

        s_ip4 = NM.SettingIP4Config.new()
        s_ip4.set_property(NM.SETTING_IP_CONFIG_METHOD, 'auto')
        conn.add_setting(s_ip4)

        s_ip6 = NM.SettingIP6Config.new()
        s_ip6.set_property(NM.SETTING_IP_CONFIG_METHOD, 'auto')
        conn.add_setting(s_ip6)

        # Activate with GLib mainloop
        loop   = GLib.MainLoop()
        result = {'active': None, 'error': None}

        def on_done(src, res, _):
            try:
                result['active'] = client.add_and_activate_connection2_finish(res)
            except Exception as e:
                result['error'] = str(e)
            loop.quit()

        client.add_and_activate_connection2(conn, dev, None, 0, None, None, on_done, None)
        GLib.timeout_add_seconds(35, loop.quit)
        loop.run()

        if result['error']:
            print(f'[{_ts()}] libnm error: {result["error"]}')
            return jsonify({'ok': False, 'error': result['error']})

        if not result['active']:
            return jsonify({'ok': False, 'error': 'Connection timed out'})

        # Poll for activation
        for _ in range(30):
            state = result['active'].get_state()
            reason_val = result['active'].get_state_reason()
            print(f'[{_ts()}] NM state={state} reason={reason_val}')
            if state == NM.ActiveConnectionState.ACTIVATED:
                _data_cache['fetched_at'] = 0
                return jsonify({'ok': True})
            if state == NM.ActiveConnectionState.DEACTIVATED:
                reasons = {
                    NM.ActiveConnectionStateReason.NO_SECRETS: 'Wrong password',
                    NM.ActiveConnectionStateReason.AUTH_SUPPLICANT_FAILED: 'Authentication failed — wrong password?',
                    NM.ActiveConnectionStateReason.IP_CONFIG_UNAVAILABLE: 'Connected but no IP — router issue',
                    NM.ActiveConnectionStateReason.CONNECT_TIMEOUT: 'Connection timed out — move closer',
                }
                msg = reasons.get(reason_val, f'Connection failed (reason {reason_val})')
                return jsonify({'ok': False, 'error': msg})
            time.sleep(1)

        return jsonify({'ok': False, 'error': 'Connection timed out'})

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
