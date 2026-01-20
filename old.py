#!/usr/bin/env python3
"""
Pixel Launch Pad Countdown Display with Kennedy Space Center Background
"""

import requests
from datetime import datetime, timezone
import tkinter as tk
import random

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

class LaunchPadDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title("Launch Countdown")
        self.root.geometry("800x600")
        self.root.configure(bg='#0a0a0a')
        
        # Create main canvas
        self.canvas = tk.Canvas(root, width=800, height=600, bg='#87ceeb', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Launch data
        self.launch_data = None
        self.launch_time = None
        self.vehicle_name = None
        
        # Animation variables
        self.cloud_offset = 0
        self.smoke_frame = 0
        
        # Draw background scene
        self.draw_background()
        
        # Fetch and display launch data
        self.fetch_and_display()
        
        # Start countdown update loop
        self.update_countdown()
        
        # Start animation loops
        self.animate_clouds()
        self.animate_smoke()
    
    def get_sky_colors(self):
        """Get sky and ocean colors based on current time of day."""
        now = datetime.now()
        hour = now.hour
        
        # 10am-4pm: Day (blue sky)
        if 10 <= hour < 16:
            return {
                'sky': '#87ceeb',
                'ocean': '#1a8b9e',
                'horizon': '#156673',
                'cloud': '#ffffff'
            }
        # 4pm-6pm: Sunset (orange)
        elif 16 <= hour < 18:
            return {
                'sky': '#ff9933',
                'ocean': '#1a5b6e',
                'horizon': '#0d3d4a',
                'cloud': '#ffd9b3'
            }
        # 6am-10am: Sunrise (orange/pink)
        elif 6 <= hour < 10:
            return {
                'sky': '#ff9966',
                'ocean': '#2a5b6e',
                'horizon': '#1d4a5a',
                'cloud': '#ffe5cc'
            }
        # 6pm-6am: Night (dark)
        else:
            return {
                'sky': '#0a0a1e',
                'ocean': '#0d1a2e',
                'horizon': '#050d1a',
                'cloud': '#d0d0d0'
            }
    
    def draw_background(self):
        """Draw Kennedy Space Center inspired pixel background."""
        colors = self.get_sky_colors()
        
        # Sky - changes based on time of day
        self.canvas.create_rectangle(0, 0, 800, 350, fill=colors['sky'], outline='')
        
        # Add stars if nighttime
        hour = datetime.now().hour
        if hour >= 18 or hour < 6:
            self.draw_stars()
        
        # Ocean - teal/turquoise
        self.canvas.create_rectangle(0, 350, 800, 600, fill=colors['ocean'], outline='')
        
        # Horizon line - darker teal
        self.canvas.create_rectangle(0, 350, 800, 365, fill=colors['horizon'], outline='')
        
        # Grassy ground area
        self.canvas.create_rectangle(0, 365, 800, 390, fill='#5a8c3a', outline='')
        
        # Add pixel grass details
        self.draw_pixel_grass()
        
        # VAB (Vehicle Assembly Building) - Large iconic building
        vab_x = 60
        vab_y = 220
        # Main building - white/light gray
        self.canvas.create_rectangle(vab_x, vab_y, vab_x+100, vab_y+130, fill='#e8e8e8', outline='')
        # Dark side panel
        self.canvas.create_rectangle(vab_x+100, vab_y+20, vab_x+120, vab_y+130, fill='#1e5a6e', outline='')
        # NASA logo area - blue circle
        self.canvas.create_oval(vab_x+35, vab_y+40, vab_x+65, vab_y+70, fill='#1e5a6e', outline='')
        # Vertical stripes
        for i in range(3):
            self.canvas.create_rectangle(vab_x+20+i*25, vab_y+80, vab_x+28+i*25, vab_y+130, fill='#1e5a6e', outline='')
        # Windows at bottom
        for i in range(8):
            self.canvas.create_rectangle(vab_x+10+i*10, vab_y+110, vab_x+16+i*10, vab_y+125, fill='#4a6b7a', outline='')
        
        # Second smaller building
        bldg2_x = 200
        bldg2_y = 270
        self.canvas.create_rectangle(bldg2_x, bldg2_y, bldg2_x+60, bldg2_y+80, fill='#d4d4d4', outline='')
        self.canvas.create_rectangle(bldg2_x+60, bldg2_y+15, bldg2_x+75, bldg2_y+80, fill='#1e5a6e', outline='')
        # Windows
        for i in range(2):
            for j in range(3):
                self.canvas.create_rectangle(bldg2_x+10+j*15, bldg2_y+15+i*25, bldg2_x+18+j*15, bldg2_y+30+i*25, fill='#4a6b7a', outline='')
        
        # Water tower
        tower_x = 290
        tower_y = 290
        # Tank
        self.canvas.create_rectangle(tower_x, tower_y, tower_x+25, tower_y+20, fill='#c0c0c0', outline='')
        # Legs
        self.canvas.create_rectangle(tower_x+3, tower_y+20, tower_x+6, tower_y+60, fill='#808080', outline='')
        self.canvas.create_rectangle(tower_x+19, tower_y+20, tower_x+22, tower_y+60, fill='#808080', outline='')
        
        # Launch tower (red/orange structure)
        tower_x = 580
        tower_y = 180
        # Main tower
        self.canvas.create_rectangle(tower_x, tower_y, tower_x+12, tower_y+170, fill='#d4524f', outline='')
        self.canvas.create_rectangle(tower_x+45, tower_y, tower_x+57, tower_y+170, fill='#d4524f', outline='')
        # Cross beams - yellow
        for i in range(6):
            y = tower_y + 25 + i*25
            self.canvas.create_rectangle(tower_x, y, tower_x+57, y+5, fill='#f5a742', outline='')
        
        # Launch pad platform
        pad_x = 530
        pad_y = 340
        # Platform - dark gray
        self.canvas.create_rectangle(pad_x, pad_y, pad_x+140, pad_y+10, fill='#5a5a5a', outline='')
        # Support pillars
        self.canvas.create_rectangle(pad_x+10, pad_y+10, pad_x+20, pad_y+40, fill='#4a4a4a', outline='')
        self.canvas.create_rectangle(pad_x+50, pad_y+10, pad_x+60, pad_y+40, fill='#4a4a4a', outline='')
        self.canvas.create_rectangle(pad_x+90, pad_y+10, pad_x+100, pad_y+40, fill='#4a4a4a', outline='')
        self.canvas.create_rectangle(pad_x+120, pad_y+10, pad_x+130, pad_y+40, fill='#4a4a4a', outline='')
        
        # Flat pixel clouds with time-appropriate color
        self.cloud1 = self.draw_flat_cloud(150, 60, colors['cloud'])
        self.cloud2 = self.draw_flat_cloud(420, 90, colors['cloud'])
        self.cloud3 = self.draw_flat_cloud(650, 50, colors['cloud'])
        self.clouds = [self.cloud1, self.cloud2, self.cloud3]
    
    def draw_stars(self):
        """Draw stars for nighttime."""
        random.seed(42)
        for _ in range(60):
            x = random.randint(0, 800)
            y = random.randint(0, 340)
            size = random.choice([1, 2])
            brightness = random.choice(['#ffffff', '#ffff99', '#aaaaaa'])
            self.canvas.create_oval(x, y, x+size, y+size, fill=brightness, outline='', tags='stars')
    
    def draw_pixel_grass(self):
        """Draw pixel grass details on the ground."""
        random.seed(123)
        grass_colors = ['#4a7c2a', '#6a9c4a', '#5a8c3a']
        
        for i in range(100):
            x = random.randint(0, 800)
            y = random.randint(368, 387)
            color = random.choice(grass_colors)
            if random.choice([True, False]):
                self.canvas.create_rectangle(x, y, x+2, y+4, fill=color, outline='')
            else:
                self.canvas.create_line(x, y, x, y+3, fill=color, width=1)
    
    def draw_flat_cloud(self, x, y, cloud_color='#ffffff'):
        """Draw a flat pixel cloud and return cloud IDs."""
        cloud_ids = []
        cloud_ids.append(self.canvas.create_oval(x, y+5, x+25, y+20, fill=cloud_color, outline='', tags='cloud'))
        cloud_ids.append(self.canvas.create_oval(x+15, y, x+40, y+18, fill=cloud_color, outline='', tags='cloud'))
        cloud_ids.append(self.canvas.create_oval(x+30, y+5, x+55, y+20, fill=cloud_color, outline='', tags='cloud'))
        return cloud_ids
    
    def animate_clouds(self):
        """Animate clouds moving horizontally."""
        self.canvas.move('cloud', 0.3, 0)
        
        for cloud_group in self.clouds:
            if cloud_group:
                coords = self.canvas.coords(cloud_group[0])
                if coords and coords[0] > 850:
                    for cloud_id in cloud_group:
                        self.canvas.move(cloud_id, -900, 0)
        
        self.root.after(50, self.animate_clouds)
    
    def animate_smoke(self):
        """Animate smoke rising from rocket base."""
        self.canvas.delete("smoke")
        
        if self.launch_data:
            pad_x = 605
            pad_y = 340
            
            for i in range(8):
                smoke_y = pad_y + 5 - (self.smoke_frame + i * 3) % 40
                smoke_x = pad_x + random.randint(-15, 15)
                opacity = 255 - ((self.smoke_frame + i * 3) % 40) * 6
                
                if opacity > 50:
                    gray_val = hex(max(100, min(200, 150 + random.randint(-20, 20))))[2:]
                    if len(gray_val) == 1:
                        gray_val = '0' + gray_val
                    smoke_color = f'#{gray_val}{gray_val}{gray_val}'
                    size = random.randint(3, 7)
                    self.canvas.create_rectangle(
                        smoke_x, smoke_y, smoke_x + size, smoke_y + size,
                        fill=smoke_color, outline='', tags="smoke"
                    )
            
            self.smoke_frame += 1
        
        self.root.after(100, self.animate_smoke)
    
    def draw_info_sign(self):
        """Draw launch info on a sign next to the pad."""
        if not self.launch_data:
            return
        
        sign_x = 400
        sign_y = 250
        
        # Sign post
        self.canvas.create_rectangle(sign_x-3, sign_y+60, sign_x+3, sign_y+100, fill='#4a4a4a', outline='')
        
        # Sign board
        self.canvas.create_rectangle(sign_x-80, sign_y, sign_x+80, sign_y+60, fill='#2a2a2a', outline='#ffd93d', width=3)
        
        # Mission name
        mission_name = self.launch_data.get('name', 'Unknown Mission')
        if len(mission_name) > 25:
            mission_name = mission_name[:22] + "..."
        self.canvas.create_text(sign_x, sign_y+12, text=mission_name,
                               font=('Courier', 9, 'bold'), fill='#ffffff', anchor='center')
        
        # Provider
        provider = self.launch_data.get('provider', {}).get('name', 'Unknown')
        if len(provider) > 20:
            provider = provider[:17] + "..."
        self.canvas.create_text(sign_x, sign_y+28, text=provider,
                               font=('Courier', 8), fill='#74b9ff', anchor='center')
        
        # Vehicle
        vehicle = self.vehicle_name
        if len(vehicle) > 20:
            vehicle = vehicle[:17] + "..."
        self.canvas.create_text(sign_x, sign_y+40, text=vehicle,
                               font=('Courier', 8), fill='#a29bfe', anchor='center')
        
        # Pad name
        pad = self.launch_data.get('pad', {})
        pad_name = pad.get('name', 'Unknown Pad')
        if len(pad_name) > 20:
            pad_name = pad_name[:17] + "..."
        self.canvas.create_text(sign_x, sign_y+52, text=pad_name,
                               font=('Courier', 7), fill='#ffd93d', anchor='center')
    
    def draw_rocket_on_pad(self, vehicle_name):
        """Draw different rockets based on vehicle name."""
        pad_x = 605
        pad_y = 340
        
        vehicle_lower = vehicle_name.lower() if vehicle_name else ''
        
        if 'falcon 9' in vehicle_lower or 'falcon' in vehicle_lower:
            self.draw_falcon_9(pad_x, pad_y)
        elif 'starship' in vehicle_lower:
            self.draw_starship(pad_x, pad_y)
        elif 'atlas' in vehicle_lower:
            self.draw_atlas(pad_x, pad_y)
        elif 'delta' in vehicle_lower:
            self.draw_delta(pad_x, pad_y)
        elif 'sls' in vehicle_lower or 'space launch system' in vehicle_lower:
            self.draw_sls(pad_x, pad_y)
        elif 'electron' in vehicle_lower:
            self.draw_electron(pad_x, pad_y)
        else:
            self.draw_generic_rocket(pad_x, pad_y)
    
    def draw_falcon_9(self, x, y):
        """Draw Falcon 9 style rocket."""
        # Main body - white/light gray (first stage)
        self.canvas.create_rectangle(x-10, y-140, x+10, y-15, fill='#f5f5f5', outline='')
        self.canvas.create_rectangle(x+6, y-140, x+10, y-15, fill='#d0d0d0', outline='')
        
        # Black interstage band
        self.canvas.create_rectangle(x-10, y-140, x+10, y-125, fill='#1a1a1a', outline='')
        
        # Second stage
        self.canvas.create_rectangle(x-9, y-165, x+9, y-140, fill='#f8f8f8', outline='')
        self.canvas.create_rectangle(x+5, y-165, x+9, y-140, fill='#d8d8d8', outline='')
        
        # Payload fairing
        self.canvas.create_polygon(x-9, y-165, x, y-185, x+9, y-165, fill='#f8f8f8', outline='')
        self.canvas.create_polygon(x+5, y-165, x, y-185, x+9, y-165, fill='#d8d8d8', outline='')
        
        # Grid fins
        self.canvas.create_rectangle(x-14, y-155, x-10, y-145, fill='#3a3a3a', outline='')
        self.canvas.create_rectangle(x+10, y-155, x+14, y-145, fill='#3a3a3a', outline='')
        
        # Landing legs
        self.canvas.create_polygon(x-10, y-25, x-18, y-8, x-10, y-15, fill='#2a2a2a', outline='')
        self.canvas.create_polygon(x-10, y-35, x-16, y-25, x-10, y-25, fill='#1a1a1a', outline='')
        self.canvas.create_polygon(x+10, y-25, x+18, y-8, x+10, y-15, fill='#2a2a2a', outline='')
        self.canvas.create_polygon(x+10, y-35, x+16, y-25, x+10, y-25, fill='#1a1a1a', outline='')
        
        # Merlin engines
        engine_y = y-8
        self.canvas.create_oval(x-6, engine_y, x-3, engine_y+3, fill='#4a4a4a', outline='')
        self.canvas.create_oval(x+3, engine_y, x+6, engine_y+3, fill='#4a4a4a', outline='')
        self.canvas.create_oval(x-2, engine_y-2, x+2, engine_y+2, fill='#5a5a5a', outline='')
        self.canvas.create_oval(x-4, engine_y+2, x-1, engine_y+5, fill='#4a4a4a', outline='')
        self.canvas.create_oval(x+1, engine_y+2, x+4, engine_y+5, fill='#4a4a4a', outline='')
        
        # Octaweb
        self.canvas.create_rectangle(x-11, y-15, x+11, y-5, fill='#2a2a2a', outline='')
        self.canvas.create_rectangle(x+7, y-15, x+11, y-5, fill='#1a1a1a', outline='')
        
        # SpaceX logo area
        self.canvas.create_rectangle(x-9, y-150, x+9, y-148, fill='#1a1a1a', outline='')
    
    def draw_starship(self, x, y):
        """Draw Starship style rocket."""
        self.canvas.create_rectangle(x-12, y-160, x+12, y-20, fill='#c8c8c8', outline='')
        self.canvas.create_rectangle(x+8, y-160, x+12, y-20, fill='#a0a0a0', outline='')
        
        for i in range(8):
            for j in range(2):
                tile_y = y-20-i*5
                tile_x = x-10+j*10
                self.canvas.create_rectangle(tile_x, tile_y, tile_x+8, tile_y+4, fill='#1a1a1a', outline='')
        
        self.canvas.create_polygon(x-12, y-120, x-20, y-115, x-12, y-110, fill='#a0a0a0', outline='')
        self.canvas.create_polygon(x+12, y-120, x+20, y-115, x+12, y-110, fill='#a0a0a0', outline='')
        self.canvas.create_polygon(x-12, y-35, x-22, y-20, x-12, y-20, fill='#a0a0a0', outline='')
        self.canvas.create_polygon(x+12, y-35, x+22, y-20, x+12, y-20, fill='#a0a0a0', outline='')
        
        engine_positions = [(x-6, y-12), (x+6, y-12), (x-3, y-8), (x+3, y-8), (x, y-5)]
        for ex, ey in engine_positions:
            self.canvas.create_oval(ex-2, ey-2, ex+2, ey+2, fill='#2a2a2a', outline='')
        
        self.canvas.create_polygon(x-12, y-160, x, y-185, x+12, y-160, fill='#c8c8c8', outline='')
        self.canvas.create_polygon(x+8, y-160, x, y-185, x+12, y-160, fill='#a0a0a0', outline='')
        self.canvas.create_oval(x-4, y-145, x+4, y-140, fill='#1a3a4a', outline='')
    
    def draw_atlas(self, x, y):
        """Draw Atlas V style rocket."""
        self.canvas.create_rectangle(x-8, y-125, x+8, y, fill='#ff8c00', outline='')
        self.canvas.create_rectangle(x+5, y-125, x+8, y, fill='#d67300', outline='')
        self.canvas.create_rectangle(x-7, y-125, x+7, y-75, fill='#f8f8f8', outline='')
        self.canvas.create_rectangle(x+4, y-125, x+7, y-75, fill='#d8d8d8', outline='')
        self.canvas.create_polygon(x-7, y-125, x, y-145, x+7, y-125, fill='#f8f8f8', outline='')
        self.canvas.create_polygon(x+4, y-125, x, y-145, x+7, y-125, fill='#d8d8d8', outline='')
        self.canvas.create_rectangle(x-17, y-75, x-12, y, fill='#ffffff', outline='')
        self.canvas.create_rectangle(x-15, y-75, x-12, y, fill='#e0e0e0', outline='')
        self.canvas.create_rectangle(x+12, y-75, x+17, y, fill='#ffffff', outline='')
        self.canvas.create_rectangle(x+14, y-75, x+17, y, fill='#e0e0e0', outline='')
        self.canvas.create_oval(x-4, y-8, x+4, y-2, fill='#4a4a4a', outline='')
        self.canvas.create_oval(x-15, y-6, x-13, y-3, fill='#3a3a3a', outline='')
        self.canvas.create_oval(x+13, y-6, x+15, y-3, fill='#3a3a3a', outline='')
    
    def draw_delta(self, x, y):
        """Draw Delta IV Heavy style rocket."""
        self.canvas.create_rectangle(x-7, y-130, x+7, y, fill='#ff8c00', outline='')
        self.canvas.create_rectangle(x+4, y-130, x+7, y, fill='#d67300', outline='')
        self.canvas.create_rectangle(x-20, y-115, x-12, y, fill='#ff8c00', outline='')
        self.canvas.create_rectangle(x-15, y-115, x-12, y, fill='#d67300', outline='')
        self.canvas.create_rectangle(x+12, y-115, x+20, y, fill='#ff8c00', outline='')
        self.canvas.create_rectangle(x+17, y-115, x+20, y, fill='#d67300', outline='')
        self.canvas.create_polygon(x-7, y-130, x, y-150, x+7, y-130, fill='#f5f5f5', outline='')
        self.canvas.create_polygon(x+4, y-130, x, y-150, x+7, y-130, fill='#d8d8d8', outline='')
        self.canvas.create_oval(x-4, y-10, x+4, y-4, fill='#6a4a3a', outline='')
        self.canvas.create_oval(x-17, y-8, x-13, y-4, fill='#6a4a3a', outline='')
        self.canvas.create_oval(x+13, y-8, x+17, y-4, fill='#6a4a3a', outline='')
    
    def draw_sls(self, x, y):
        """Draw SLS style rocket."""
        self.canvas.create_rectangle(x-9, y-170, x+9, y, fill='#ff8c00', outline='')
        self.canvas.create_rectangle(x+6, y-170, x+9, y, fill='#d67300', outline='')
        self.canvas.create_rectangle(x-23, y-155, x-14, y, fill='#f8f8f8', outline='')
        self.canvas.create_rectangle(x-17, y-155, x-14, y, fill='#d8d8d8', outline='')
        self.canvas.create_rectangle(x+14, y-155, x+23, y, fill='#f8f8f8', outline='')
        self.canvas.create_rectangle(x+20, y-155, x+23, y, fill='#d8d8d8', outline='')
        self.canvas.create_rectangle(x-8, y-170, x+8, y-140, fill='#ff9933', outline='')
        self.canvas.create_rectangle(x+5, y-170, x+8, y-140, fill='#d67300', outline='')
        self.canvas.create_oval(x-8, y-185, x+8, y-170, fill='#4a4a4a', outline='')
        self.canvas.create_oval(x+4, y-185, x+8, y-177, fill='#3a3a3a', outline='')
        self.canvas.create_rectangle(x-7, y-175, x+7, y-170, fill='#e8e8e8', outline='')
        self.canvas.create_rectangle(x-2, y-195, x+2, y-185, fill='#d44444', outline='')
        for i in range(4):
            ex = x - 6 + i * 4
            self.canvas.create_oval(ex-2, y-10, ex+2, y-5, fill='#6a4a3a', outline='')
        self.canvas.create_oval(x-20, y-8, x-16, y-3, fill='#4a4a4a', outline='')
        self.canvas.create_oval(x+16, y-8, x+20, y-3, fill='#4a4a4a', outline='')
    
    def draw_electron(self, x, y):
        """Draw Electron style rocket (small)."""
        self.canvas.create_rectangle(x-5, y-95, x+5, y, fill='#1a1a1a', outline='')
        self.canvas.create_rectangle(x+3, y-95, x+5, y, fill='#0a0a0a', outline='')
        self.canvas.create_rectangle(x-5, y-60, x+5, y-55, fill='#ff6b35', outline='')
        self.canvas.create_polygon(x-5, y-95, x, y-108, x+5, y-95, fill='#1a1a1a', outline='')
        self.canvas.create_polygon(x+3, y-95, x, y-108, x+5, y-95, fill='#0a0a0a', outline='')
        self.canvas.create_polygon(x-5, y-12, x-10, y-2, x-5, y, fill='#2a2a2a', outline='')
        self.canvas.create_polygon(x+5, y-12, x+10, y-2, x+5, y, fill='#2a2a2a', outline='')
        for i in range(3):
            ex = x - 3 + i * 3
            self.canvas.create_oval(ex-1, y-5, ex+1, y-2, fill='#4a3a2a', outline='')
    
    def draw_generic_rocket(self, x, y):
        """Draw a generic rocket."""
        self.canvas.create_rectangle(x-8, y-115, x+8, y, fill='#f5f5f5', outline='')
        self.canvas.create_rectangle(x+5, y-115, x+8, y, fill='#d0d0d0', outline='')
        self.canvas.create_rectangle(x-8, y-70, x+8, y-60, fill='#d44444', outline='')
        self.canvas.create_rectangle(x-8, y-55, x+8, y-50, fill='#4a69bd', outline='')
        self.canvas.create_polygon(x-8, y-115, x, y-135, x+8, y-115, fill='#d44444', outline='')
        self.canvas.create_polygon(x+5, y-115, x, y-135, x+8, y-115, fill='#b03333', outline='')
        self.canvas.create_polygon(x-8, y-25, x-16, y-5, x-8, y, fill='#c0c0c0', outline='')
        self.canvas.create_polygon(x+8, y-25, x+16, y-5, x+8, y, fill='#a0a0a0', outline='')
        self.canvas.create_oval(x-5, y-10, x+5, y-3, fill='#4a4a4a', outline='')
    
    def fetch_and_display(self):
        """Fetch launch data and display it."""
        launches = fetch_launches(1)
        
        if not launches:
            self.canvas.create_text(400, 50, text="NO DATA",
                                   font=('Courier', 16, 'bold'), fill='#ff4444')
            return
        
        self.launch_data = launches[0]
        self.launch_time = self.launch_data.get('t0') or self.launch_data.get('win_open')
        self.vehicle_name = self.launch_data.get('vehicle', {}).get('name', 'Unknown')
        
        self.draw_rocket_on_pad(self.vehicle_name)
        self.draw_info_sign()
        self.display_launch_info()
    
    def display_launch_info(self):
        """Display the launch information."""
        self.canvas.create_text(400, 580, text="Data: RocketLaunch.Live",
                               font=('Courier', 7), fill='#666666')
    
    def update_countdown(self):
        """Update the countdown display every second."""
        if not self.launch_time:
            self.root.after(1000, self.update_countdown)
            return
        
        self.canvas.delete("countdown")
        
        countdown = get_countdown(self.launch_time)
        
        y_top = 20
        
        if countdown == "LAUNCHED":
            self.canvas.create_rectangle(250, 10, 550, 80, fill='#1a1a1a', 
                                        outline='#ff4444', width=3, tags="countdown")
            self.canvas.create_text(400, 45, text="LAUNCHED",
                                   font=('Courier', 28, 'bold'), fill='#ff4444', tags="countdown")
        elif countdown:
            self.canvas.create_text(400, y_top, text="T-MINUS",
                                   font=('Courier', 10, 'bold'), fill='#00ff88', tags="countdown")
            
            box_width = 60
            box_height = 50
            spacing = 10
            start_x = 400 - (4 * box_width + 3 * spacing) / 2
            y_pos = 30
            
            labels = ['D', 'H', 'M', 'S']
            values = [countdown['days'], countdown['hours'], countdown['minutes'], countdown['seconds']]
            colors = ['#ff6b6b', '#4a90e2', '#00ff88', '#ffd93d']
            
            for i, (label, value, color) in enumerate(zip(labels, values, colors)):
                x = start_x + i * (box_width + spacing)
                
                self.canvas.create_rectangle(x, y_pos, x+box_width, y_pos+box_height,
                                            fill='#1a1a1a', outline=color, width=2, tags="countdown")
                
                self.canvas.create_text(x+box_width/2, y_pos+22, text=f"{value:02d}",
                                       font=('Courier', 20, 'bold'), fill=color, tags="countdown")
                
                self.canvas.create_text(x+box_width/2, y_pos+40, text=label,
                                       font=('Courier', 7), fill='#666666', tags="countdown")
        else:
            date_str = self.launch_data.get('date_str', 'TBD')
            self.canvas.create_rectangle(250, 20, 550, 70, fill='#1a1a1a',
                                        outline='#ffd93d', width=2, tags="countdown")
            self.canvas.create_text(400, 45, text=date_str,
                                   font=('Courier', 12, 'bold'), fill='#ffd93d', tags="countdown")
        
        self.root.after(1000, self.update_countdown)

def main():
    """Main function to run the rocket launch display."""
    root = tk.Tk()
    app = LaunchPadDisplay(root)
    root.mainloop()

if __name__ == "__main__":
    main()