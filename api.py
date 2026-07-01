import json, os, requests, time, threading
from flask import Flask, jsonify, request

app = Flask(__name__)

_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 300  # 5 minutes

# ── T0 slip history — tracks first-seen T0 per launch ID ─────────────────────
# Stored in memory; survives as long as the process runs on DO.
# All Pis share this so DELAYED badges are universal.
_t0_history = {}
_T0_HIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 't0_history_relay.json')

def _load_t0_history():
    global _t0_history
    try:
        with open(_T0_HIST_FILE) as f:
            _t0_history = json.load(f)
        print(f"T0 history loaded: {len(_t0_history)} entries")
    except Exception:
        _t0_history = {}

def _save_t0_history():
    try:
        with open(_T0_HIST_FILE, 'w') as f:
            json.dump(_t0_history, f)
    except Exception as e:
        print(f"T0 history save error: {e}")

def _apply_t0_history(launches):
    """Record first-seen T0 for each launch; attach original_t0 if T0 has slipped."""
    changed = False
    cutoff = time.time() - 30 * 86400  # prune entries older than 30 days
    for l in launches:
        lid = str(l.get('id', ''))
        net = (l.get('net') or '').strip()
        if not lid or not net:
            continue
        if lid not in _t0_history:
            _t0_history[lid] = {'t0': net, 'seen': time.time()}
            changed = True
        else:
            orig = _t0_history[lid]['t0']
            if orig != net:
                l['original_t0'] = orig
    # Prune old entries
    stale = [k for k, v in _t0_history.items() if v.get('seen', 0) < cutoff]
    if stale:
        for k in stale:
            del _t0_history[k]
        changed = True
    if changed:
        _save_t0_history()
    return launches

_load_t0_history()

LL2_BASE = "https://ll.thespacedevs.com/2.3.0"
WEATHER_BASE = "https://api.open-meteo.com/v1"

DEFAULT_LAT, DEFAULT_LON = 28.5623, -80.5774  # KSC fallback

_WIND_DIRS = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']
_WMO_LABELS = {
    0:'Clear sky',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',
    45:'Foggy',48:'Icy fog',51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',
    61:'Light rain',63:'Rain',65:'Heavy rain',80:'Light showers',81:'Showers',82:'Heavy showers',
    95:'Thunderstorm',96:'Thunderstorm w/ hail',99:'Thunderstorm w/ heavy hail',
}
_WMO_CONDITION = {
    0:'clear',1:'clear',2:'cloudy',3:'cloudy',45:'fog',48:'fog',
    51:'light_rain',53:'light_rain',55:'light_rain',61:'light_rain',
    63:'rain',65:'rain',80:'rain',81:'rain',82:'rain',
    95:'thunderstorm',96:'thunderstorm',99:'thunderstorm',
}

def _fetch_launches():
    try:
        r = requests.get(f"{LL2_BASE}/launches/upcoming/",
            params={'limit': 10, 'format': 'json'},
            timeout=15)
        r.raise_for_status()
        return r.json().get('results', [])
    except Exception as e:
        print(f"Launch fetch error: {e}")
        return None

def _fetch_year_launches():
    from datetime import datetime
    year_str = datetime.now().strftime('%Y-01-01')
    url = f"{LL2_BASE}/launches/?window_start__gte={year_str}&limit=100&ordering=window_start&format=json"
    all_results = []
    pages = 0
    while url and pages < 5:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 429:
                print(f"Year launches rate limited (page {pages+1})")
                break
            r.raise_for_status()
            payload = r.json()
            all_results.extend(payload.get('results', []))
            url = payload.get('next')
            pages += 1
            if url:
                time.sleep(2)
        except Exception as e:
            print(f"Year launches error (page {pages+1}): {e}")
            break
    print(f"Year launches: {len(all_results)} across {pages} page(s)")
    return all_results if all_results else None

def _fetch_events():
    try:
        r = requests.get(f"{LL2_BASE}/events/upcoming/",
            params={'limit': 5, 'format': 'json'}, timeout=15)
        r.raise_for_status()
        results = r.json().get('results', [])
        print(f"Events: {len(results)}")
        return results
    except Exception as e:
        print(f"Events fetch error: {e}")
        return None

def _get_pad_coords():
    """Return (lat, lon) of next upcoming launch pad, falling back to KSC."""
    for launch in (_cache.get('launches') or []):
        try:
            lat = float((launch.get('pad') or {}).get('latitude') or
                        launch.get('pad_lat') or '')
            lon = float((launch.get('pad') or {}).get('longitude') or
                        launch.get('pad_lon') or '')
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except (ValueError, TypeError):
            pass
    return DEFAULT_LAT, DEFAULT_LON

def _fetch_weather():
    """Fetch weather for the next launch pad and return normalized dict."""
    lat, lon = _get_pad_coords()
    try:
        r = requests.get(f"{WEATHER_BASE}/forecast", params={
            'latitude': lat, 'longitude': lon,
            'current': 'temperature_2m,relative_humidity_2m,precipitation,'
                       'weather_code,cloud_cover,wind_speed_10m,wind_direction_10m',
            'daily': 'sunrise,sunset',
            'temperature_unit': 'fahrenheit',
            'wind_speed_unit': 'mph',
            'timezone': 'auto',
            'forecast_days': 1,
        }, timeout=10)
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
            'pad_lat':     lat, 'pad_lon': lon,
        }
        print(f"Weather: {result['label']}, {temp_f}°F @ {lat:.3f},{lon:.3f}")
        return result
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None

