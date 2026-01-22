#!/usr/bin/env python3
"""
Pixel Launch Pad Countdown Display with Kennedy Space Center Background
Main entry point for the application.
"""

import tkinter as tk
import random
from api_client import fetch_launches, get_countdown
from landscape import draw_background, draw_bird, draw_car, draw_car_vertical
from rockets import draw_rocket_on_pad
from ui_elements import (
    draw_info_sign,
    draw_countdown_display,
    draw_smoke_effect,
    draw_attribution
)
from launch_animation import LaunchAnimation
from aircraft import T38Aircraft


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

        # Update notification animation
        self.notification_active = False
        self.notification_offset = 150  # Start offscreen
        self.notification_timer = 0
        
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
        self.fetch_and_display()
        
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
        self.animate_notification()
    
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
        
        # Check if rocket is currently in flight
        # launch_description can be a string or dict
        launch_desc = self.launch_data.get('launch_description', '')
        if isinstance(launch_desc, dict):
            status = launch_desc.get('description', '')
        else:
            status = launch_desc
        
        if status == 'In Flight':
            print("Rocket is in flight - not displaying on pad")
        else:
            # Draw rocket
            self.draw_rocket_with_tag()
            
            # Create launch animator
            self.launch_animator = LaunchAnimation(
                self.canvas,
                rocket_tag='rocket',
                initial_x=620,
                initial_y=340,
                vehicle_name=self.vehicle_name
            )
        
        draw_info_sign(self.canvas, self.launch_data, self.vehicle_name)
        draw_attribution(self.canvas)
        
        # Draw spotlights AFTER rocket so they appear on top
        from landscape import draw_spotlights
        draw_spotlights(self.canvas, self.vehicle_name)
        
        # Trigger update notification
        self.show_update_notification()
    
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
        """Animate sky color transitions based on time of day."""
        colors = self.get_current_sky_colors_with_transition()
        
        # Update sky rectangle
        sky_items = self.canvas.find_withtag('sky')
        for item in sky_items:
            self.canvas.itemconfig(item, fill=colors['sky'])
        
        # Update ocean
        ocean_items = self.canvas.find_withtag('ocean')
        for item in ocean_items:
            self.canvas.itemconfig(item, fill=colors['ocean'])
        
        # Update horizon
        horizon_items = self.canvas.find_withtag('horizon')
        for item in horizon_items:
            self.canvas.itemconfig(item, fill=colors['horizon'])
        
        # Update clouds
        cloud_items = self.canvas.find_withtag('cloud')
        for item in cloud_items:
            self.canvas.itemconfig(item, fill=colors['cloud'])
        
        # Update stars visibility (show/hide based on time)
        from datetime import datetime
        hour = datetime.now().hour
        if hour >= 18 or hour < 6:
            # Show stars at night
            star_items = self.canvas.find_withtag('stars')
            for item in star_items:
                self.canvas.itemconfig(item, state='normal')
        else:
            # Hide stars during day
            star_items = self.canvas.find_withtag('stars')
            for item in star_items:
                self.canvas.itemconfig(item, state='hidden')
        
        # Update spotlights
        from landscape import draw_spotlights
        self.canvas.delete('spotlight')
        draw_spotlights(self.canvas, self.vehicle_name)
        
        # Check again in 30 seconds
        self.root.after(30000, self.animate_sky_colors)
    
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

    def show_update_notification(self):
        """Trigger the update notification to slide in."""
        self.notification_active = True
        self.notification_offset = 150  # Start offscreen
        self.notification_timer = 0
    
    def animate_notification(self):
        """Animate the update notification sliding in and out."""
        if self.notification_active:
            self.notification_timer += 1
            
            # Slide in from RIGHT (frames 0-20)
            if self.notification_timer <= 20:
                # Start at 150 (offscreen right), move to 0 (visible)
                self.notification_offset = 150 * (1 - (self.notification_timer / 20))
            # Stay visible (frames 21-100) - visible for ~2.4 seconds
            elif self.notification_timer <= 100:
                self.notification_offset = 0
            # Slide out to RIGHT (frames 101-120)
            elif self.notification_timer <= 120:
                # Move from 0 (visible) to 150 (offscreen right)
                progress = (self.notification_timer - 100) / 20
                self.notification_offset = 150 * progress
            # Hide notification
            else:
                self.notification_active = False
                self.canvas.delete('update_notification')
                self.root.after(30, self.animate_notification)
                return
        
        # Redraw notification if active
        if self.notification_active:
            from ui_elements import draw_update_notification
            self.canvas.delete('update_notification')
            draw_update_notification(self.canvas, self.notification_offset)
        
        self.root.after(30, self.animate_notification)
    
    def spawn_cars(self):
        """Create initial cars that will drive on the road and park."""
        car_colors = ['#3a7bc8', '#d44444', '#f5f5f5', '#2a2a2a', '#ffd93d', '#4a9d5f']
        road_y = 429
        
        for i in range(4):
            will_park = random.choice([True, False])
            direction = random.choice([-1, 1])
            
            if direction == 1:
                x = -50 - (i * 40)
            else:
                x = 850 + (i * 40)
            
            speed = random.uniform(0.5, 1.0)
            color = random.choice(car_colors)
            
            parking_spot = None
            if will_park:
                parking_areas = [
                    {'name': 'vab', 'x_range': (60, 200), 'y': 390},
                    {'name': 'hangar', 'x_range': (245, 325), 'y': 390},
                    {'name': 'lcc', 'x_range': (348, 422), 'y': 390}
                ]
                parking_area = random.choice(parking_areas)
                parking_spot = {
                    'area': parking_area['name'],
                    'x': random.randint(parking_area['x_range'][0], parking_area['x_range'][1]),
                    'y': parking_area['y'],
                    'reached': False
                }
            
            car_ids = draw_car(self.canvas, x, road_y, color)
            self.cars.append({
                'ids': car_ids,
                'speed': speed * direction,
                'direction': direction,
                'color': color,
                'x': x,
                'y': road_y,
                'will_park': will_park,
                'parking_spot': parking_spot,
                'is_parked': False,
                'parked_timer': 0,
                'turning_to_park': False,
                'type': 'horizontal'
            })
    
    def animate_cars(self):
        """Animate cars driving on the road, parking, and leaving."""
        road_y = 429
        
        for car in self.cars:
            if car['is_parked']:
                car['parked_timer'] += 1
                if car['parked_timer'] > 167:
                    for car_id in car['ids']:
                        self.canvas.delete(car_id)
                    car['ids'] = []
                    
                    direction = random.choice([-1, 1])
                    if direction == 1:
                        new_x = -50
                    else:
                        new_x = 850
                    
                    will_park = random.choice([True, False])
                    parking_spot = None
                    
                    if will_park:
                        parking_areas = [
                            {'name': 'vab', 'x_range': (60, 200), 'y': 390},
                            {'name': 'hangar', 'x_range': (245, 325), 'y': 390},
                            {'name': 'lcc', 'x_range': (348, 422), 'y': 390}
                        ]
                        parking_area = random.choice(parking_areas)
                        parking_spot = {
                            'area': parking_area['name'],
                            'x': random.randint(parking_area['x_range'][0], parking_area['x_range'][1]),
                            'y': parking_area['y'],
                            'reached': False
                        }
                    
                    new_speed = random.uniform(0.5, 1.0)
                    car['ids'] = draw_car(self.canvas, new_x, road_y, car['color'])
                    car['speed'] = new_speed * direction
                    car['direction'] = direction
                    car['x'] = new_x
                    car['y'] = road_y
                    car['will_park'] = will_park
                    car['parking_spot'] = parking_spot
                    car['is_parked'] = False
                    car['parked_timer'] = 0
                    car['turning_to_park'] = False
                    car['type'] = 'horizontal'
                
                continue
            
            if car['will_park'] and not car['turning_to_park'] and car['parking_spot']:
                parking_x = car['parking_spot']['x']
                
                if abs(car['x'] - parking_x) < 5:
                    car['turning_to_park'] = True
                    for car_id in car['ids']:
                        self.canvas.delete(car_id)
                    car['ids'] = draw_car_vertical(self.canvas, parking_x, car['parking_spot']['y'], car['color'])
                    car['x'] = parking_x
                    car['y'] = car['parking_spot']['y']
                    car['is_parked'] = True
                    car['type'] = 'vertical'
                    continue
            
            for car_id in car['ids']:
                self.canvas.move(car_id, car['speed'], 0)
            
            car['x'] += car['speed']
            
            if car['ids'] and not car['will_park']:
                if (car['direction'] == 1 and car['x'] > 850) or (car['direction'] == -1 and car['x'] < -50):
                    for car_id in car['ids']:
                        self.canvas.delete(car_id)
                    
                    direction = random.choice([-1, 1])
                    if direction == 1:
                        new_x = -50
                    else:
                        new_x = 850
                    
                    will_park = random.choice([True, False])
                    parking_spot = None
                    
                    if will_park:
                        parking_areas = [
                            {'name': 'vab', 'x_range': (60, 200), 'y': 390},
                            {'name': 'hangar', 'x_range': (245, 325), 'y': 390},
                            {'name': 'lcc', 'x_range': (348, 422), 'y': 390}
                        ]
                        parking_area = random.choice(parking_areas)
                        parking_spot = {
                            'area': parking_area['name'],
                            'x': random.randint(parking_area['x_range'][0], parking_area['x_range'][1]),
                            'y': parking_area['y'],
                            'reached': False
                        }
                    
                    new_speed = random.uniform(0.5, 1.0)
                    car['ids'] = draw_car(self.canvas, new_x, road_y, car['color'])
                    car['speed'] = new_speed * direction
                    car['direction'] = direction
                    car['x'] = new_x
                    car['y'] = road_y
                    car['will_park'] = will_park
                    car['parking_spot'] = parking_spot
                    car['is_parked'] = False
                    car['parked_timer'] = 0
                    car['turning_to_park'] = False
                    car['type'] = 'horizontal'
        
        self.root.after(60, self.animate_cars)
    
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
                self.show_update_notification()
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
        
        # Show update notification
        self.show_update_notification()
        
        print("Next launch loaded!")


def main():
    """Main function to run the rocket launch display."""
    root = tk.Tk()
    app = LaunchPadDisplay(root)
    root.mainloop()


if __name__ == "__main__":
    main()