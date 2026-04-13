import requests, time, threading
from flask import Flask, jsonify, request

app = Flask(__name__)

_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 300  # 5 minutes

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

# ── Unit tracking ──────────────────────────────────────────────────────────────

_units = {}
_commands = {}   # unit_id -> list of pending command dicts
_acks    = {}    # unit_id -> list of {command, ts}
_cmd_lock = threading.Lock()

UNIT_TTL = 3600  # drop units not seen in 1h

@app.route('/api/unit/ping', methods=['POST'])
def unit_ping():
    data = request.get_json() or {}
    unit_id = data.get('unit_id', 'unknown')
    now = time.time()
    # Expire stale units
    stale = [k for k, v in _units.items() if now - v.get('last_seen', 0) > UNIT_TTL]
    for k in stale:
        del _units[k]
    _units[unit_id] = {**data, 'last_seen': now}
    return jsonify({'ok': True})

@app.route('/api/units')
def units():
    now = time.time()
    active = {k: v for k, v in _units.items() if now - v.get('last_seen', 0) < UNIT_TTL}
    return jsonify(active)

@app.route('/api/unit/<unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    _units.pop(unit_id, None)
    return jsonify({'ok': True})

# ── Command queue ──────────────────────────────────────────────────────────────

@app.route('/api/unit/command', methods=['POST'])
def send_command():
    """Dashboard posts a command for a specific unit."""
    data = request.get_json() or {}
    unit_id = data.get('unit_id')
    cmd     = data.get('command')  # 'restart', 'update', 'reboot'
    if not unit_id or not cmd:
        return jsonify({'ok': False, 'error': 'unit_id and command required'}), 400
    with _cmd_lock:
        if unit_id not in _commands:
            _commands[unit_id] = []
        _commands[unit_id].append({'command': cmd, 'queued_at': time.time()})
    print(f"Command '{cmd}' queued for {unit_id}")
    return jsonify({'ok': True})

@app.route('/api/unit/commands/<unit_id>')
def get_commands(unit_id):
    """Pi polls this to get pending commands."""
    with _cmd_lock:
        cmds = _commands.pop(unit_id, [])
    return jsonify(cmds)

@app.route('/api/unit/ack', methods=['POST'])
def unit_ack():
    """Pi confirms a command was received and is executing."""
    data    = request.get_json() or {}
    unit_id = data.get('unit_id')
    cmd     = data.get('command')
    if unit_id and cmd:
        _acks.setdefault(unit_id, []).append({'command': cmd, 'ts': time.time()})
    return jsonify({'ok': True})

@app.route('/api/unit/acks/<unit_id>')
def get_acks(unit_id):
    """Dashboard polls this; clears on read."""
    return jsonify(_acks.pop(unit_id, []))

@app.after_request
def add_cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return r

if __name__ == '__main__':
    threading.Thread(target=_bg_refresh, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
