"""Tests for the WiFi screen's connect handler (server.py wifi_connect).
    python3 tests/test_wifi_connect.py

server.py isn't imported (it starts the app); wifi_connect and the helpers it uses
are lifted out with ast and run against fakes: Flask's request/jsonify, the WiFi
log, and a subprocess.run that plays nmcli and journalctl. The fake reproduces the
NetworkManager 1.52 behaviour that broke the screen on a field unit (2026-11-03):
`nmcli dev wifi connect` for a network whose saved profile is in use fails at once
with "802-11-wireless-security.key-mgmt: property is missing".
"""
import ast
import pathlib
import types
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PHASE2 = HERE.parent

_src = (PHASE2 / 'server.py').read_text()
_want = {'_WIFI_BAD_KEY_MARKERS', '_WIFI_NO_CONNECT_MARKERS', '_classify_wifi_failure',
         '_wifi_log_since', 'wifi_connect'}
_nodes = [n for n in ast.parse(_src).body
          if (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in _want for t in n.targets))
          or (isinstance(n, ast.FunctionDef) and n.name in _want)]
_code = compile(ast.Module(body=_nodes, type_ignores=[]), 'server.py', 'exec')

MISSING = 'Error: 802-11-wireless-security.key-mgmt: property is missing.'
DISPATCHER = ("<warn>  [1.0] dispatcher: (28) /etc/NetworkManager/dispatcher.d/99-wifi-powersave-off "
              "failed (failed): Script '/etc/NetworkManager/dispatcher.d/99-wifi-powersave-off' exited with status 1")


def _res(rc=0, out='', err=''):
    return types.SimpleNamespace(returncode=rc, stdout=out, stderr=err)


class FakeNM:
    """Saved profiles and what nmcli does with them."""

    def __init__(self):
        self.profiles = {}       # uuid -> {'id', 'ssid', 'psk', 'active'}
        self.calls = []
        self.journal = ''
        self.up_ok = True        # does an activation succeed?
        self.up_err = 'Error: Connection activation failed: (53) The Wi-Fi network could not be found.'
        self._n = 0

    def add(self, uuid, name, ssid, psk='saved-pass', active=False):
        self.profiles[uuid] = {'id': name, 'ssid': ssid, 'psk': psk, 'active': active}

    def ran(self, *words):
        return [c for c in self.calls if all(w in c for w in words)]

    def run(self, cmd, capture_output=False, text=False, timeout=None, check=False):
        self.calls.append(list(cmd))
        a = [c for c in cmd if c != 'sudo']
        if a[0] == 'journalctl':
            return _res(out=self.journal)
        assert a[0] == 'nmcli', cmd
        a = a[1:]
        esc = lambda s: s.replace('\\', '\\\\').replace(':', '\\:')
        if a == ['-t', '-f', 'NAME,DEVICE,STATE', 'con', 'show', '--active']:
            return _res(out='\n'.join(f'{esc(p["id"])}:wlan0:activated' for p in self.profiles.values() if p['active']))
        if a == ['-t', '-f', 'UUID', 'con', 'show', '--active']:
            return _res(out='\n'.join(u for u, p in self.profiles.items() if p['active']))
        if a == ['-t', '-f', 'UUID,TYPE', 'con', 'show']:
            return _res(out='\n'.join([f'{u}:802-11-wireless' for u in self.profiles] + ['lo-uuid:loopback']))
        if len(a) == 6 and a[0] == '-g' and a[2:5] == ['con', 'show', 'uuid']:
            p = self.profiles[a[5]]
            return _res(out=esc({'connection.id': p['id'], '802-11-wireless.ssid': p['ssid']}[a[1]]) + '\n')
        if a[:3] == ['con', 'delete', 'uuid']:
            del self.profiles[a[3]]
            return _res(out=f'Connection successfully deleted ({a[3]}).')
        if a[:3] == ['con', 'modify', 'uuid'] and a[4] == '802-11-wireless-security.psk':
            self.profiles[a[3]]['psk'] = a[5]
            return _res()
        if a[:5] == ['--wait', '25', 'con', 'up', 'uuid']:
            if not self.up_ok:
                return _res(4, err=self.up_err)
            for p in self.profiles.values():
                p['active'] = False
            self.profiles[a[5]]['active'] = True
            return _res(out='Connection successfully activated (D-Bus active path: /org/freedesktop/NetworkManager/ActiveConnection/7)')
        if a[:3] == ['dev', 'wifi', 'connect']:
            ssid = a[3]
            if any(p['active'] and p['ssid'] == ssid for p in self.profiles.values()):
                return _res(1, err=MISSING)                 # the NetworkManager 1.52 behaviour
            if not self.up_ok:
                return _res(4, err=self.up_err)
            self._n += 1
            uuid = f'new-{self._n}'
            self.add(uuid, ssid, ssid, a[5] if 'password' in a else '', active=True)
            return _res(out=f"Device 'wlan0' successfully activated with '{uuid}'.")
        if a == ['dev', 'wifi', 'rescan']:
            return _res()
        raise AssertionError(f'unexpected command {cmd}')


