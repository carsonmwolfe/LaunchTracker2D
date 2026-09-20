#!/usr/bin/env python3
"""
API client for fetching rocket launch data.
"""

import requests
from datetime import datetime, timezone


def _ts():
    """Return a compact timestamp string for log lines."""
    return datetime.now().strftime("%H:%M:%S")


def fetch_launches(num_launches=5):
    """Fetch the next upcoming rocket launches.
    
    Always fetches fresh data from the API.
    Returns launches that haven't completed yet.
    """
    url = f"https://fdo.rocketlaunch.live/json/launches/next/{num_launches}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        launches = data.get('result', [])
        
        # Filter to only upcoming launches (not already completed)
        filtered_launches = []
        skipped = []
        
        for launch in launches:
            name = launch.get('name', 'Unknown')
            
            # Get status
            status = launch.get('status', {})
            status_id = status.get('id', 0)
            status_name = status.get('name', 'Unknown')
            
            # Get result (1=success, 2=failure, 3=partial, null=not launched, -1=scrubbed/TBD)
            result = launch.get('result')
            
            # Skip if launch has a POSITIVE result (1, 2, 3 = already completed)
            if result is not None and result > 0:
                skipped.append(f"{name} (completed)")
                continue
            
            # Skip if status is "Launch Successful"
            if status_id == 3:
                skipped.append(f"{name} (status=completed)")
                continue
            
            filtered_launches.append(launch)
        
        # Single condensed summary line
        print(f"[{_ts()}] Launches fetched: {len(filtered_launches)} upcoming"
              + (f", {len(skipped)} skipped" if skipped else ""))
        
        # Print upcoming launches in a compact table
        for i, launch in enumerate(filtered_launches):
            t0 = launch.get('t0') or launch.get('win_open') or 'TBD'
            vehicle = launch.get('vehicle', {}).get('name', 'Unknown')
            status_name = launch.get('status', {}).get('name', '?')
            marker = ">>>" if i == 0 else "   "
            print(f"  {marker} [{i+1}] {launch.get('name', 'Unknown')}")
            print(f"         Vehicle: {vehicle} | Status: {status_name} | T0: {t0}")
        
        return filtered_launches
        
    except requests.exceptions.RequestException as e:
        print(f"[{_ts()}] ERROR fetching launch data: {e}")
        return []


def get_countdown(launch_time_iso):
    """Calculate countdown to launch."""
    if not launch_time_iso:
        return None
    
    try:
        launch_time = datetime.fromisoformat(launch_time_iso.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = launch_time - now
        
        if delta.total_seconds() < 0:
            return "LAUNCHED"
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'total_seconds': delta.total_seconds()
        }
    except:
        return None