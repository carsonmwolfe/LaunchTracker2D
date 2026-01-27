#!/usr/bin/env python3
"""
Pixel Launch Pad Countdown Display with Kennedy Space Center Background
Main entry point for the application.
"""

import tkinter as tk
import random
from api_client import fetch_launches, get_countdown
from landscape import draw_background, draw_bird, draw_car
from rockets import draw_rocket_on_pad
from ui_elements import (
    draw_info_sign,
    draw_countdown_display,
    draw_smoke_effect,
    draw_attribution
)
from launch_animation import LaunchAnimation
from aircraft import T38Aircraft
from weather import WeatherSystem


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

        self.weather = WeatherSystem(self.canvas)
        self.weather.fetch_weather()  # Initial weather fetch

        # Animation variables
        self.smoke_frame = 0
        self.light_blink_state = False
        self.light_blink_counter = 0
        
        # Launch animation
        self.launch_animator = None
        self.rocket_ids = []
        
        # Gator animation
        self.gator_visible = False
        self.gator_timer = 0
        
        # T-38 Aircraft
        self.aircraft = T38Aircraft(self.canvas)
        
        # Birds
        self.birds = []
        self.spawn_birds()
        
        # Cars
        self.cars = []
        self.spawn_cars()
        
        # Draw background scene and get cloud references
        self.clouds = draw_background(self.canvas)
        
        # Create test launch button
        self.test_button = tk.Button(
            root,
            text="TEST LAUNCH",
            command=self.test_launch,
            bg='#ff6600',
            fg='#ffffff',
            font=('Courier', 10, 'bold'),
            padx=10,
            pady=5
        )
        self.test_button.place(x=10, y=10)
        
        # Fetch and display launch data
        self.fetch_and_display(is_initial=True)
        
        # Start countdown update loop
        self.update_countdown()
        
        # Start animation loops
        self.animate_clouds()
        self.animate_smoke()
        self.animate_birds()
        self.animate_cars()
        self.animate_gator()
        self.animate_aircraft()
        self.animate_tower_lights()
        self.animate_sky_colors()
        self.animate_weather()
        self.refresh_weather()  # Start weather refresh cycle

    
    def fetch_and_display(self, is_initial=True):
        """Fetch launch data and display it."""
        print("Fetching fresh launch data...")
        launches = fetch_launches(5)
        
        if not launches:
            print("ERROR: No upcoming launches found!")
            self.canvas.create_text(400, 50, text="NO UPCOMING LAUNCHES",
                                   font=('Courier', 16, 'bold'), fill='#ff4444')
            # Retry in 60 seconds
            self.root.after(60000, lambda: self.fetch_and_display(is_initial=False))
            return
        
        # Use the first upcoming launch
        self.launch_data = launches[0]
        self.launch_time = self.launch_data.get('t0') or self.launch_data.get('win_open')
        self.vehicle_name = self.launch_data.get('vehicle', {}).get('name', 'Unknown')
        
        print(f"\n=== SELECTED LAUNCH ===")
        print(f"Name: {self.launch_data.get('name')}")
        print(f"Vehicle: {self.vehicle_name}")
        print(f"Status: {self.launch_data.get('status', {}).get('name')}")
        print(f"Launch time: {self.launch_time}")
        print(f"======================\n")
        
        # Only draw rocket and create animator if it's the initial load
        # or if we're explicitly refreshing after a launch
        if is_initial:
            # Draw rocket on pad
            self.draw_rocket_with_tag()
            
            # Create launch animator
            self.launch_animator = LaunchAnimation(
                self.canvas,
                rocket_tag='rocket',
                initial_x=620,
                initial_y=340,
                vehicle_name=self.vehicle_name
            )
        
        # Clear and redraw info sign
        self.canvas.delete('info_sign')
        draw_info_sign(self.canvas, self.launch_data, self.vehicle_name)
        draw_attribution(self.canvas)
        
        # Draw spotlights AFTER rocket so they appear on top
        from landscape import draw_spotlights
        self.canvas.delete('spotlight')
        draw_spotlights(self.canvas, self.vehicle_name)
        
        # Schedule next data refresh in 5 minutes ONLY if we're not close to launch
        if not is_initial:  # Don't schedule on initial load
            return
            
        countdown = get_countdown(self.launch_time)
        if countdown and countdown != "LAUNCHED":
            seconds_to_launch = countdown.get('total_seconds', 0)
            # Only schedule refresh if launch is more than 10 minutes away
            if seconds_to_launch > 600:
                print(f"Scheduling data refresh in 5 minutes (launch is {seconds_to_launch/60:.1f} minutes away)")
                self.root.after(300000, self.safe_refresh)
            else:
                print(f"Not scheduling refresh - launch is only {seconds_to_launch/60:.1f} minutes away")
    
    def safe_refresh(self):
        """Safely refresh data only if conditions are right."""
        # Don't refresh if we're currently launching
        if self.launch_animator and self.launch_animator.is_launching:
            print("Skipping refresh - launch in progress")
            # Try again in 2 minutes
            self.root.after(120000, self.safe_refresh)
            return
        
        # Check if we're still far from launch
        if self.launch_time:
            countdown = get_countdown(self.launch_time)
            if countdown and countdown != "LAUNCHED":
                seconds_to_launch = countdown.get('total_seconds', 0)
                if seconds_to_launch < 300:  # Less than 5 minutes
                    print(f"Skipping refresh - too close to launch ({seconds_to_launch/60:.1f} minutes)")
                    # Try again in 1 minute
                    self.root.after(60000, self.safe_refresh)
                    return
        
        print("Performing safe data refresh...")
        # Fetch fresh data
        launches = fetch_launches(5)
        
        if not launches:
            print("No launches found during refresh")
            self.root.after(300000, self.safe_refresh)
            return
        
        current_launch_id = self.launch_data.get('id') if self.launch_data else None
        new_launch = launches[0]
        new_launch_id = new_launch.get('id')
        
        if new_launch_id != current_launch_id:
            # Launch has changed! Need full refresh
            print(f"Launch has changed! Old: {current_launch_id}, New: {new_launch_id}")
            self.load_next_launch()
        else:
            # Same launch - check if launch time changed
            old_time = self.launch_time
            new_time = new_launch.get('t0') or new_launch.get('win_open')
            
            if new_time != old_time:
                print(f"⚠️ LAUNCH TIME CHANGED!")
                print(f"   Old time: {old_time}")
                print(f"   New time: {new_time}")
                self.launch_time = new_time
            
            # Update launch data
            self.launch_data = new_launch
            
            # Refresh info sign with updated data
            self.canvas.delete('info_sign')
            draw_info_sign(self.canvas, self.launch_data, self.vehicle_name)
            
            print("Data refreshed successfully")
            
            # Schedule next refresh
            self.root.after(300000, self.safe_refresh)
    
    def load_next_launch(self):
        """Load the next launch after current one completes."""
        print("Loading next launch...")
        
        # Clean up current rocket
        self.canvas.delete('launch_flame')
        self.canvas.delete('rocket')
        
        # Fetch fresh data and display
        self.fetch_and_display(is_initial=True)
    
    def draw_rocket_with_tag(self):
        """Draw the rocket with a 'rocket' tag on all elements."""
        import rockets
        
        # Temporarily modify the rocket drawing to add tags
        original_create_rectangle = self.canvas.create_rectangle
        original_create_polygon = self.canvas.create_polygon
        original_create_oval = self.canvas.create_oval
        
        def tagged_rectangle(*args, **kwargs):
            if 'tags' in kwargs:
                kwargs['tags'] = (kwargs['tags'], 'rocket')
            else:
                kwargs['tags'] = 'rocket'
            return original_create_rectangle(*args, **kwargs)
        
        def tagged_polygon(*args, **kwargs):
            if 'tags' in kwargs:
                kwargs['tags'] = (kwargs['tags'], 'rocket')
            else:
                kwargs['tags'] = 'rocket'
            return original_create_polygon(*args, **kwargs)
        
        def tagged_oval(*args, **kwargs):
            if 'tags' in kwargs:
                kwargs['tags'] = (kwargs['tags'], 'rocket')
            else:
                kwargs['tags'] = 'rocket'
            return original_create_oval(*args, **kwargs)
        
        # Temporarily replace canvas methods
        self.canvas.create_rectangle = tagged_rectangle
        self.canvas.create_polygon = tagged_polygon
        self.canvas.create_oval = tagged_oval
        
        # Draw the rocket (now all elements will have 'rocket' tag)
        rockets.draw_rocket_on_pad(self.canvas, self.vehicle_name, pad_x=620, pad_y=340)
        
        # Restore original methods
        self.canvas.create_rectangle = original_create_rectangle
        self.canvas.create_polygon = original_create_polygon
        self.canvas.create_oval = original_create_oval
    
    def interpolate_color(self, color1, color2, ratio):
        """Interpolate between two hex colors."""
        # Convert hex to RGB
        r1 = int(color1[1:3], 16)
        g1 = int(color1[3:5], 16)
        b1 = int(color1[5:7], 16)
        
        r2 = int(color2[1:3], 16)
        g2 = int(color2[3:5], 16)
        b2 = int(color2[5:7], 16)
        
        # Interpolate
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        
        # Convert back to hex
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def get_current_sky_colors_with_transition(self):
        """Get current sky colors with smooth transitions between times."""
        from datetime import datetime
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Calculate time as a float (e.g., 6:30 = 6.5)
        time_float = hour + minute / 60.0
        
        # Define time periods and their colors
        periods = [
            # Night: 0-6am
            (0, 6, {
                'sky': '#0a0a1e',
                'ocean': '#0d1a2e',
                'horizon': '#050d1a',
                'cloud': '#d0d0d0'
            }),
            # Sunrise: 6-10am
            (6, 10, {
                'sky': '#ff9966',
                'ocean': '#2a5b6e',
                'horizon': '#1d4a5a',
                'cloud': '#ffe5cc'
            }),
            # Day: 10am-4pm
            (10, 16, {
                'sky': '#87ceeb',
                'ocean': '#1a8b9e',
                'horizon': '#156673',
                'cloud': '#ffffff'
            }),
            # Sunset: 4-6pm
            (16, 18, {
                'sky': '#ff9933',
                'ocean': '#1a5b6e',
                'horizon': '#0d3d4a',
                'cloud': '#ffd9b3'
            }),
            # Night: 6pm-midnight
            (18, 24, {
                'sky': '#0a0a1e',
                'ocean': '#0d1a2e',
                'horizon': '#050d1a',
                'cloud': '#d0d0d0'
            }),
        ]
        
        # Find which period we're in and calculate transition
        for i, (start, end, colors) in enumerate(periods):
            if start <= time_float < end:
                # Check if we should transition to next period
                transition_start = end - 0.5  # Start transitioning 30 min before period end
                
                if time_float >= transition_start and i < len(periods) - 1:
                    # We're in transition zone
                    next_colors = periods[i + 1][2] if i + 1 < len(periods) else periods[0][2]
                    ratio = (time_float - transition_start) / 0.5  # 0 to 1 over 30 minutes
                    
                    # Interpolate all colors
                    result = {}
                    for key in colors.keys():
                        result[key] = self.interpolate_color(colors[key], next_colors[key], ratio)
                    return result
                else:
                    # No transition, return current period colors
                    return colors
        
        # Fallback
        return periods[2][2]  # Return day colors
    
    def animate_sky_colors(self):
        """Animate sky color transitions based on time of day AND WEATHER."""
        # Get weather-adjusted sky color
        sky_color = self.weather.get_weather_sky_color()
        
        # Update sky rectangle
        sky_items = self.canvas.find_withtag('sky')
        for item in sky_items:
            self.canvas.itemconfig(item, fill=sky_color)
        
        # Update ocean (darker in storms)
        ocean_color = '#0d1a2e' if self.weather.weather_condition in ['rain', 'thunderstorm'] else '#1a8b9e'
        ocean_items = self.canvas.find_withtag('ocean')
        for item in ocean_items:
            self.canvas.itemconfig(item, fill=ocean_color)
        
        # Update horizon
        horizon_color = '#050d1a' if self.weather.weather_condition in ['rain', 'thunderstorm'] else '#156673'
        horizon_items = self.canvas.find_withtag('horizon')
        for item in horizon_items:
            self.canvas.itemconfig(item, fill=horizon_color)
        
        # Update cloud colors based on weather
        cloud_color = self.weather.get_cloud_color()
        cloud_items = self.canvas.find_withtag('cloud')
        for item in cloud_items:
            self.canvas.itemconfig(item, fill=cloud_color)
        
        # Update stars visibility based on weather
        if self.weather.should_show_stars():
            star_items = self.canvas.find_withtag('stars')
            for item in star_items:
                self.canvas.itemconfig(item, state='normal')
        else:
            star_items = self.canvas.find_withtag('stars')
            for item in star_items:
                self.canvas.itemconfig(item, state='hidden')
        
        # Update spotlights
        from landscape import draw_spotlights
        self.canvas.delete('spotlight')
        draw_spotlights(self.canvas, self.vehicle_name)
        
        # Check again in 30 seconds
        self.root.after(30000, self.animate_sky_colors)

