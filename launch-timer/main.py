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
        self.smoke_frame = 0
        
        # Launch animation
        self.launch_animator = None
        self.rocket_ids = []
        
        # Gator animation
        self.gator_visible = False
        self.gator_timer = 0
        
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
        
        # Draw rocket - we'll use the 'rocket' tag to identify all rocket elements
        self.draw_rocket_with_tag()
        
        # Create launch animator
        self.launch_animator = LaunchAnimation(
            self.canvas,
            rocket_tag='rocket',  # Pass the tag instead of IDs
            initial_x=620,
            initial_y=340,
            vehicle_name=self.vehicle_name
        )
        
        draw_info_sign(self.canvas, self.launch_data, self.vehicle_name)
        draw_attribution(self.canvas)
        
        # Draw spotlights AFTER rocket so they appear on top
        from landscape import draw_spotlights
        draw_spotlights(self.canvas, self.vehicle_name)
    
    def draw_rocket_with_tag(self):
        """Draw the rocket with a 'rocket' tag on all elements."""
        # Import here to avoid circular imports
        import rockets
        
        # Temporarily modify the rocket drawing to add tags
        # We'll create a wrapper that adds tags to all canvas operations
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
        draw_smoke_effect(self.canvas, self.smoke_frame, self.launch_data)
        self.smoke_frame += 1
        self.root.after(100, self.animate_smoke)
    
    def spawn_birds(self):
        """Create initial birds at random positions off-screen."""
        used_y_positions = []
        for i in range(3):
            # Start off screen to the left
            x = -100 - (i * 150)  # Stagger them
            
            # Find a unique y position
            while True:
                y = random.randint(80, 280)
                # Make sure birds are at least 40 pixels apart vertically
                if not any(abs(y - used_y) < 40 for used_y in used_y_positions):
                    used_y_positions.append(y)
                    break
            
            speed_x = random.uniform(0.8, 1.8)
            speed_y = random.uniform(-0.15, 0.15)  # Gentle vertical movement
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
            # Update flap animation
            bird['flap_counter'] += 1
            if bird['flap_counter'] >= 8:  # Flap every 8 frames
                bird['flap_counter'] = 0
                bird['flap_up'] = not bird['flap_up']
                
                # Redraw bird with new flap position
                if bird['ids']:
                    coords = self.canvas.coords(bird['ids'][0])
                    if coords:
                        current_x = coords[0]
                        current_y = bird['y']
                        
                        # Remove old bird
                        for bird_id in bird['ids']:
                            self.canvas.delete(bird_id)
                        
                        # Draw new bird with flap
                        bird['ids'] = draw_bird(self.canvas, current_x, current_y, bird['flap_up'])
            
            # Move bird horizontally and vertically
            for bird_id in bird['ids']:
                self.canvas.move(bird_id, bird['speed_x'], bird['speed_y'])
            
            # Update y position and check bounds
            bird['y'] += bird['speed_y']
            bird['x'] += bird['speed_x']
            
            # Bounce off vertical boundaries
            if bird['y'] <= bird['min_y'] or bird['y'] >= bird['max_y']:
                bird['speed_y'] = -bird['speed_y']
            
            # Check if bird is off screen, respawn on left
            if bird['x'] > 850:
                # Remove old bird
                for bird_id in bird['ids']:
                    self.canvas.delete(bird_id)
                
                # Find new unique y position
                used_y_positions = [b['y'] for b in self.birds if b != bird]
                while True:
                    new_y = random.randint(80, 280)
                    if not any(abs(new_y - used_y) < 40 for used_y in used_y_positions):
                        break
                
                # Create new bird off screen to the left
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
        """Create initial cars near the VAB, starting off-screen."""
        car_colors = ['#3a7bc8', '#d44444', '#f5f5f5', '#2a2a2a', '#ffd93d']
        used_y_positions = []
        
        for i in range(2):
            # Randomly choose direction
            direction = random.choice([-1, 1])
            
            # Start off screen based on direction
            if direction == 1:  # Moving right
                x = -50 - (i * 30)  # Start left, stagger them
            else:  # Moving left
                x = 270 + (i * 30)  # Start right, stagger them
            
            # Find unique y position (ground level variations)
            while True:
                y = random.choice([368, 371, 374])  # Slight variations in road position
                if not any(abs(y - used_y) < 3 for used_y in used_y_positions):
                    used_y_positions.append(y)
                    break
            
            speed = random.uniform(0.4, 0.9)
            color = random.choice(car_colors)
            car_ids = draw_car(self.canvas, x, y, color)
            self.cars.append({
                'ids': car_ids,
                'speed': speed * direction,
                'direction': direction,
                'color': color,
                'x': x,
                'y': y
            })
    
    def animate_cars(self):
        """Animate cars driving around the VAB area."""
        for car in self.cars:
            # Move car
            for car_id in car['ids']:
                self.canvas.move(car_id, car['speed'], 0)
            
            car['x'] += car['speed']
            
            # Check if car is off screen, respawn on opposite side
            if car['ids']:
                # Moving right and off screen
                if car['direction'] == 1 and car['x'] > 270:
                    for car_id in car['ids']:
                        self.canvas.delete(car_id)
                    
                    # Find new unique y position
                    used_y_positions = [c['y'] for c in self.cars if c != car]
                    while True:
                        new_y = random.choice([368, 371, 374])
                        if not any(abs(new_y - used_y) < 3 for used_y in used_y_positions):
                            break
                    
                    # Respawn off screen to the left
                    new_speed = random.uniform(0.4, 0.9)
                    car['ids'] = draw_car(self.canvas, -50, new_y, car['color'])
                    car['speed'] = new_speed
                    car['x'] = -50
                    car['y'] = new_y
                
                # Moving left and off screen
                elif car['direction'] == -1 and car['x'] < -50:
                    for car_id in car['ids']:
                        self.canvas.delete(car_id)
                    
                    # Find new unique y position
                    used_y_positions = [c['y'] for c in self.cars if c != car]
                    while True:
                        new_y = random.choice([368, 371, 374])
                        if not any(abs(new_y - used_y) < 3 for used_y in used_y_positions):
                            break
                    
                    # Respawn off screen to the right
                    new_speed = random.uniform(0.4, 0.9)
                    car['ids'] = draw_car(self.canvas, 270, new_y, car['color'])
                    car['speed'] = -new_speed
                    car['x'] = 270
                    car['y'] = new_y
        
        self.root.after(60, self.animate_cars)
    
    def animate_gator(self):
        """Animate alligator appearing and disappearing from pond."""
        from landscape import draw_pond_with_gator
        
        self.gator_timer += 1
        
        # Every 30 seconds (30000ms / 1000ms per call = 30 calls)
        if self.gator_timer >= 30:
            self.gator_visible = True
            self.gator_timer = 0
        
        # Show gator for 5 seconds, then hide for 25 seconds
        if self.gator_timer < 5:
            show_gator = True
        else:
            show_gator = False
        
        # Redraw pond with or without gator
        self.canvas.delete('pond', 'gator')
        draw_pond_with_gator(self.canvas, gator_visible=show_gator)
        
        self.root.after(1000, self.animate_gator)  # Update every second
    
    def update_countdown(self):
        """Update the countdown display every second."""
        if not self.launch_time:
            self.root.after(1000, self.update_countdown)
            return
        
        countdown = get_countdown(self.launch_time)
        draw_countdown_display(self.canvas, countdown, self.launch_data)
        
        # Check if we hit T-0 and launch!
        if countdown and countdown != "LAUNCHED":
            if countdown['total_seconds'] <= 0:
                self.trigger_launch()
        
        self.root.after(1000, self.update_countdown)
    
    def trigger_launch(self):
        """Trigger the launch animation at T-0."""
        if self.launch_animator and not self.launch_animator.is_launching:
            print("T-0! Launching rocket!")
            # Pass callback to load next launch after completion
            self.launch_animator.start_launch(on_complete=self.load_next_launch)
    
    def test_launch(self):
        """Test button handler to manually trigger launch."""
        if self.launch_animator:
            print("Test launch initiated!")
            # Pass callback to reset same rocket after test
            self.launch_animator.start_launch(on_complete=self.reset_same_rocket)
        else:
            print("No rocket to launch!")
    
    def reset_same_rocket(self):
        """Reset the same rocket after a test launch."""
        print("Resetting same rocket...")
        
        # Clear any existing launch flames
        self.canvas.delete('launch_flame')
        self.canvas.delete('rocket')
        
        # Redraw the same rocket with tag
        self.draw_rocket_with_tag()
        
        # Recreate launch animator
        self.launch_animator = LaunchAnimation(
            self.canvas,
            rocket_tag='rocket',
            initial_x=620,
            initial_y=340,
            vehicle_name=self.vehicle_name
        )
        
        # Redraw spotlights
        from landscape import draw_spotlights
        self.canvas.delete('spotlight')
        draw_spotlights(self.canvas, self.vehicle_name)
        
        print("Rocket reset complete!")
    
    def load_next_launch(self):
        """Load the next launch after T-0 launch completes."""
        print("Loading next launch...")
        
        # Clear any existing launch flames and rocket
        self.canvas.delete('launch_flame')
        self.canvas.delete('rocket')
        
        # Fetch new launch data
        launches = fetch_launches(1)
        
        if not launches:
            print("No more launches available")
            return
        
        self.launch_data = launches[0]
        self.launch_time = self.launch_data.get('t0') or self.launch_data.get('win_open')
        self.vehicle_name = self.launch_data.get('vehicle', {}).get('name', 'Unknown')
        
        # Redraw rocket with new vehicle
        self.draw_rocket_with_tag()
        
        # Recreate launch animator
        self.launch_animator = LaunchAnimation(
            self.canvas,
            rocket_tag='rocket',
            initial_x=620,
            initial_y=340,
            vehicle_name=self.vehicle_name
        )
        
        # Update info sign with new launch data
        self.canvas.delete('info_sign')
        draw_info_sign(self.canvas, self.launch_data, self.vehicle_name)
        
        # Redraw spotlights
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