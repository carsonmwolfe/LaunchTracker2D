"""Tests for how a failed WiFi connect is classified and worded.
    python3 tests/test_wifi_messages.py

server.py isn't imported (it starts the app); the classifier and its marker lists
are lifted out with ast and run on their own. The wifi.html message mapping is run
through JavaScriptCore when available (macOS); skipped elsewhere.
"""
import ast
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PHASE2 = HERE.parent
FIX = HERE / 'fixtures'

_src = (PHASE2 / 'server.py').read_text()
_want = {'_WIFI_BAD_KEY_MARKERS', '_WIFI_NO_CONNECT_MARKERS', '_classify_wifi_failure'}
_nodes = [n for n in ast.parse(_src).body
          if (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in _want for t in n.targets))
          or (isinstance(n, ast.FunctionDef) and n.name in _want)]
_ns = {}
exec(compile(ast.Module(body=_nodes, type_ignores=[]), 'server.py', 'exec'), _ns)
classify = _ns['_classify_wifi_failure']

NMCLI_SECRETS = "Error: Connection activation failed: (7) Secrets were required, but not provided."


class Classify(unittest.TestCase):
    def test_real_stuck_chip_log_is_not_a_password_problem(self):
        log = (FIX / 'wifi_stuck_field_unit_20261025.log').read_text()
        self.assertIn('status_code=16', log)          # sanity: fixture is what we think
        self.assertEqual(classify(NMCLI_SECRETS, log), 'no_connect')

    def test_wrong_password_log_is_a_password_problem(self):
        log = (FIX / 'wifi_wrong_password_constructed.log').read_text()
        self.assertEqual(classify(NMCLI_SECRETS, log), 'wrong_password')

    def test_each_wrong_key_marker_alone(self):
        for line in ('wlan0: WPA: 4-Way Handshake failed - pre-shared key may be incorrect',
                     'CTRL-EVENT-SSID-TEMP-DISABLED id=0 ssid="X" auth_failures=1 duration=10 reason=WRONG_KEY',
                     'device (wlan0): Activation: (wifi) disconnected during association, asking for new key'):
            with self.subTest(line=line):
                self.assertEqual(classify('', line), 'wrong_password')

    def test_each_no_connect_marker_alone(self):
        for line in ('device (wlan0): Activation: (wifi) association took too long',
                     'wlan0: CTRL-EVENT-ASSOC-REJECT bssid=00:00:00:00:00:00 status_code=16',
                     'wlan0: CTRL-EVENT-AUTH-REJECT 02:00:00:00:00:b8 auth_type=0 status_code=1',
                     'CTRL-EVENT-SSID-TEMP-DISABLED id=0 ssid="HomeNet 2.4" auth_failures=1 duration=10 reason=CONN_FAILED'):
            with self.subTest(line=line):
                self.assertEqual(classify(NMCLI_SECRETS, line), 'no_connect')

    def test_timeouts_then_key_rejected_means_wrong_password(self):
        # The chip connected on a later try and the key was then rejected.
        log = ('wlan0: CTRL-EVENT-ASSOC-REJECT bssid=00:00:00:00:00:00 status_code=16\n'
               'wlan0: Associated with 02:00:00:00:00:b8\n'
               'wlan0: WPA: 4-Way Handshake failed - pre-shared key may be incorrect\n')
        self.assertEqual(classify(NMCLI_SECRETS, log), 'wrong_password')

    def test_conn_failed_is_never_read_as_wrong_key(self):
        self.assertNotEqual(classify('', 'reason=CONN_FAILED'), 'wrong_password')

    def test_no_log_falls_back_to_previous_behaviour(self):
        self.assertEqual(classify(NMCLI_SECRETS, ''), 'wrong_password')
        self.assertEqual(classify(NMCLI_SECRETS, None), 'wrong_password')
        self.assertEqual(classify('Error: No network with SSID "X" found.', ''), 'other')
        self.assertEqual(classify('', ''), 'other')


class ConnectHandler(unittest.TestCase):
    def test_old_keyword_guess_is_gone_and_classifier_used_twice(self):
        body = _src[_src.index('def wifi_connect():'):_src.index("@app.route('/api/wifi/forget'")]
        self.assertNotIn('wrong_pw = any(', body)
        self.assertEqual(body.count('_classify_wifi_failure('), 2)
        self.assertIn("not a password problem", body)


class ScreenMessages(unittest.TestCase):
    JSC = '/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc'

    def friendly(self, raws):
        html = (PHASE2 / 'static' / 'wifi.html').read_text()
        start = html.index('function friendlyError(raw)')
        depth, i = 0, html.index('{', start)
        while True:                       # find the function's closing brace
            depth += {'{': 1, '}': -1}.get(html[i], 0)
            i += 1
            if depth == 0:
                break
        js = html[start:i] + '\nprint(JSON.stringify(%s.map(friendlyError)));' % json.dumps(raws)
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
            f.write(js)
        out = subprocess.run([self.JSC, f.name], capture_output=True, text=True, timeout=20)
        return json.loads(out.stdout)

    def setUp(self):
        if not pathlib.Path(self.JSC).exists() and not shutil.which('jsc'):
            self.skipTest('JavaScriptCore not available')

    def test_mapping(self):
        got = self.friendly([
            "Couldn't connect — not a password problem",
            'Wrong password — the router rejected the key',
            NMCLI_SECRETS,
            'Connection timed out — check password and signal',
            '',
        ])
        self.assertTrue(got[0].startswith("Couldn't connect — not a password problem"), got[0])
        self.assertNotIn('Wrong password', got[0])
        self.assertEqual(got[1], 'Wrong password — check carefully and retry')
        self.assertEqual(got[2], 'Wrong password — check carefully and retry')   # unchanged
        self.assertEqual(got[3], 'Timed out — move closer to the router and retry')   # unchanged
        self.assertEqual(got[4], "Couldn't connect — check the password and signal, then retry")


if __name__ == '__main__':
    unittest.main(verbosity=2)
