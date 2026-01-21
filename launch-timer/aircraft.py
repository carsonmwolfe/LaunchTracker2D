#!/usr/bin/env python3
"""
T-38 aircraft animation for flyby sequences.
"""

import random
import time


class T38Aircraft:
    """T-38 trainer jet that flies across the screen periodically."""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.active = False
        self.x = 0
        self.y = 0
        self.direction = 1  # 1 for left-to-right, -1 for right-to-left
        self.speed = 4
        self.aircraft_ids = []
        self.trail_ids = []
        # Set first flyby to happen 45-60 seconds after initialization
        current_time = time.time() * 1000
        self.next_flyby_time = current_time + random.randint(45000, 60000)
        self.last_update_time = 0
        
    def should_start_flyby(self, current_time):
        """Check if it's time to start a new flyby."""
        actual_current_time = time.time() * 1000
        if not self.active and actual_current_time >= self.next_flyby_time:
            return True
        return False
    
    def start_flyby(self):
        """Initialize a new flyby."""
        self.active = True
        
        # Random direction
        self.direction = random.choice([-1, 1])
        
        # Random height in upper sky area (well above launch tower at y=140)
        self.y = random.randint(60, 120)
        
        # Start position off screen
        if self.direction == 1:  # Left to right
            self.x = -100
        else:  # Right to left
            self.x = 900
        
        # Draw the aircraft
        self.draw_aircraft()
    
    def draw_aircraft(self):
        """Draw the T-38 aircraft based on reference image."""
        # Clear any existing aircraft
        self.clear_aircraft()
        
        # Aircraft is drawn facing the direction of travel
        if self.direction == 1:  # Flying right
            self.draw_t38_right()
        else:  # Flying left
            self.draw_t38_left()
    
    def draw_t38_right(self):
        """Draw T-38 flying to the right (based on reference image)."""
        x = self.x
        y = self.y
        
        # Main fuselage body - white/light gray, long and sleek
        fuse_id = self.canvas.create_rectangle(
            x, y - 4, x + 60, y + 4,
            fill='#e8e8e8', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(fuse_id)
        
        # Upper fuselage detail (lighter)
        upper_fuse = self.canvas.create_rectangle(
            x + 5, y - 4, x + 55, y - 1,
            fill='#f8f8f8', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(upper_fuse)
        
        # Blue stripe along bottom fuselage
        stripe_id = self.canvas.create_rectangle(
            x + 10, y + 1, x + 50, y + 4,
            fill='#2a5a9a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(stripe_id)
        
        # Nose cone (pointed, dark gray)
        nose_id = self.canvas.create_polygon(
            x + 60, y - 3,
            x + 70, y,
            x + 60, y + 3,
            fill='#3a3a3a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nose_id)
        
        # Cockpit canopy (two-seater, dark blue)
        cockpit1_id = self.canvas.create_rectangle(
            x + 20, y - 5, x + 28, y - 3,
            fill='#1a3a5a', outline='#2a2a2a', tags='aircraft'
        )
        self.aircraft_ids.append(cockpit1_id)
        
        cockpit2_id = self.canvas.create_rectangle(
            x + 30, y - 5, x + 38, y - 3,
            fill='#1a3a5a', outline='#2a2a2a', tags='aircraft'
        )
        self.aircraft_ids.append(cockpit2_id)
        
        # Main wings (swept back, near middle of fuselage)
        # Top wing
        wing_top = self.canvas.create_polygon(
            x + 25, y - 4,
            x + 23, y - 12,
            x + 35, y - 4,
            fill='#d8d8d8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(wing_top)
        
        # Bottom wing
        wing_bottom = self.canvas.create_polygon(
            x + 25, y + 4,
            x + 23, y + 12,
            x + 35, y + 4,
            fill='#c8c8c8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(wing_bottom)
        
        # Horizontal stabilizers (tail wings) - smaller, at back
        # Top tail wing
        tail_wing_top = self.canvas.create_polygon(
            x + 3, y - 1,
            x + 2, y - 7,
            x + 10, y - 1,
            fill='#d8d8d8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(tail_wing_top)
        
        # Bottom tail wing
        tail_wing_bottom = self.canvas.create_polygon(
            x + 3, y + 1,
            x + 2, y + 7,
            x + 10, y + 1,
            fill='#c8c8c8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(tail_wing_bottom)
        
        # Vertical tail stabilizer
        tail_id = self.canvas.create_polygon(
            x + 5, y,
            x + 5, y - 10,
            x + 12, y - 5,
            x + 12, y,
            fill='#e8e8e8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(tail_id)
        
        # Engine nacelles (twin engines on sides)
        # Top engine nacelle
        engine_top = self.canvas.create_rectangle(
            x + 15, y - 6, x + 45, y - 4,
            fill='#5a5a5a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(engine_top)
        
        # Bottom engine nacelle
        engine_bottom = self.canvas.create_rectangle(
            x + 15, y + 4, x + 45, y + 6,
            fill='#4a4a4a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(engine_bottom)
        
        # Engine intakes (dark areas near front)
        intake_top = self.canvas.create_rectangle(
            x + 15, y - 6, x + 20, y - 4,
            fill='#2a2a2a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(intake_top)
        
        intake_bottom = self.canvas.create_rectangle(
            x + 15, y + 4, x + 20, y + 6,
            fill='#2a2a2a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(intake_bottom)
        
        # Engine exhausts (back - red/orange glow)
        exhaust_top = self.canvas.create_rectangle(
            x - 2, y - 6, x + 3, y - 4,
            fill='#ff6600', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(exhaust_top)
        
        exhaust_bottom = self.canvas.create_rectangle(
            x - 2, y + 4, x + 3, y + 6,
            fill='#ff6600', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(exhaust_bottom)
    
    def draw_t38_left(self):
        """Draw T-38 flying to the left (mirrored)."""
        x = self.x
        y = self.y
        
        # Main fuselage body - white/light gray, long and sleek
        fuse_id = self.canvas.create_rectangle(
            x - 60, y - 4, x, y + 4,
            fill='#e8e8e8', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(fuse_id)
        
        # Upper fuselage detail (lighter)
        upper_fuse = self.canvas.create_rectangle(
            x - 55, y - 4, x - 5, y - 1,
            fill='#f8f8f8', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(upper_fuse)
        
        # Blue stripe along bottom fuselage
        stripe_id = self.canvas.create_rectangle(
            x - 50, y + 1, x - 10, y + 4,
            fill='#2a5a9a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(stripe_id)
        
        # Nose cone (pointed, dark gray)
        nose_id = self.canvas.create_polygon(
            x - 60, y - 3,
            x - 70, y,
            x - 60, y + 3,
            fill='#3a3a3a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nose_id)
        
        # Cockpit canopy (two-seater, dark blue)
        cockpit1_id = self.canvas.create_rectangle(
            x - 28, y - 5, x - 20, y - 3,
            fill='#1a3a5a', outline='#2a2a2a', tags='aircraft'
        )
        self.aircraft_ids.append(cockpit1_id)
        
        cockpit2_id = self.canvas.create_rectangle(
            x - 38, y - 5, x - 30, y - 3,
            fill='#1a3a5a', outline='#2a2a2a', tags='aircraft'
        )
        self.aircraft_ids.append(cockpit2_id)
        
        # Main wings (swept back, near middle of fuselage)
        # Top wing
        wing_top = self.canvas.create_polygon(
            x - 25, y - 4,
            x - 23, y - 12,
            x - 35, y - 4,
            fill='#d8d8d8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(wing_top)
        
        # Bottom wing
        wing_bottom = self.canvas.create_polygon(
            x - 25, y + 4,
            x - 23, y + 12,
            x - 35, y + 4,
            fill='#c8c8c8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(wing_bottom)
        
        # Horizontal stabilizers (tail wings) - smaller, at back
        # Top tail wing
        tail_wing_top = self.canvas.create_polygon(
            x - 3, y - 1,
            x - 2, y - 7,
            x - 10, y - 1,
            fill='#d8d8d8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(tail_wing_top)
        
        # Bottom tail wing
        tail_wing_bottom = self.canvas.create_polygon(
            x - 3, y + 1,
            x - 2, y + 7,
            x - 10, y + 1,
            fill='#c8c8c8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(tail_wing_bottom)
        
        # Vertical tail stabilizer
        tail_id = self.canvas.create_polygon(
            x - 5, y,
            x - 5, y - 10,
            x - 12, y - 5,
            x - 12, y,
            fill='#e8e8e8', outline='#3a3a3a', tags='aircraft'
        )
        self.aircraft_ids.append(tail_id)
        
        # Engine nacelles (twin engines on sides)
        # Top engine nacelle
        engine_top = self.canvas.create_rectangle(
            x - 45, y - 6, x - 15, y - 4,
            fill='#5a5a5a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(engine_top)
        
        # Bottom engine nacelle
        engine_bottom = self.canvas.create_rectangle(
            x - 45, y + 4, x - 15, y + 6,
            fill='#4a4a4a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(engine_bottom)
        
        # Engine intakes (dark areas near front)
        intake_top = self.canvas.create_rectangle(
            x - 20, y - 6, x - 15, y - 4,
            fill='#2a2a2a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(intake_top)
        
        intake_bottom = self.canvas.create_rectangle(
            x - 20, y + 4, x - 15, y + 6,
            fill='#2a2a2a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(intake_bottom)
        
        # Engine exhausts (back - red/orange glow)
        exhaust_top = self.canvas.create_rectangle(
            x - 3, y - 6, x + 2, y - 4,
            fill='#ff6600', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(exhaust_top)
        
        exhaust_bottom = self.canvas.create_rectangle(
            x - 3, y + 4, x + 2, y + 6,
            fill='#ff6600', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(exhaust_bottom)
    
    def draw_trail(self):
        """Draw a contrail/exhaust trail behind the aircraft."""
        # Clear old trail segments (keep only last 20)
        while len(self.trail_ids) > 20:
            old_trail = self.trail_ids.pop(0)
            try:
                self.canvas.delete(old_trail)
            except:
                pass
        
        # Add new trail segment
        trail_length = 15
        trail_offset = -50 if self.direction == 1 else 50
        
        # Create fading trail effect
        trail_id = self.canvas.create_line(
            self.x + trail_offset, self.y,
            self.x + trail_offset - (trail_length * self.direction), self.y,
            fill='#d8d8d8', width=2, tags='aircraft_trail'
        )
        self.trail_ids.append(trail_id)
    
    def update(self, delta_time):
        """Update aircraft position."""
        if not self.active:
            return
        
        # Move aircraft
        self.x += self.speed * self.direction
        
        # Draw trail
        if random.random() < 0.3:  # Don't draw trail every frame
            self.draw_trail()
        
        # Redraw aircraft at new position
        self.draw_aircraft()
        
        # Check if aircraft has left the screen
        if self.direction == 1 and self.x > 900:
            self.end_flyby()
        elif self.direction == -1 and self.x < -100:
            self.end_flyby()
    
    def end_flyby(self):
        """End the current flyby and schedule next one."""
        self.active = False
        self.clear_aircraft()
        self.clear_trail()
        
        # Schedule next flyby in 45-60 seconds from NOW
        current_time = time.time() * 1000
        self.next_flyby_time = current_time + random.randint(45000, 60000)
        self.last_update_time = 0
    
    def clear_aircraft(self):
        """Remove aircraft from canvas."""
        for aircraft_id in self.aircraft_ids:
            try:
                self.canvas.delete(aircraft_id)
            except:
                pass
        self.aircraft_ids = []
    
    def clear_trail(self):
        """Remove trail from canvas."""
        for trail_id in self.trail_ids:
            try:
                self.canvas.delete(trail_id)
            except:
                pass
        self.trail_ids = []