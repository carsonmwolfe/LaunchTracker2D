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

LL2_BASE = "https://ll.thespacedevs.com/2.2.0"
WEATHER_BASE = "https://api.open-meteo.com/v1"

SITES = {
    'cape':       {'lat': 28.5623, 'lon': -80.5774},
    'vandenberg': {'lat': 34.7420, 'lon': -120.5724},
}

def _fetch_launches():
    try:
        r = requests.get(f"{LL2_BASE}/launch/upcoming/",
            params={'limit': 10, 'format': 'json'},
            timeout=15)
        return r.json().get('results', [])
    except Exception as e:
        print(f"Launch fetch error: {e}")
        return None

def _fetch_weather(lat, lon):
    try:
        r = requests.get(f"{WEATHER_BASE}/forecast", params={
            'latitude': lat, 'longitude': lon,
            'current': 'temperature_2m,windspeed_10m,cloudcover,weathercode',
            'daily': 'sunrise,sunset',
            'timezone': 'auto', 'forecast_days': 1
        }, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None

def _refresh():
    with _cache_lock:
        now = time.time()
        if now - _cache.get('_fetched_at', 0) < CACHE_TTL:
            return
        launches = _fetch_launches()
        if launches is not None:
            launches = _apply_t0_history(launches)
            _cache['launches'] = launches
        for site_id, site in SITES.items():
            wx = _fetch_weather(site['lat'], site['lon'])
            if wx:
                _cache[f'weather_{site_id}'] = wx
        _cache['_fetched_at'] = now
        print(f"Cache refreshed at {time.strftime('%H:%M:%S')}")

def _bg_refresh():
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
    site = request.args.get('site', 'cape')
    _refresh()
    return jsonify(_cache.get(f'weather_{site}', {}))

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

if __name__ == '__main__':
    threading.Thread(target=_bg_refresh, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
