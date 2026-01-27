#!/usr/bin/env python3
"""
T-38 aircraft animation for flyby sequences - PIXEL ART STYLE.
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
        self.speed = 5
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
        """Draw the T-38 aircraft in pixel art style."""
        # Clear any existing aircraft
        self.clear_aircraft()
        
        # Aircraft is drawn facing the direction of travel
        if self.direction == 1:  # Flying right
            self.draw_t38_right()
        else:  # Flying left
            self.draw_t38_left()
    
    def draw_t38_right(self):
        """Draw pixel-art T-38 flying to the right."""
        x = self.x
        y = self.y
        
        # Color palette
        white = '#f5f5f5'
        light_gray = '#d8d8d8'
        med_blue = '#4a7dc8'
        dark_blue = '#1a3a6a'
        red = '#d62828'
        outline = '#0a1a3a'
        
        # === MAIN FUSELAGE BODY ===
        # White main body - pointed nose expanding to cockpit, tapering to tail
        fuselage_points = [
            x - 10, y,        # Nose point
            x + 5, y - 4,     # Expanding
            x + 20, y - 6,    # Cockpit area (widest)
            x + 35, y - 6,
            x + 50, y - 5,    # Tapering
            x + 65, y - 3,
            x + 75, y - 2,    # Tail
            x + 75, y + 2,    # Tail bottom
            x + 65, y + 3,
            x + 50, y + 5,
            x + 35, y + 6,
            x + 20, y + 6,
            x + 5, y + 4,
        ]
        
        # Main white body
        body = self.canvas.create_polygon(
            fuselage_points,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(body)
        
        # Subtle top shading (light gray)
        top_shade = self.canvas.create_polygon(
            x - 8, y,
            x + 10, y - 3,
            x + 30, y - 5,
            x + 55, y - 4,
            x + 72, y - 1,
            x + 70, y,
            x + 50, y - 2,
            x + 25, y - 3,
            x + 5, y - 1,
            fill=light_gray, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(top_shade)
        
        # === DARK BLUE UNDERSIDE BAND ===
        underside = self.canvas.create_polygon(
            x - 5, y + 2,
            x + 20, y + 5,
            x + 50, y + 5,
            x + 73, y + 2,
            x + 73, y + 1,
            x + 50, y + 3,
            x + 20, y + 3,
            x - 5, y + 1,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(underside)
        
        # === MEDIUM BLUE HORIZONTAL STRIPE ===
        stripe = self.canvas.create_rectangle(
            x + 12, y,
            x + 68, y + 3,
            fill=med_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(stripe)
        
        # === COCKPIT ===
        # Raised canopy base
        canopy_base = self.canvas.create_rectangle(
            x + 18, y - 8,
            x + 38, y - 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(canopy_base)
        
        # Front window
        window1 = self.canvas.create_rectangle(
            x + 19, y - 8,
            x + 27, y - 6,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(window1)
        
        # Rear window
        window2 = self.canvas.create_rectangle(
            x + 28, y - 8,
            x + 37, y - 6,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(window2)
        
        # White frame separator
        frame = self.canvas.create_rectangle(
            x + 27, y - 8,
            x + 28, y - 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(frame)
        
        # === BODY DETAILS ===
        # Small red square behind cockpit
        red_mark = self.canvas.create_rectangle(
            x + 40, y - 4,
            x + 43, y - 2,
            fill=red, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(red_mark)
        
        # Small dark panel on fuselage (in the stripe)
        panel = self.canvas.create_rectangle(
            x + 48, y + 1,
            x + 52, y + 2,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(panel)
        
        # === WINGS (small swept delta) ===
        # Top wing
        wing_top = self.canvas.create_polygon(
            x + 30, y - 6,
            x + 26, y - 14,
            x + 38, y - 12,
            x + 42, y - 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(wing_top)
        
        # Top wing shading
        wing_top_shade = self.canvas.create_polygon(
            x + 30, y - 6,
            x + 27, y - 13,
            x + 34, y - 11,
            x + 36, y - 6,
            fill=light_gray, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(wing_top_shade)
        
        # Bottom wing (no shading on bottom)
        wing_bottom = self.canvas.create_polygon(
            x + 30, y + 6,
            x + 26, y + 14,
            x + 38, y + 12,
            x + 42, y + 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(wing_bottom)
        
        # === TAIL SECTION ===
        # Vertical stabilizer
        tail = self.canvas.create_polygon(
            x + 66, y - 2,
            x + 64, y - 12,
            x + 73, y - 10,
            x + 75, y - 2,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(tail)
        
        # Tail shading
        tail_shade = self.canvas.create_polygon(
            x + 66, y - 2,
            x + 65, y - 10,
            x + 70, y - 9,
            x + 71, y - 2,
            fill=light_gray, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(tail_shade)
        
        # NASA meatball on tail
        # Blue circle
        nasa_circle = self.canvas.create_oval(
            x + 67, y - 8,
            x + 73, y - 4,
            fill=med_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nasa_circle)
        
        # Red vector slash
        nasa_vector = self.canvas.create_polygon(
            x + 68, y - 6.5,
            x + 72, y - 5.5,
            x + 71, y - 6.8,
            fill=red, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nasa_vector)
        
        # Horizontal stabilizers
        h_stab_top = self.canvas.create_polygon(
            x + 66, y - 2,
            x + 63, y - 7,
            x + 72, y - 6,
            x + 74, y - 2,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(h_stab_top)
        
        h_stab_bottom = self.canvas.create_polygon(
            x + 66, y + 2,
            x + 63, y + 7,
            x + 72, y + 6,
            x + 74, y + 2,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(h_stab_bottom)
        
        # === REGISTRATION TEXT ===
        reg_text = self.canvas.create_text(
            x + 58, y + 1.5,
            text="N901NA",
            font=('Courier', 5, 'bold'),
            fill=white,
            tags='aircraft'
        )
        self.aircraft_ids.append(reg_text)
        
        # === ENGINE NOZZLE ===
        nozzle = self.canvas.create_rectangle(
            x + 74, y - 2,
            x + 78, y + 2,
            fill='#2a2a2a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nozzle)
        
        # Inner nozzle
        nozzle_inner = self.canvas.create_rectangle(
            x + 75, y - 1,
            x + 77, y + 1,
            fill='#1a1a1a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nozzle_inner)
        
        # === DARK BLUE OUTLINE (draw last so it's on top) ===
        outline_elem = self.canvas.create_polygon(
            fuselage_points,
            fill='', outline=outline, width=2, tags='aircraft'
        )
        self.aircraft_ids.append(outline_elem)
        
        # Wing outlines
        wing_outline_top = self.canvas.create_polygon(
            x + 30, y - 6,
            x + 26, y - 14,
            x + 38, y - 12,
            x + 42, y - 6,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(wing_outline_top)
        
        wing_outline_bottom = self.canvas.create_polygon(
            x + 30, y + 6,
            x + 26, y + 14,
            x + 38, y + 12,
            x + 42, y + 6,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(wing_outline_bottom)
        
        # Tail outline
        tail_outline = self.canvas.create_polygon(
            x + 66, y - 2,
            x + 64, y - 12,
            x + 73, y - 10,
            x + 75, y - 2,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(tail_outline)
        
        # Cockpit outline
        canopy_outline = self.canvas.create_rectangle(
            x + 18, y - 8,
            x + 38, y - 6,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(canopy_outline)
    
    def draw_t38_left(self):
        """Draw pixel-art T-38 flying to the left (mirrored)."""
        x = self.x
        y = self.y
        
        # Color palette
        white = '#f5f5f5'
        light_gray = '#d8d8d8'
        med_blue = '#4a7dc8'
        dark_blue = '#1a3a6a'
        red = '#d62828'
        outline = '#0a1a3a'
        
        # === MAIN FUSELAGE BODY (mirrored) ===
        fuselage_points = [
            x + 10, y,
            x - 5, y - 4,
            x - 20, y - 6,
            x - 35, y - 6,
            x - 50, y - 5,
            x - 65, y - 3,
            x - 75, y - 2,
            x - 75, y + 2,
            x - 65, y + 3,
            x - 50, y + 5,
            x - 35, y + 6,
            x - 20, y + 6,
            x - 5, y + 4,
        ]
        
        body = self.canvas.create_polygon(
            fuselage_points,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(body)
        
        top_shade = self.canvas.create_polygon(
            x + 8, y,
            x - 10, y - 3,
            x - 30, y - 5,
            x - 55, y - 4,
            x - 72, y - 1,
            x - 70, y,
            x - 50, y - 2,
            x - 25, y - 3,
            x - 5, y - 1,
            fill=light_gray, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(top_shade)
        
        # === DARK BLUE UNDERSIDE ===
        underside = self.canvas.create_polygon(
            x + 5, y + 2,
            x - 20, y + 5,
            x - 50, y + 5,
            x - 73, y + 2,
            x - 73, y + 1,
            x - 50, y + 3,
            x - 20, y + 3,
            x + 5, y + 1,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(underside)
        
        # === STRIPE ===
        stripe = self.canvas.create_rectangle(
            x - 12, y,
            x - 68, y + 3,
            fill=med_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(stripe)
        
        # === COCKPIT ===
        canopy_base = self.canvas.create_rectangle(
            x - 18, y - 8,
            x - 38, y - 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(canopy_base)
        
        window1 = self.canvas.create_rectangle(
            x - 19, y - 8,
            x - 27, y - 6,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(window1)
        
        window2 = self.canvas.create_rectangle(
            x - 28, y - 8,
            x - 37, y - 6,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(window2)
        
        frame = self.canvas.create_rectangle(
            x - 27, y - 8,
            x - 28, y - 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(frame)
        
        # === DETAILS ===
        red_mark = self.canvas.create_rectangle(
            x - 40, y - 4,
            x - 43, y - 2,
            fill=red, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(red_mark)
        
        panel = self.canvas.create_rectangle(
            x - 48, y + 1,
            x - 52, y + 2,
            fill=dark_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(panel)
        
        # === WINGS ===
        wing_top = self.canvas.create_polygon(
            x - 30, y - 6,
            x - 26, y - 14,
            x - 38, y - 12,
            x - 42, y - 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(wing_top)
        
        wing_top_shade = self.canvas.create_polygon(
            x - 30, y - 6,
            x - 27, y - 13,
            x - 34, y - 11,
            x - 36, y - 6,
            fill=light_gray, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(wing_top_shade)
        
        wing_bottom = self.canvas.create_polygon(
            x - 30, y + 6,
            x - 26, y + 14,
            x - 38, y + 12,
            x - 42, y + 6,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(wing_bottom)
        
        # === TAIL ===
        tail = self.canvas.create_polygon(
            x - 66, y - 2,
            x - 64, y - 12,
            x - 73, y - 10,
            x - 75, y - 2,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(tail)
        
        tail_shade = self.canvas.create_polygon(
            x - 66, y - 2,
            x - 65, y - 10,
            x - 70, y - 9,
            x - 71, y - 2,
            fill=light_gray, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(tail_shade)
        
        # NASA logo
        nasa_circle = self.canvas.create_oval(
            x - 73, y - 8,
            x - 67, y - 4,
            fill=med_blue, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nasa_circle)
        
        nasa_vector = self.canvas.create_polygon(
            x - 72, y - 6.5,
            x - 68, y - 5.5,
            x - 69, y - 6.8,
            fill=red, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nasa_vector)
        
        # H-stabs
        h_stab_top = self.canvas.create_polygon(
            x - 66, y - 2,
            x - 63, y - 7,
            x - 72, y - 6,
            x - 74, y - 2,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(h_stab_top)
        
        h_stab_bottom = self.canvas.create_polygon(
            x - 66, y + 2,
            x - 63, y + 7,
            x - 72, y + 6,
            x - 74, y + 2,
            fill=white, outline='', tags='aircraft'
        )
        self.aircraft_ids.append(h_stab_bottom)
        
        # === TEXT ===
        reg_text = self.canvas.create_text(
            x - 58, y + 1.5,
            text="N901NA",
            font=('Courier', 5, 'bold'),
            fill=white,
            tags='aircraft'
        )
        self.aircraft_ids.append(reg_text)
        
        # === NOZZLE ===
        nozzle = self.canvas.create_rectangle(
            x - 74, y - 2,
            x - 78, y + 2,
            fill='#2a2a2a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nozzle)
        
        nozzle_inner = self.canvas.create_rectangle(
            x - 75, y - 1,
            x - 77, y + 1,
            fill='#1a1a1a', outline='', tags='aircraft'
        )
        self.aircraft_ids.append(nozzle_inner)
        
        # === OUTLINES ===
        outline_elem = self.canvas.create_polygon(
            fuselage_points,
            fill='', outline=outline, width=2, tags='aircraft'
        )
        self.aircraft_ids.append(outline_elem)
        
        wing_outline_top = self.canvas.create_polygon(
            x - 30, y - 6,
            x - 26, y - 14,
            x - 38, y - 12,
            x - 42, y - 6,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(wing_outline_top)
        
        wing_outline_bottom = self.canvas.create_polygon(
            x - 30, y + 6,
            x - 26, y + 14,
            x - 38, y + 12,
            x - 42, y + 6,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(wing_outline_bottom)
        
        tail_outline = self.canvas.create_polygon(
            x - 66, y - 2,
            x - 64, y - 12,
            x - 73, y - 10,
            x - 75, y - 2,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(tail_outline)
        
        canopy_outline = self.canvas.create_rectangle(
            x - 18, y - 8,
            x - 38, y - 6,
            fill='', outline=outline, width=1, tags='aircraft'
        )
        self.aircraft_ids.append(canopy_outline)
    
    def draw_trail(self):
        """Draw a contrail/exhaust trail behind the aircraft."""
        # Clear old trail segments (keep only last 30)
        while len(self.trail_ids) > 30:
            old_trail = self.trail_ids.pop(0)
            try:
                self.canvas.delete(old_trail)
            except:
                pass
        
        # Add new trail segment - positioned at exhaust
        trail_length = 20
        
        if self.direction == 1:  # Flying right
            trail_x = self.x + 76
        else:  # Flying left
            trail_x = self.x - 76
        
        # Create fading trail effect
        trail_id = self.canvas.create_line(
            trail_x, self.y,
            trail_x - (trail_length * self.direction), self.y,
            fill='#e8e8e8', width=2, tags='aircraft_trail'
        )
        self.trail_ids.append(trail_id)
    
    def update(self, delta_time):
        """Update aircraft position."""
        if not self.active:
            return
        
        # Move aircraft
        self.x += self.speed * self.direction
        
        # Draw trail occasionally
        if random.random() < 0.3:
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