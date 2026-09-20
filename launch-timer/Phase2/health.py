#!/usr/bin/env python3
"""RangeTrack OS — Server watchdog. Restarts server.py if it stops responding."""

import sys
import os
import time
import subprocess
import urllib.request
from datetime import datetime

SERVER_SCRIPT = 'server.py'
PHASE2        = os.path.dirname(os.path.abspath(__file__))

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def is_server_running():
    try:
        urllib.request.urlopen('http://localhost:5001/', timeout=5)
        return True
    except Exception:
        return False

def restart_server():
    if os.path.exists('/tmp/rangetrack_update.lock'):
        print(f'[{ts()}] Update in progress — skipping restart.')
        return
    subprocess.run(['pkill', '-f', SERVER_SCRIPT], capture_output=True)
    time.sleep(2)
    with open('/home/pi/server.log', 'a') as f:
        subprocess.Popen(['python3', SERVER_SCRIPT], cwd=PHASE2, stdout=f, stderr=subprocess.STDOUT)
    print(f'[{ts()}] Server restarted.')

if __name__ == '__main__':
    if not is_server_running():
        restart_server()
