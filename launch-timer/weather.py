#!/usr/bin/env python3
"""
Weather system for Cape Canaveral, Florida.
Fetches real weather data and provides visual effects.
"""

import requests
import random
from datetime import datetime


class WeatherSystem:
    """Manages real-time weather data and visual effects."""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.current_weather = None
        self.weather_condition = "clear"  # clear, cloudy, rain, thunderstorm, fog
        self.rain_drops = []
        self.lightning_flash = False
        self.lightning_timer = 0
        
    def fetch_weather(self):
        """Fetch current weather for Cape Canaveral, FL using Open-Meteo API.
        
        Open-Meteo is free, no API key required, and far more reliable than wttr.in.
        Uses WMO weather interpretation codes.
        Cape Canaveral: 28.3922N, -80.6077W
        """
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")

        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=28.3922&longitude=-80.6077"
                "&current=temperature_2m,relative_humidity_2m,precipitation,"
                "weather_code,cloud_cover,wind_speed_10m,wind_direction_10m"
                "&temperature_unit=fahrenheit"
                "&wind_speed_unit=mph"
                "&timezone=America%2FNew_York"
            )

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            current = data['current']

            # Convert wind direction degrees to cardinal
            wind_deg = current.get('wind_direction_10m', 0)
            directions = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
                          'S','SSW','SW','WSW','W','WNW','NW','NNW']
            wind_dir = directions[int((wind_deg + 11.25) / 22.5) % 16]

            # WMO weather code -> human description
            wmo_descriptions = {
                0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
                45: 'Foggy', 48: 'Icy fog',
                51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
                61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
                71: 'Light snow', 73: 'Snow', 75: 'Heavy snow',
                80: 'Light showers', 81: 'Showers', 82: 'Heavy showers',
                95: 'Thunderstorm', 96: 'Thunderstorm w/ hail', 99: 'Thunderstorm w/ heavy hail',
            }
            wmo_code = current.get('weather_code', 0)
            condition = wmo_descriptions.get(wmo_code, f'Code {wmo_code}')

            # Celsius from Fahrenheit for display
            temp_f = current['temperature_2m']
            temp_c = round((temp_f - 32) * 5 / 9, 1)

            weather_info = {
                'temp_f': round(temp_f, 1),
                'temp_c': temp_c,
                'condition': condition,
                'weather_code': wmo_code,
                'humidity': current.get('relative_humidity_2m', 0),
                'wind_speed': round(current.get('wind_speed_10m', 0), 1),
                'wind_dir': wind_dir,
                'precip': current.get('precipitation', 0),
                'cloud_cover': current.get('cloud_cover', 0),
            }

            self.current_weather = weather_info
            self.determine_weather_condition(weather_info)

            print(f"[{ts}] Weather | {condition}, {weather_info['temp_f']}°F, "
                  f"{weather_info['wind_speed']} mph {wind_dir}, "
                  f"{weather_info['cloud_cover']}% cloud → visual: {self.weather_condition}")

            return weather_info

        except requests.exceptions.Timeout:
            print(f"[{ts}] Weather API timeout — keeping current condition: {self.weather_condition}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"[{ts}] Weather API connection error — keeping current condition: {self.weather_condition}")
            return None
        except Exception as e:
            print(f"[{ts}] Weather fetch error: {e} — keeping current condition: {self.weather_condition}")
            return None
    
    def determine_weather_condition(self, weather_info):
        """Determine visual weather condition from WMO weather code (Open-Meteo)."""
        code = int(weather_info['weather_code'])

        # WMO Weather Interpretation Codes
        # 0-2:  Clear / mainly clear
        # 3:    Overcast
        # 45,48: Fog
        # 51-67: Drizzle / rain
        # 71-77: Snow
        # 80-82: Rain showers
        # 85-86: Snow showers
        # 95:   Thunderstorm
        # 96,99: Thunderstorm with hail

        if code in (0, 1):
            self.weather_condition = "clear"
        elif code in (2, 3):
            self.weather_condition = "cloudy"
        elif code in (45, 48):
            self.weather_condition = "fog"
        elif code in (51, 53, 55, 61):
            self.weather_condition = "light_rain"
        elif code in (63, 65, 80, 81, 82):
            self.weather_condition = "rain"
        elif code in (95, 96, 99):
            self.weather_condition = "thunderstorm"
        else:
            self.weather_condition = "clear"
    
    def get_weather_sky_color(self):
        """Get sky color based on current weather and time of day."""
        hour = datetime.now().hour
        
        # Base colors for time of day
        if 10 <= hour < 16:  # Day
            if self.weather_condition in ["rain", "thunderstorm"]:
                return '#5a6a7a'  # Dark gray for stormy day
            elif self.weather_condition == "cloudy":
                return '#9ab8d3'  # Lighter gray-blue for cloudy
            elif self.weather_condition == "fog":
                return '#b8c8d8'  # Light gray for fog
            else:
                return '#87ceeb'  # Clear blue
        elif 16 <= hour < 18:  # Sunset
            if self.weather_condition in ["rain", "thunderstorm"]:
                return '#6a5a4a'  # Dark orange-gray
            else:
                return '#ff9933'  # Orange sunset
        elif 6 <= hour < 10:  # Sunrise
            if self.weather_condition in ["rain", "thunderstorm"]:
                return '#7a6a5a'  # Dark pink-gray
            else:
                return '#ff9966'  # Pink sunrise
        else:  # Night
            if self.weather_condition in ["rain", "thunderstorm"]:
                return '#0a0a0a'  # Very dark for stormy night
            else:
                return '#0a0a1e'  # Dark blue night
    
    def should_show_stars(self):
        """Determine if stars should be visible."""
        hour = datetime.now().hour
        is_night = hour >= 18 or hour < 6
        
        # Hide stars if cloudy/rainy/foggy
        if self.weather_condition in ["cloudy", "rain", "light_rain", "thunderstorm", "fog"]:
            return False
        
        return is_night
    
    def create_rain_drop(self):
        """Create a single rain drop."""
        x = random.randint(0, 800)
        y = random.randint(-20, 0)
        length = random.randint(8, 15)
        speed = random.uniform(12, 18)
        
        # Lighter rain for light_rain
        if self.weather_condition == "light_rain":
            speed *= 0.6
        
        drop_id = self.canvas.create_line(
            x, y,
            x - 2, y + length,
            fill='#a8b8c8', width=1, tags='rain'
        )
        
        self.rain_drops.append({
            'id': drop_id,
            'x': x,
            'y': y,
            'speed': speed
        })
    
    def update_rain(self):
        """Update rain drop positions."""
        if self.weather_condition not in ["rain", "light_rain", "thunderstorm"]:
            # Clear rain if weather changed
            self.canvas.delete('rain')
            self.rain_drops = []
            return
        
        # Spawn new rain drops
        spawn_rate = 3 if self.weather_condition == "light_rain" else 8
        for _ in range(spawn_rate):
            if len(self.rain_drops) < 150:
                self.create_rain_drop()
        
        # Update existing drops
        drops_to_remove = []
        for drop in self.rain_drops:
            drop['y'] += drop['speed']
            
            # Remove if off screen
            if drop['y'] > 600:
                self.canvas.delete(drop['id'])
                drops_to_remove.append(drop)
            else:
                # Move drop
                self.canvas.coords(
                    drop['id'],
                    drop['x'], drop['y'],
                    drop['x'] - 2, drop['y'] + random.randint(8, 15)
                )
        
        # Clean up off-screen drops
        for drop in drops_to_remove:
            self.rain_drops.remove(drop)
    
    def trigger_lightning(self):
        """Trigger a lightning flash."""
        if self.weather_condition == "thunderstorm":
            if random.random() < 0.02:  # 2% chance per frame
                self.lightning_flash = True
                self.lightning_timer = 0
    
    def update_lightning(self):
        """Update lightning flash effect."""
        if not self.lightning_flash:
            return
        
        self.lightning_timer += 1
        
        if self.lightning_timer == 1:
            # Create white flash overlay
            flash_id = self.canvas.create_rectangle(
                0, 0, 800, 600,
                fill='#ffffff',
                stipple='gray50',
                tags='lightning_flash'
            )
        elif self.lightning_timer > 2:
            # Remove flash
            self.canvas.delete('lightning_flash')
            self.lightning_flash = False
            self.lightning_timer = 0
    
    def create_fog_layer(self):
        """Create fog overlay effect."""
        if self.weather_condition != "fog":
            self.canvas.delete('fog')
            return
        
        # Draw semi-transparent fog layers
        self.canvas.delete('fog')
        
        for i in range(5):
            y_offset = i * 120
            fog_id = self.canvas.create_rectangle(
                0, y_offset,
                800, y_offset + 120,
                fill='#d8d8d8',
                stipple='gray25',
                tags='fog'
            )
    
    def update(self):
        """Update all weather effects (call every frame)."""
        # Update rain
        if self.weather_condition in ["rain", "light_rain", "thunderstorm"]:
            self.update_rain()
        
        # Update lightning
        if self.weather_condition == "thunderstorm":
            self.trigger_lightning()
            self.update_lightning()
        
        # Update fog
        if self.weather_condition == "fog":
            self.create_fog_layer()
    
    def get_cloud_count(self):
        """Get number of clouds to display based on weather."""
        if self.weather_condition == "clear":
            return 2
        elif self.weather_condition in ["cloudy", "light_rain"]:
            return 6
        elif self.weather_condition in ["rain", "thunderstorm"]:
            return 8
        elif self.weather_condition == "fog":
            return 0  # Fog replaces clouds
        else:
            return 3
    
    def get_cloud_color(self):
        """Get cloud color based on weather."""
        hour = datetime.now().hour
        
        if self.weather_condition in ["rain", "thunderstorm"]:
            return '#606060'  # Dark gray
        elif self.weather_condition == "cloudy":
            return '#c8c8c8'  # Light gray
        else:
            # Use time-based color
            if 10 <= hour < 16:
                return '#ffffff'
            elif 16 <= hour < 18:
                return '#ffd9b3'
            elif 6 <= hour < 10:
                return '#ffe5cc'
            else:
                return '#d0d0d0'