def connect(nm, **payload):
    """Run wifi_connect with payload against nm. Returns (response, log lines)."""
    log = []
    ns = {
        'app': types.SimpleNamespace(route=lambda *a, **k: (lambda f: f)),
        'request': types.SimpleNamespace(get_json=lambda: payload),
        'jsonify': lambda d: d,
        '_wlog': log.append,
        '_data_cache': {},
        'subprocess': types.SimpleNamespace(run=nm.run, TimeoutExpired=TimeoutError),
        'time': types.SimpleNamespace(time=lambda: 1_000_000.0, sleep=lambda s: None),
    }
    exec(_code, ns)
    return ns['wifi_connect'](), log


class WifiConnect(unittest.TestCase):
    def test_fake_reproduces_the_field_bug(self):
        nm = FakeNM(); nm.add('u1', 'HomeNet', 'HomeNet', active=True)
        r = nm.run(['sudo', 'nmcli', 'dev', 'wifi', 'connect', 'HomeNet', 'password', 'x'])
        self.assertEqual(r.stderr, MISSING)

    def test_network_already_in_use_reuses_its_saved_profile(self):
        # The field case: NetworkManager was retrying the network when the user typed
        # the password into the WiFi screen.
        nm = FakeNM(); nm.add('u1', 'HomeNet', 'HomeNet', psk='old-pass', active=True)
        resp, log = connect(nm, ssid='HomeNet', password='new-pass')
        self.assertTrue(resp['ok'], log)
        self.assertEqual(nm.profiles['u1']['psk'], 'new-pass')
        self.assertTrue(nm.ran('modify', 'u1', '802-11-wireless-security.psk'))
        self.assertTrue(nm.ran('up', 'u1'))
        self.assertFalse(nm.ran('wifi', 'connect'))
        self.assertIn('u1', nm.profiles)                    # kept, with its settings

    def test_saved_but_not_in_use_is_deleted_then_connected_fresh(self):
        nm = FakeNM(); nm.add('u2', 'HomeNet', 'HomeNet', psk='stale')
        resp, log = connect(nm, ssid='HomeNet', password='new-pass')
        self.assertTrue(resp['ok'], log)
        self.assertNotIn('u2', nm.profiles)
        self.assertEqual(len(nm.ran('wifi', 'connect', 'HomeNet')), 1)

    def test_new_network(self):
        nm = FakeNM()
        resp, log = connect(nm, ssid='CafeNet', password='cafe-pass')
        self.assertTrue(resp['ok'], log)
        self.assertEqual(len(nm.ran('wifi', 'connect', 'CafeNet')), 1)

    def test_live_profile_for_another_network_is_left_alone(self):
        nm = FakeNM(); nm.add('u3', 'Phone Hotspot', 'Phone Hotspot', active=True)
        resp, log = connect(nm, ssid='HomeNet', password='new-pass')
        self.assertTrue(resp['ok'], log)
        self.assertFalse(nm.ran('delete'))
        self.assertFalse(nm.ran('modify'))
        self.assertEqual(len(nm.ran('wifi', 'connect', 'HomeNet')), 1)

    def test_open_network_in_use_is_just_brought_up(self):
        nm = FakeNM(); nm.add('u4', 'Cafe', 'Cafe', psk='', active=True)
        resp, log = connect(nm, ssid='Cafe', open=True)
        self.assertTrue(resp['ok'], log)
        self.assertFalse(nm.ran('modify'))
        self.assertTrue(nm.ran('up', 'u4'))

    def test_name_with_colon_still_matched(self):
        nm = FakeNM(); nm.add('u5', 'Weird:Net', 'Weird:Net', active=True)
        resp, log = connect(nm, ssid='Weird:Net', password='pw-12345')
        self.assertTrue(resp['ok'], log)
        self.assertTrue(nm.ran('up', 'u5'))
        self.assertFalse(nm.ran('wifi', 'connect'))

    def test_in_use_network_that_wont_connect_says_not_a_password_problem(self):
        nm = FakeNM(); nm.add('u1', 'HomeNet', 'HomeNet', active=True)
        nm.up_ok = False
        nm.journal = ('device (wlan0): Activation: (wifi) association took too long\n'
                      'wlan0: CTRL-EVENT-ASSOC-REJECT bssid=00:00:00:00:00:00 status_code=16\n' + DISPATCHER)
        resp, log = connect(nm, ssid='HomeNet', password='new-pass')
        self.assertFalse(resp['ok'])
        self.assertEqual(resp['kind'], 'no_connect')
        self.assertEqual(resp['error'], "Couldn't connect — not a password problem")
        self.assertEqual(len(nm.ran('up', 'u1')), 2)        # retried once
        self.assertTrue(nm.ran('rescan'))

    def test_error_shown_is_not_the_dispatcher_noise(self):
        nm = FakeNM(); nm.add('u1', 'HomeNet', 'HomeNet', active=True)
        nm.up_ok = False
        nm.up_err = 'Error: Connection activation failed: something unexpected'
        nm.journal = DISPATCHER
        resp, log = connect(nm, ssid='HomeNet', password='new-pass')
        self.assertFalse(resp['ok'])
        self.assertNotIn('dispatcher', resp['error'])
        self.assertIn('something unexpected', resp['error'])

    def test_password_never_logged(self):
        for setup in (lambda nm: nm.add('u1', 'HomeNet', 'HomeNet', active=True),
                      lambda nm: None):
            nm = FakeNM(); setup(nm)
            resp, log = connect(nm, ssid='HomeNet', password='s3cret-Pass!')
            self.assertTrue(resp['ok'], log)
            self.assertFalse([l for l in log if 's3cret-Pass!' in l], log)


if __name__ == '__main__':
    unittest.main(verbosity=2)
