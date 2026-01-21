#!/usr/bin/env python3
"""
API client for fetching rocket launch data.
"""

import requests
from datetime import datetime, timezone


def fetch_launches(num_launches=1):
    """Fetch the next upcoming rocket launches."""
    url = f"https://fdo.rocketlaunch.live/json/launches/next/{num_launches}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('result', [])
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