# Add this new method to update weather effects every frame:
    def animate_weather(self):
        """Animate weather effects (rain, lightning, fog)."""
        self.weather.update()
        self.root.after(50, self.animate_weather)
    def refresh_weather(self):
        """Refresh weather data every 15 minutes."""
        print("Refreshing weather data...")
        self.weather.fetch_weather()
        
        # Update sky colors immediately
        self.animate_sky_colors()
        
        # Schedule next refresh in 60 minutes
        self.root.after(3600000, self.refresh_weather)
    
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
        is_launching = self.launch_animator and self.launch_animator.is_launching
        draw_smoke_effect(self.canvas, self.smoke_frame, self.launch_data, is_launching=is_launching)
        self.smoke_frame += 1
        self.root.after(100, self.animate_smoke)
    
    def animate_tower_lights(self):
        """Animate the blinking white lights on the launch tower."""
        self.light_blink_counter += 1
        
        # Blink every 30 frames (~1 second at 30ms intervals)
        if self.light_blink_counter >= 30:
            self.light_blink_counter = 0
            self.light_blink_state = not self.light_blink_state
            
            # Update all tower lights
            tower_lights = self.canvas.find_withtag('tower_light')
            for light_id in tower_lights:
                if self.light_blink_state:
                    # Turn on (bright white)
                    self.canvas.itemconfig(light_id, fill='#ffffff', outline='#ffff99')
                else:
                    # Turn off (dark gray)
                    self.canvas.itemconfig(light_id, fill='#3a3a3a', outline='#2a2a2a')
        
        self.root.after(30, self.animate_tower_lights)
    
    def animate_aircraft(self):
        """Animate T-38 aircraft flyby."""
        import time
        current_time = time.time() * 1000
        
        # Check if it's time to start a new flyby
        if self.aircraft.should_start_flyby(current_time):
            self.aircraft.start_flyby()
        
        # Update aircraft if active
        if self.aircraft.active:
            self.aircraft.update(33)
        
        self.root.after(33, self.animate_aircraft)
    
    def spawn_birds(self):
        """Create initial birds at random positions off-screen."""
        used_y_positions = []
        for i in range(3):
            x = -100 - (i * 150)
            
            while True:
                y = random.randint(80, 280)
                if not any(abs(y - used_y) < 40 for used_y in used_y_positions):
                    used_y_positions.append(y)
                    break
            
            speed_x = random.uniform(0.8, 1.8)
            speed_y = random.uniform(-0.15, 0.15)
            bird_ids = draw_bird(self.canvas, x, y, flap_up=True)
            self.birds.append({
                'ids': bird_ids,
                'speed_x': speed_x,
                'speed_y': speed_y,
                'y': y,
                'x': x,
                'flap_up': True,
                'flap_counter': 0,
                'min_y': 60,
                'max_y': 300
            })
    
    def animate_birds(self):
        """Animate birds flying across the screen with flapping wings."""
        for bird in self.birds:
            bird['flap_counter'] += 1
            if bird['flap_counter'] >= 8:
                bird['flap_counter'] = 0
                bird['flap_up'] = not bird['flap_up']
                
                if bird['ids']:
                    coords = self.canvas.coords(bird['ids'][0])
                    if coords:
                        current_x = coords[0]
                        current_y = bird['y']
                        
                        for bird_id in bird['ids']:
                            self.canvas.delete(bird_id)
                        
                        bird['ids'] = draw_bird(self.canvas, current_x, current_y, bird['flap_up'])
            
            for bird_id in bird['ids']:
                self.canvas.move(bird_id, bird['speed_x'], bird['speed_y'])
            
            bird['y'] += bird['speed_y']
            bird['x'] += bird['speed_x']
            
            if bird['y'] <= bird['min_y'] or bird['y'] >= bird['max_y']:
                bird['speed_y'] = -bird['speed_y']
            
            if bird['x'] > 850:
                for bird_id in bird['ids']:
                    self.canvas.delete(bird_id)
                
                used_y_positions = [b['y'] for b in self.birds if b != bird]
                while True:
                    new_y = random.randint(80, 280)
                    if not any(abs(new_y - used_y) < 40 for used_y in used_y_positions):
                        break
                
                new_x = -50
                new_speed_x = random.uniform(0.8, 1.8)
                new_speed_y = random.uniform(-0.15, 0.15)
                bird['ids'] = draw_bird(self.canvas, new_x, new_y, bird['flap_up'])
                bird['speed_x'] = new_speed_x
                bird['speed_y'] = new_speed_y
                bird['y'] = new_y
                bird['x'] = new_x
        
        self.root.after(50, self.animate_birds)

   
    
    def spawn_cars(self):
        """Create initial cars that will drive on the road and stop at gate."""
        car_colors = ['#3a7bc8', '#d44444', '#f5f5f5', '#2a2a2a', '#ffd93d', '#4a9d5f']
        road_y = 429
        
        # Gate location (at the guard shack, just before fence)
        self.gate_x = 490
        self.gate_timer = 0  # Timer for gate openings
        self.gate_open_interval = 3000  # Open gate every 3 seconds (in ms)
        self.last_gate_open = 0
        
        for i in range(6):
            # All cars approach from the left
            x = -50 - (i * 80)  # Spread them out initially
            
            speed = random.uniform(0.8, 1.2)
            color = random.choice(car_colors)
            
            car_ids = draw_car(self.canvas, x, road_y, color)
            self.cars.append({
                'ids': car_ids,
                'speed': speed,
                'base_speed': speed,
                'color': color,
                'x': x,
                'y': road_y,
                'state': 'approaching',  # approaching, waiting, entering, driving
                'wait_start': 0
            })
    
    def animate_cars(self):
        """Animate cars with gate queue system."""
        import time
        current_time = time.time() * 1000
        road_y = 429
        
        # Check if gate should open (every 3 seconds)
        if current_time - self.last_gate_open >= self.gate_open_interval:
            self.last_gate_open = current_time
            # Let the first waiting car through
            for car in self.cars:
                if car['state'] == 'waiting':
                    car['state'] = 'entering'
                    car['wait_start'] = current_time
                    break
        
        # Calculate how many cars are currently waiting
        waiting_cars = [c for c in self.cars if c['state'] == 'waiting']
        
        for car in self.cars:
            if car['state'] == 'approaching':
                # Car is driving toward the gate
                # Check if there are cars waiting ahead
                cars_ahead = [c for c in self.cars if c['state'] in ['waiting', 'approaching'] and c['x'] < car['x'] and c['x'] > car['x'] - 100]
                
                if cars_ahead:
                    # Stop behind the car ahead (maintain 15 pixel gap)
                    closest_car = max(cars_ahead, key=lambda c: c['x'])
                    stop_position = closest_car['x'] - 15
                    
                    if car['x'] >= stop_position:
                        car['speed'] = 0
                        car['state'] = 'waiting'
                    else:
                        car['speed'] = car['base_speed']
                        for car_id in car['ids']:
                            self.canvas.move(car_id, car['speed'], 0)
                        car['x'] += car['speed']
                else:
                    # No cars ahead, check distance to gate
                    if car['x'] >= self.gate_x - 20:
                        # Reached gate, stop and wait
                        car['speed'] = 0
                        car['state'] = 'waiting'
                    else:
                        # Keep driving toward gate
                        car['speed'] = car['base_speed']
                        for car_id in car['ids']:
                            self.canvas.move(car_id, car['speed'], 0)
                        car['x'] += car['speed']
            
            elif car['state'] == 'waiting':
                # Car is stopped at gate or in queue
                # Don't move, just wait
                pass
            
            elif car['state'] == 'entering':
                # Gate opened, car is entering (drives for 2 seconds then goes to 'driving')
                if current_time - car['wait_start'] < 2000:
                    # Drive through gate for 2 seconds
                    car['speed'] = car['base_speed']
                    for car_id in car['ids']:
                        self.canvas.move(car_id, car['speed'], 0)
                    car['x'] += car['speed']
                else:
                    # Done entering, now freely driving
                    car['state'] = 'driving'
            
            elif car['state'] == 'driving':
                # Car is past the gate, driving freely
                car['speed'] = car['base_speed']
                for car_id in car['ids']:
                    self.canvas.move(car_id, car['speed'], 0)
                car['x'] += car['speed']
                
                # Check if car went off screen
                if car['x'] > 850:
                    # Respawn car on the left
                    for car_id in car['ids']:
                        self.canvas.delete(car_id)
                    
                    new_x = -50
                    new_speed = random.uniform(0.8, 1.2)
                    car['ids'] = draw_car(self.canvas, new_x, road_y, car['color'])
                    car['speed'] = new_speed
                    car['base_speed'] = new_speed
                    car['x'] = new_x
                    car['state'] = 'approaching'
        
        self.root.after(50, self.animate_cars)
    
    def animate_gator(self):
        """Animate alligator appearing and disappearing from pond."""
        from landscape import draw_pond_with_gator
        
        self.gator_timer += 1
        
        if self.gator_timer >= 30:
            self.gator_visible = True
            self.gator_timer = 0
        
        if self.gator_timer < 5:
            show_gator = True
        else:
            show_gator = False
        
        self.canvas.delete('pond', 'gator')
        draw_pond_with_gator(self.canvas, gator_visible=show_gator)
        
        self.root.after(1000, self.animate_gator)
    
    def check_launch_status(self):
        """Check if launch actually happened or was postponed when countdown reaches zero."""
        if not self.launch_data:
            return
        
        print("Checking launch status...")
        
        # Re-fetch launches to get updated status
        launches = fetch_launches(5)
        current_launch_id = self.launch_data.get('id')
        
        # Find our current launch in the results
        updated_launch = None
        for launch in launches:
            if launch.get('id') == current_launch_id:
                updated_launch = launch
                break
        
        if updated_launch:
            # Check status
            # launch_description can be a string or dict
            launch_desc = updated_launch.get('launch_description', '')
            if isinstance(launch_desc, dict):
                status = launch_desc.get('description', '')
            else:
                status = launch_desc
            
            # Check if the launch time has changed (postponement)
            new_launch_time = updated_launch.get('t0') or updated_launch.get('win_open')
            
            if new_launch_time != self.launch_time:
                # Launch was postponed!
                print(f"Launch postponed! New time: {new_launch_time}")
                self.launch_time = new_launch_time
                self.launch_data = updated_launch
                # Update the info sign with new data
                self.canvas.delete('info_sign')
                draw_info_sign(self.canvas, self.launch_data, self.vehicle_name)
                return
            
            # Check if in flight or completed
            if status == 'In Flight':
                print("Launch is in flight - waiting for completion...")
                # Check again in 30 seconds
                self.root.after(30000, self.check_launch_status)
                return
            
            # Check launch result if available
            result = updated_launch.get('result')
            if result == 1:  # Success
                print("Launch confirmed successful! Loading next launch...")
                self.load_next_launch()
            elif result == 2:  # Failure
                print("Launch failed - loading next launch...")
                self.load_next_launch()
            elif result == 3:  # Partial failure
                print("Launch partial failure - loading next launch...")
                self.load_next_launch()
            elif status not in ['In Flight', 'Go', 'Go for Launch']:
                # Launch completed (no longer in flight), load next
                print(f"Launch status: {status} - loading next launch...")
                self.load_next_launch()
            else:
                # Still unclear, check again in 30 seconds
                print("Status unclear, checking again in 30 seconds...")
                self.root.after(30000, self.check_launch_status)
        else:
            # Couldn't find our launch, it might have been removed (scrubbed)
            print("Launch data no longer available - loading next launch")
            self.load_next_launch()
    
    def update_countdown(self):
        """Update the countdown display every second."""
        if not self.launch_time:
            self.root.after(1000, self.update_countdown)
            return
        
        countdown = get_countdown(self.launch_time)
        draw_countdown_display(self.canvas, countdown, self.launch_data)
        
        # Check if countdown reached zero
        if countdown and countdown != "LAUNCHED":
            if countdown['total_seconds'] <= 0 and countdown['total_seconds'] > -5:
                # At T-0, trigger launch immediately
                self.trigger_launch()
            elif countdown['total_seconds'] <= -10:
                # More than 10 seconds past T-0, check status
                self.check_launch_status()
        
        self.root.after(1000, self.update_countdown)
    
    def trigger_launch(self):
        """Trigger the launch animation at T-0."""
        if self.launch_animator and not self.launch_animator.is_launching:
            print("T-0! Launching rocket!")
            # Start checking status after launch animation
            self.launch_animator.start_launch(on_complete=self.check_post_launch_status)
    
    def check_post_launch_status(self):
        """Check status after launch animation completes."""
        print("Launch animation complete, checking status...")
        # Wait a few seconds then check if we should load next launch
        self.root.after(5000, self.check_launch_status)
    
    def test_launch(self):
        if self.launch_animator:
            print("Test launch initiated!")
            # Debug: check if rocket elements exist
            rocket_items = self.canvas.find_withtag('rocket')
            print(f"Found {len(rocket_items)} rocket elements")
            self.launch_animator.start_launch(on_complete=self.reset_same_rocket)
        else:
            print("No rocket to launch!")
    
    def reset_same_rocket(self):
        """Reset the same rocket after a test launch."""
        print("Resetting same rocket...")
        
        self.canvas.delete('launch_flame')
        self.canvas.delete('rocket')
        
        self.draw_rocket_with_tag()
        
        self.launch_animator = LaunchAnimation(
            self.canvas,
            rocket_tag='rocket',
            initial_x=620,
            initial_y=340,
            vehicle_name=self.vehicle_name
        )
        
        from landscape import draw_spotlights
        self.canvas.delete('spotlight')
        draw_spotlights(self.canvas, self.vehicle_name)
        
        print("Rocket reset complete!")
    
    def load_next_launch(self):
        """Load the next launch after T-0 launch completes."""
        print("Loading next launch...")
        
        self.canvas.delete('launch_flame')
        self.canvas.delete('rocket')
        
        # Fetch multiple launches to ensure we get a different one
        launches = fetch_launches(5)
        
        if not launches:
            print("No more launches available")
            return
        
        # Find a launch that's different from the current one AND not in flight
        current_launch_id = self.launch_data.get('id') if self.launch_data else None
        next_launch = None
        
        for launch in launches:
            # launch_description can be a string or dict
            launch_desc = launch.get('launch_description', '')
            if isinstance(launch_desc, dict):
                status = launch_desc.get('description', '')
            else:
                status = launch_desc
            
            if launch.get('id') != current_launch_id and status != 'In Flight':
                next_launch = launch
                break
        
        # If we couldn't find a different launch, just use the first non-in-flight one
        if not next_launch:
            for launch in launches:
                # launch_description can be a string or dict
                launch_desc = launch.get('launch_description', '')
                if isinstance(launch_desc, dict):
                    status = launch_desc.get('description', '')
                else:
                    status = launch_desc
                
                if status != 'In Flight':
                    next_launch = launch
                    break
        
        # Last resort - use first launch even if in flight
        if not next_launch:
            next_launch = launches[0]
        
        self.launch_data = next_launch
        self.launch_time = self.launch_data.get('t0') or self.launch_data.get('win_open')
        self.vehicle_name = self.launch_data.get('vehicle', {}).get('name', 'Unknown')
        
        # Check if new launch is in flight
        # launch_description can be a string or dict
        launch_desc = self.launch_data.get('launch_description', '')
        if isinstance(launch_desc, dict):
            status = launch_desc.get('description', '')
        else:
            status = launch_desc
        
        if status != 'In Flight':
            self.draw_rocket_with_tag()
            
            self.launch_animator = LaunchAnimation(
                self.canvas,
                rocket_tag='rocket',
                initial_x=620,
                initial_y=340,
                vehicle_name=self.vehicle_name
            )
        else:
            print("Next launch is also in flight - not displaying rocket")
            self.launch_animator = None
        
        self.canvas.delete('info_sign')
        draw_info_sign(self.canvas, self.launch_data, self.vehicle_name)
        
        from landscape import draw_spotlights
        self.canvas.delete('spotlight')
        draw_spotlights(self.canvas, self.vehicle_name)
        
        print("Next launch loaded!")


def main():
    """Main function to run the rocket launch display."""
    root = tk.Tk()
    app = LaunchPadDisplay(root)
    root.mainloop()


if __name__ == "__main__":
    main()