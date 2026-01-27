#!/usr/bin/env python3
"""
API client for fetching rocket launch data.
"""

import requests
from datetime import datetime, timezone


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
        
        print(f"\n=== API returned {len(launches)} launches ===")
        
        # Filter to only upcoming launches (not already completed)
        filtered_launches = []
        
        for launch in launches:
            name = launch.get('name', 'Unknown')
            
            # Get status
            status = launch.get('status', {})
            status_id = status.get('id', 0)
            status_name = status.get('name', 'Unknown')
            
            # Get result (1=success, 2=failure, 3=partial, null=not launched, -1=scrubbed/TBD)
            result = launch.get('result')
            
            # Get launch time
            launch_time_str = launch.get('t0') or launch.get('win_open')
            
            print(f"\n{name}")
            print(f"  Status: {status_name} (id={status_id})")
            print(f"  Result: {result}")
            print(f"  T0: {launch_time_str}")
            
            # Skip if launch has a POSITIVE result (1, 2, 3 = already completed)
            if result is not None and result > 0:
                print(f"  -> SKIPPING (already completed with result={result})")
                continue
            
            # Skip if status is "Launch Successful" 
            if status_id == 3:
                print(f"  -> SKIPPING (status indicates completed)")
                continue
            
            # This is an upcoming launch
            print(f"  -> KEEPING (upcoming)")
            filtered_launches.append(launch)
        
        print(f"\n=== Filtered to {len(filtered_launches)} upcoming launches ===\n")
        return filtered_launches
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
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