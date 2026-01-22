#!/usr/bin/env python3
"""
Launch animation - handles rocket liftoff sequence at T-0.
Enhanced with realistic flame based on real fire reference.
"""

import random
import math

class LaunchAnimation:
    def __init__(self, canvas, rocket_tag, initial_x, initial_y, vehicle_name=None):
        """
        Initialize launch animation.
        
        Args:
            canvas: The tkinter canvas
            rocket_tag: Tag identifying all rocket elements
            initial_x: Starting x position
            initial_y: Starting y position (ground level)
            vehicle_name: Name of the rocket vehicle
        """
        self.canvas = canvas
        self.rocket_tag = rocket_tag
        self.initial_x = initial_x
        self.initial_y = initial_y
        self.current_y = initial_y
        self.vehicle_name = vehicle_name
        
        # Animation parameters
        self.is_launching = False
        self.launch_frame = 0
        self.velocity = 0
        self.acceleration = 0.08
        self.max_velocity = 4
        
        # Flame parameters
        self.flame_ids = []
        self.flame_intensity = 0
        self.flame_particles = []  # Individual flame particles
        self.vent_particles = []  # Horizontal venting particles
        
        # Callback for when launch completes
        self.on_complete_callback = None
        
    def start_launch(self, on_complete=None):
        """Begin the launch sequence."""
        if not self.is_launching:
            self.is_launching = True
            self.launch_frame = 0
            self.velocity = 0
            self.current_y = self.initial_y
            self.flame_particles = []
            self.vent_particles = []
            self.on_complete_callback = on_complete
            self.animate_launch()
    
    def animate_launch(self):
        """Animate one frame of the launch."""
        if not self.is_launching:
            return
        
        self.launch_frame += 1
        
        # Startup phase (frames 0-150): Build up flame for 5 seconds at 30 FPS
        if self.launch_frame < 150:
            self.flame_intensity = min(1.0, self.launch_frame / 150)
            self.draw_horizontal_vents()  # Draw venting
            self.draw_realistic_flame()
        
        # Liftoff phase (frames 150+): Rocket rises
        elif self.launch_frame >= 150:
            # Accelerate rocket upward
            self.velocity = min(self.velocity + self.acceleration, self.max_velocity)
            
            # Debug output every 30 frames
            if (self.launch_frame - 150) % 30 == 0:
                rocket_items = self.canvas.find_withtag(self.rocket_tag)
                print(f"Frame {self.launch_frame}: Moving {len(rocket_items)} elements, velocity={self.velocity:.2f}, current_y={self.current_y:.2f}")
                if len(rocket_items) > 0:
                    # Check position of first rocket element
                    coords = self.canvas.coords(rocket_items[0])
                    print(f"  First element coords: {coords}")
            
            # Move ALL rocket elements using the tag
            move_result = self.canvas.move(self.rocket_tag, 0, -self.velocity)
            
            self.current_y -= self.velocity
            
            # Draw exhaust flames
            self.draw_realistic_flame()
            
            # Check if rocket is off screen
            if self.current_y < -200:
                self.complete_launch()
                return
        
        # Continue animation
        if self.is_launching:
            self.canvas.after(33, self.animate_launch)
    
    def draw_realistic_flame(self):
        """Draw realistic flame based on actual fire reference."""
        # Clear previous flames
        for flame_id in self.flame_ids:
            try:
                self.canvas.delete(flame_id)
            except:
                pass
        self.flame_ids = []
        
        if self.flame_intensity == 0:
            return
        
        # Flame stays at rocket's current position
        flame_x = self.initial_x
        flame_y = self.current_y + 8
        
        # Update and age existing particles
        new_particles = []
        for particle in self.flame_particles:
            particle['age'] += 1
            # Particles move DOWN (away from rocket moving up)
            particle['y'] += particle['velocity_y']
            particle['x'] += particle['velocity_x']
            
            # Particle dies after certain age
            if particle['age'] < particle['lifetime']:
                new_particles.append(particle)
        
        self.flame_particles = new_particles
        
        # Spawn new flame particles at rocket base
        num_particles = int(20 * self.flame_intensity)
        for _ in range(num_particles):
            # Create particle at rocket's current base position
            particle = {
                'x': flame_x + random.uniform(-8, 8),
                'y': flame_y,
                'velocity_x': random.uniform(-0.5, 0.5),
                'velocity_y': random.uniform(2.0, 4.5),  # Downward speed (positive = down)
                'age': 0,
                'lifetime': random.randint(12, 25),
                'size': random.uniform(3, 8),
                'type': random.choice(['core', 'core', 'mid', 'outer'])  # More core particles
            }
            self.flame_particles.append(particle)
        
        # Draw particles from front to back (lower/newer first for proper layering)
        sorted_particles = sorted(self.flame_particles, key=lambda p: p['y'])
        
        for particle in sorted_particles:
            age_ratio = particle['age'] / particle['lifetime']
            
            # Determine color based on age and type
            if particle['type'] == 'core':
                # Hot white/yellow core
                if age_ratio < 0.2:
                    color = '#ffffff'
                elif age_ratio < 0.4:
                    color = '#ffffcc'
                elif age_ratio < 0.6:
                    color = '#ffff88'
                else:
                    color = '#ffdd44'
            elif particle['type'] == 'mid':
                # Orange middle zone
                if age_ratio < 0.3:
                    color = '#ffcc00'
                elif age_ratio < 0.5:
                    color = '#ffaa00'
                elif age_ratio < 0.7:
                    color = '#ff8800'
                else:
                    color = '#ff6600'
            else:
                # Red/dark outer zone
                if age_ratio < 0.25:
                    color = '#ff6600'
                elif age_ratio < 0.5:
                    color = '#ff4400'
                elif age_ratio < 0.75:
                    color = '#dd2200'
                else:
                    color = '#aa1100'
            
            # Fade out near end of life
            if age_ratio > 0.85:
                if random.random() > 0.7:  # Start becoming transparent/invisible
                    continue
            
            # Size decreases with age
            current_size = particle['size'] * (1.2 - age_ratio * 0.8)
            
            # Add shimmer/wobble
            wobble_x = math.sin(particle['age'] * 0.3) * 1.5
            wobble_y = math.cos(particle['age'] * 0.4) * 0.8
            
            draw_x = particle['x'] + wobble_x
            draw_y = particle['y'] + wobble_y
            
            # Draw particle as oval for more organic look
            particle_id = self.canvas.create_oval(
                draw_x - current_size/2, draw_y - current_size/2,
                draw_x + current_size/2, draw_y + current_size/2,
                fill=color, outline='', tags='launch_flame'
            )
            self.flame_ids.append(particle_id)
        
        # Add bright core glow at base
        num_core = int(8 * self.flame_intensity)
        for i in range(num_core):
            core_x = flame_x + random.uniform(-5, 5)
            core_y = flame_y + random.uniform(0, 8)
            core_size = random.uniform(4, 9)
            
            # Bright white/yellow core with occasional flicker
            brightness = random.uniform(0.9, 1.0)
            if brightness > 0.95:
                core_color = '#ffffff'
            else:
                core_color = '#ffffee'
            
            core_id = self.canvas.create_oval(
                core_x - core_size/2, core_y - core_size/2,
                core_x + core_size/2, core_y + core_size/2,
                fill=core_color, outline='', tags='launch_flame'
            )
            self.flame_ids.append(core_id)
        
        # Add sparks (occasional bright particles shooting downward)
        if random.random() > 0.5:
            num_sparks = random.randint(2, 4)
            for _ in range(num_sparks):
                spark_x = flame_x + random.uniform(-12, 12)
                spark_y = flame_y + random.uniform(5, 35)
                spark_size = random.uniform(1.5, 3)
                spark_color = random.choice(['#ffffff', '#ffffcc', '#ffff88'])
                
                spark_id = self.canvas.create_rectangle(
                    spark_x, spark_y,
                    spark_x + spark_size, spark_y + spark_size,
                    fill=spark_color, outline='', tags='launch_flame'
                )
                self.flame_ids.append(spark_id)
        
        # Add heat distortion lines below rocket
        if self.launch_frame >= 150:  # Only during active burn
            for i in range(3):
                distortion_x = flame_x + random.uniform(-15, 15)
                distortion_y = flame_y + random.uniform(40, 70)
                wave_offset = math.sin(self.launch_frame * 0.2 + i) * 3
                
                distortion_id = self.canvas.create_line(
                    distortion_x + wave_offset, distortion_y,
                    distortion_x + wave_offset + random.uniform(-2, 2), distortion_y + 8,
                    fill='#ffaa44', width=1, tags='launch_flame'
                )
                self.flame_ids.append(distortion_id)
    
    def draw_horizontal_vents(self):
        """Draw horizontal gas venting from rocket sides during pre-launch."""
        # Vent position - halfway up the rocket body
        vent_y = self.current_y - 60  # Halfway up a typical rocket
        vent_x_left = self.initial_x - 12  # Left side of rocket
        vent_x_right = self.initial_x + 12  # Right side of rocket
        
        # Update existing vent particles
        new_vents = []
        for vent in self.vent_particles:
            vent['age'] += 1
            vent['x'] += vent['velocity_x']
            vent['y'] += vent['velocity_y']
            
            # Vent particles fade and drift
            if vent['age'] < vent['lifetime']:
                new_vents.append(vent)
        
        self.vent_particles = new_vents
        
        # Spawn new vent particles (occasional bursts)
        if random.random() > 0.7:  # 30% chance each frame
            # Left side vent
            for _ in range(random.randint(2, 4)):
                vent = {
                    'x': vent_x_left,
                    'y': vent_y + random.uniform(-3, 3),
                    'velocity_x': random.uniform(-1.5, -0.5),  # Move left
                    'velocity_y': random.uniform(-0.3, 0.3),  # Slight vertical drift
                    'age': 0,
                    'lifetime': random.randint(20, 35),
                    'size': random.uniform(2, 5),
                    'color': random.choice(['#ffffff', '#f5f5f5', '#eeeeee', '#e8e8e8'])
                }
                self.vent_particles.append(vent)
            
            # Right side vent
            for _ in range(random.randint(2, 4)):
                vent = {
                    'x': vent_x_right,
                    'y': vent_y + random.uniform(-3, 3),
                    'velocity_x': random.uniform(0.5, 1.5),  # Move right
                    'velocity_y': random.uniform(-0.3, 0.3),  # Slight vertical drift
                    'age': 0,
                    'lifetime': random.randint(20, 35),
                    'size': random.uniform(2, 5),
                    'color': random.choice(['#ffffff', '#f5f5f5', '#eeeeee', '#e8e8e8'])
                }
                self.vent_particles.append(vent)
        
        # Draw vent particles
        for vent in self.vent_particles:
            age_ratio = vent['age'] / vent['lifetime']
            
            # Fade out near end of life
            if age_ratio > 0.7:
                if random.random() > 0.5:  # Start becoming transparent
                    continue
            
            # Size increases slightly as gas expands
            current_size = vent['size'] * (1.0 + age_ratio * 0.5)
            
            # Slight wobble
            wobble = math.sin(vent['age'] * 0.2) * 0.5
            
            vent_id = self.canvas.create_oval(
                vent['x'] - current_size/2, vent['y'] + wobble - current_size/2,
                vent['x'] + current_size/2, vent['y'] + wobble + current_size/2,
                fill=vent['color'], outline='', tags='launch_flame'
            )
            self.flame_ids.append(vent_id)
    
    def complete_launch(self):
        """Clean up after launch animation completes."""
        self.is_launching = False
        
        # Clear flames
        for flame_id in self.flame_ids:
            try:
                self.canvas.delete(flame_id)
            except:
                pass
        self.flame_ids = []
        self.flame_particles = []
        self.vent_particles = []
        
        # Delete rocket
        self.canvas.delete(self.rocket_tag)
        
        print("Launch complete!")
        
        if self.on_complete_callback:
            self.on_complete_callback()
    
    def stop(self):
        """Stop the animation immediately."""
        self.is_launching = False
        
        # Clear flames
        for flame_id in self.flame_ids:
            try:
                self.canvas.delete(flame_id)
            except:
                pass
        self.flame_ids = []
        self.flame_particles = []
        self.vent_particles = []