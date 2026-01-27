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
        """Fetch current weather from Cape Canaveral, FL using wttr.in API."""
        try:
            # Using wttr.in - free, no API key needed
            # Cape Canaveral coordinates: 28.3922° N, 80.6077° W
            url = "https://wttr.in/Cape_Canaveral,Florida?format=j1"
            
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; LaunchPad/1.0)'
            })
            response.raise_for_status()
            data = response.json()
            
            # Extract current conditions
            current = data['current_condition'][0]
            
            weather_info = {
                'temp_f': current['temp_F'],
                'temp_c': current['temp_C'],
                'condition': current['weatherDesc'][0]['value'],
                'weather_code': current['weatherCode'],
                'humidity': current['humidity'],
                'wind_speed': current['windspeedMiles'],
                'wind_dir': current['winddir16Point'],
                'precip': current['precipMM'],
                'cloud_cover': current['cloudcover']
            }
            
            self.current_weather = weather_info
            self.determine_weather_condition(weather_info)
            
            print(f"\n=== WEATHER UPDATE ===")
            print(f"Location: Cape Canaveral, FL")
            print(f"Condition: {weather_info['condition']}")
            print(f"Temperature: {weather_info['temp_f']}°F ({weather_info['temp_c']}°C)")
            print(f"Humidity: {weather_info['humidity']}%")
            print(f"Wind: {weather_info['wind_speed']} mph {weather_info['wind_dir']}")
            print(f"Cloud Cover: {weather_info['cloud_cover']}%")
            print(f"======================\n")
            
            return weather_info
            
        except requests.exceptions.Timeout:
            print(f"Weather API timeout - using default clear weather")
            self.weather_condition = "clear"
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Weather API connection error - using default clear weather")
            self.weather_condition = "clear"
            return None
        except Exception as e:
            print(f"Error fetching weather: {e}")
            print("Using default clear weather")
            self.weather_condition = "clear"
            return None
    
    def determine_weather_condition(self, weather_info):
        """Determine visual weather condition from weather data."""
        code = int(weather_info['weather_code'])
        
        # Weather codes from wttr.in
        # 113: Clear/Sunny
        # 116: Partly cloudy
        # 119: Cloudy
        # 122: Overcast
        # 143: Mist
        # 176-353: Various rain conditions
        # 200-232: Thundery conditions
        # 248-260: Fog
        # 263-284: Light to moderate rain
        # 293-299: Moderate to heavy rain
        # 302-365: Heavy rain and freezing rain
        
        if code == 113:
            self.weather_condition = "clear"
        elif code in [116, 119, 122]:
            self.weather_condition = "cloudy"
        elif code in [143, 248, 260]:
            self.weather_condition = "fog"
        elif code in [176, 263, 266, 281, 284, 293, 296]:
            self.weather_condition = "light_rain"
        elif code in [299, 302, 305, 308, 311, 314, 317, 320, 323, 326]:
            self.weather_condition = "rain"
        elif code in [200, 386, 389, 392, 395]:
            self.weather_condition = "thunderstorm"
        else:
            self.weather_condition = "clear"
        
        print(f"Visual weather condition set to: {self.weather_condition}")
    
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