WEATHER_TTL = 900   # 15 min
YEAR_TTL    = 3600  # 1 hour
EVENTS_TTL  = 1800  # 30 min

def _refresh():
    now = time.time()
    if now - _cache.get('_fetched_at', 0) < CACHE_TTL:
        return

    launches = _fetch_launches()

    wx = None
    if now - _cache.get('_wx_fetched_at', 0) >= WEATHER_TTL:
        wx = _fetch_weather()

    year = None
    if now - _cache.get('_year_fetched_at', 0) >= YEAR_TTL:
        year = _fetch_year_launches()

    events = None
    need_events = now - _cache.get('_events_fetched_at', 0) >= EVENTS_TTL
    if need_events:
        time.sleep(3)
        events = _fetch_events()

    with _cache_lock:
        now = time.time()
        if launches:
            launches = _apply_t0_history(launches)
            _cache['launches'] = launches
        if wx:
            _cache['weather'] = wx
            _cache['_wx_fetched_at'] = now
        if year:
            _cache['year_launches'] = year
            _cache['_year_fetched_at'] = now
        if need_events and events is not None:
            _cache['events'] = events
            _cache['_events_fetched_at'] = now
        _cache['_fetched_at'] = now
    print(f"Cache refreshed at {time.strftime('%H:%M:%S')}")

def _bg_refresh():
    time.sleep(10)  # startup delay — let gunicorn finish booting before hitting LL2
    while True:
        try:
            _refresh()
        except Exception as e:
            print(f"BG refresh error: {e}")
        time.sleep(60)

@app.route('/api/launches')
def launches():
    _refresh()
    return jsonify(_cache.get('launches', []))

@app.route('/api/weather')
def weather():
    _refresh()
    return jsonify(_cache.get('weather') or {})

@app.route('/api/launches/year')
def year_launches():
    _refresh()
    return jsonify(_cache.get('year_launches', []))

@app.route('/api/events')
def events_route():
    _refresh()
    return jsonify(_cache.get('events', []))

@app.route('/api/health')
def health():
    return jsonify({'ok': True, 'cached_at': _cache.get('_fetched_at', 0)})

# ── Unit tracking — file-backed so state survives restarts ───────────────────

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'relay_state.json')
_state_lock = threading.Lock()
UNIT_TTL    = 3600   # drop units not seen in 1h
CMD_TTL     = 300    # discard undelivered commands older than 5 min

def _load_state():
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {'units': {}, 'commands': {}, 'acks': {}}

def _save_state(state):
    try:
        with open(_STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"State save error: {e}")

@app.route('/api/unit/ping', methods=['POST'])
def unit_ping():
    data    = request.get_json() or {}
    unit_id = data.get('unit_id', 'unknown')
    now     = time.time()
    with _state_lock:
        s = _load_state()
        # Expire stale units
        s['units'] = {k: v for k, v in s['units'].items() if now - v.get('last_seen', 0) < UNIT_TTL}
        s['units'][unit_id] = {**data, 'last_seen': now}
        _save_state(s)
    return jsonify({'ok': True})

@app.route('/api/units')
def units():
    now = time.time()
    with _state_lock:
        s = _load_state()
    active = {k: v for k, v in s['units'].items() if now - v.get('last_seen', 0) < UNIT_TTL}
    return jsonify(active)

@app.route('/api/unit/<unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    with _state_lock:
        s = _load_state()
        s['units'].pop(unit_id, None)
        _save_state(s)
    return jsonify({'ok': True})

# ── Command queue — persisted so restarts don't drop pending commands ─────────

@app.route('/api/unit/command', methods=['POST'])
def send_command():
    data    = request.get_json() or {}
    unit_id = data.get('unit_id')
    cmd     = data.get('command')
    if not unit_id or not cmd:
        return jsonify({'ok': False, 'error': 'unit_id and command required'}), 400
    now = time.time()
    with _state_lock:
        s = _load_state()
        s['commands'].setdefault(unit_id, [])
        # Drop expired commands then append new one
        s['commands'][unit_id] = [c for c in s['commands'][unit_id] if now - c.get('queued_at', 0) < CMD_TTL]
        s['commands'][unit_id].append({'command': cmd, 'queued_at': now})
        _save_state(s)
    print(f"Command '{cmd}' queued for {unit_id}")
    return jsonify({'ok': True})

@app.route('/api/unit/commands/<unit_id>')
def get_commands(unit_id):
    now = time.time()
    with _state_lock:
        s    = _load_state()
        cmds = [c for c in s['commands'].pop(unit_id, []) if now - c.get('queued_at', 0) < CMD_TTL]
        _save_state(s)
    return jsonify(cmds)

@app.route('/api/unit/ack', methods=['POST'])
def unit_ack():
    data    = request.get_json() or {}
    unit_id = data.get('unit_id')
    cmd     = data.get('command')
    if unit_id and cmd:
        with _state_lock:
            s = _load_state()
            s['acks'].setdefault(unit_id, []).append({'command': cmd, 'ts': time.time()})
            _save_state(s)
    return jsonify({'ok': True})

@app.route('/api/unit/acks/<unit_id>')
def get_acks(unit_id):
    with _state_lock:
        s    = _load_state()
        acks = s['acks'].pop(unit_id, [])
        _save_state(s)
    return jsonify(acks)

@app.after_request
def add_cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return r

threading.Thread(target=_bg_refresh, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
