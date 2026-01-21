#!/usr/bin/env python3
"""
Launch animation - handles rocket liftoff sequence at T-0.
Enhanced with realistic flickering flame animation.
"""

import random

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
        self.flicker_offset = 0  # For flame animation
        
        # Callback for when launch completes
        self.on_complete_callback = None
        
    def start_launch(self, on_complete=None):
        """
        Begin the launch sequence.
        
        Args:
            on_complete: Callback function to call when launch completes
        """
        if not self.is_launching:
            self.is_launching = True
            self.launch_frame = 0
            self.velocity = 0
            self.current_y = self.initial_y
            self.on_complete_callback = on_complete
            self.animate_launch()
    
    def animate_launch(self):
        """Animate one frame of the launch."""
        if not self.is_launching:
            return
        
        self.launch_frame += 1
        
        # Startup phase (frames 0-60): Build up flame for 2 seconds at 30 FPS
        if self.launch_frame < 60:
            self.flame_intensity = min(1.0, self.launch_frame / 60)
            self.draw_pixelated_flame()
        
        # Liftoff phase (frames 60+): Rocket rises
        elif self.launch_frame >= 60:
            # Accelerate rocket upward
            self.velocity = min(self.velocity + self.acceleration, self.max_velocity)
            
            # Move ALL rocket elements using the tag
            self.canvas.move(self.rocket_tag, 0, -self.velocity)
            
            self.current_y -= self.velocity
            
            # Draw exhaust flames
            self.draw_pixelated_flame()
            
            # Check if rocket is off screen
            if self.current_y < -200:
                self.complete_launch()
                return
        
        # Continue animation
        if self.is_launching:
            self.canvas.after(33, self.animate_launch)  # ~30 FPS
    
    def draw_pixelated_flame(self):
        """Draw realistic rocket exhaust flame with animated flickering."""
        # Clear previous flames
        for flame_id in self.flame_ids:
            try:
                self.canvas.delete(flame_id)
            except:
                pass
        self.flame_ids = []
        
        if self.flame_intensity == 0:
            return
        
        # Update flicker offset for animation
        self.flicker_offset += 1
        
        # Flame position (below rocket)
        flame_x = self.initial_x
        flame_y = self.current_y + 8
        
        # Pixel size for blocky look
        pixel_size = 3
        
        # Scale based on intensity
        scale = self.flame_intensity
        
        # Random flicker values for this frame
        flicker_scale = 1.0 + random.uniform(-0.15, 0.15)  # Size flicker
        brightness_shift = random.randint(-15, 15)  # Brightness flicker
        
        # Define flame pattern with animated variations
        flame_layers = self._get_flame_layers(flame_y, pixel_size, scale, flicker_scale, brightness_shift)
        glow_layers = self._get_glow_layers(flame_y, pixel_size, scale, flicker_scale, brightness_shift)
        
        # Draw glow first (behind)
        for row_offset, pixels in glow_layers:
            y = row_offset
            for x_offset, width, color in pixels:
                x = flame_x + x_offset * pixel_size * scale * flicker_scale
                
                pixel_id = self.canvas.create_rectangle(
                    x - pixel_size * width / 2, y,
                    x + pixel_size * width / 2, y + pixel_size,
                    fill=color, outline='', tags='launch_flame'
                )
                self.flame_ids.append(pixel_id)
        
        # Draw main flame with flicker
        for row_offset, pixels in flame_layers:
            y = row_offset
            for x_offset, width, color in pixels:
                x = flame_x + x_offset * pixel_size * scale * flicker_scale
                
                # Add random horizontal jitter to some pixels for turbulence
                if random.random() < 0.2:  # 20% of pixels get jitter
                    x += random.uniform(-2, 2)
                
                # Apply brightness adjustment
                adjusted_color = self._adjust_color_brightness(color, brightness_shift)
                
                # Create pixel with proper width
                pixel_id = self.canvas.create_rectangle(
                    x - pixel_size * width / 2, y,
                    x + pixel_size * width / 2, y + pixel_size,
                    fill=adjusted_color, outline='', tags='launch_flame'
                )
                self.flame_ids.append(pixel_id)
    
    def _get_flame_layers(self, base_y, pixel_size, scale, flicker_scale, brightness_shift):
        """Generate flame layer positions with flicker variation."""
        # Vary the flame height slightly
        height_variation = random.randint(-2, 2)
        
        layers = [
            # Row 0 - Bottom tip (brightest white)
            (base_y + 0 * pixel_size * scale, [(0, 1, '#ffffff')]),
            
            # Row 1-2 - Bright white core expanding
            (base_y + 1 * pixel_size * scale, [(0, 2, '#ffffff')]),
            (base_y + 2 * pixel_size * scale, [(-1, 1, '#ffffee'), (0, 2, '#ffffff'), (1, 1, '#ffffee')]),
            
            # Row 3-5 - Brilliant yellow
            (base_y + 3 * pixel_size * scale, [(-1, 1, '#ffff99'), (-0.5, 2, '#ffffcc'), (0.5, 2, '#ffffff'), (1.5, 1, '#ffffcc'), (2, 1, '#ffff99')]),
            (base_y + 4 * pixel_size * scale, [(-2, 1, '#ffee66'), (-1, 2, '#ffffaa'), (0, 2, '#ffffdd'), (1, 2, '#ffffaa'), (2, 1, '#ffee66')]),
            (base_y + 5 * pixel_size * scale, [(-2, 1, '#ffdd55'), (-1, 1, '#ffee88'), (0, 3, '#ffffbb'), (1, 1, '#ffee88'), (2, 1, '#ffdd55')]),
            
            # Row 6-8 - Yellow to orange transition
            (base_y + 6 * pixel_size * scale, [(-3, 1, '#ffcc44'), (-2, 2, '#ffdd77'), (-0.5, 3, '#ffee99'), (1.5, 2, '#ffdd77'), (3, 1, '#ffcc44')]),
            (base_y + 7 * pixel_size * scale, [(-3, 1, '#ffbb33'), (-2, 1, '#ffcc66'), (-1, 2, '#ffdd88'), (0, 2, '#ffee99'), (1, 2, '#ffdd88'), (2, 1, '#ffcc66'), (3, 1, '#ffbb33')]),
            (base_y + 8 * pixel_size * scale, [(-3, 1, '#ffaa22'), (-2, 2, '#ffbb55'), (0, 3, '#ffcc77'), (2, 2, '#ffbb55'), (3, 1, '#ffaa22')]),
            
            # Row 9-11 - Orange
            (base_y + 9 * pixel_size * scale, [(-4, 1, '#ff9911'), (-3, 2, '#ffaa44'), (-1, 3, '#ffbb66'), (1, 3, '#ffbb66'), (3, 2, '#ffaa44'), (4, 1, '#ff9911')]),
            (base_y + 10 * pixel_size * scale, [(-4, 1, '#ff8800'), (-3, 1, '#ff9922'), (-2, 2, '#ffaa55'), (0, 2, '#ffbb77'), (1, 2, '#ffaa55'), (2, 1, '#ff9922'), (4, 1, '#ff8800')]),
            (base_y + 11 * pixel_size * scale, [(-4, 1, '#ff7700'), (-3, 2, '#ff8833'), (-1, 2, '#ff9955'), (0, 2, '#ffaa66'), (1, 2, '#ff9955'), (2, 2, '#ff8833'), (4, 1, '#ff7700')]),
            
            # Row 12-14 - Orange to red
            (base_y + 12 * pixel_size * scale, [(-4, 1, '#ff6600'), (-3, 1, '#ff7722'), (-2, 2, '#ff8844'), (0, 3, '#ff9955'), (2, 2, '#ff8844'), (3, 1, '#ff7722'), (4, 1, '#ff6600')]),
            (base_y + 13 * pixel_size * scale, [(-4, 1, '#ff5500'), (-3, 2, '#ff6633'), (-1, 2, '#ff7755'), (1, 2, '#ff7755'), (2, 2, '#ff6633'), (4, 1, '#ff5500')]),
            (base_y + 14 * pixel_size * scale, [(-4, 1, '#ff4400'), (-3, 1, '#ff5522'), (-2, 2, '#ff6644'), (0, 2, '#ff7766'), (1, 2, '#ff6644'), (2, 1, '#ff5522'), (3, 1, '#ff4400')]),
            
            # Row 15-17 - Red
            (base_y + 15 * pixel_size * scale, [(-3, 1, '#ff3300'), (-2, 2, '#ff4422'), (0, 2, '#ff5544'), (1, 2, '#ff4422'), (3, 1, '#ff3300')]),
            (base_y + 16 * pixel_size * scale, [(-3, 1, '#ee2200'), (-2, 1, '#ff3311'), (-1, 2, '#ff4433'), (1, 2, '#ff4433'), (2, 1, '#ff3311'), (3, 1, '#ee2200')]),
            (base_y + 17 * pixel_size * scale, [(-3, 1, '#dd1100'), (-2, 2, '#ee2222'), (0, 2, '#ff3333'), (1, 2, '#ee2222'), (2, 1, '#dd1100')]),
            
            # Row 18-20 - Deep red tips (with height variation)
            (base_y + (18 + height_variation) * pixel_size * scale, [(-2, 1, '#cc0000'), (-1, 2, '#dd1111'), (1, 2, '#dd1111'), (2, 1, '#cc0000')]),
            (base_y + (19 + height_variation) * pixel_size * scale, [(-2, 1, '#bb0000'), (-1, 1, '#cc1100'), (0, 1, '#dd2200'), (1, 1, '#cc1100'), (2, 1, '#bb0000')]),
            (base_y + (20 + height_variation) * pixel_size * scale, [(-1, 1, '#aa0000'), (0, 1, '#bb0000'), (1, 1, '#aa0000')]),
        ]
        
        return layers
    
    def _get_glow_layers(self, base_y, pixel_size, scale, flicker_scale, brightness_shift):
        """Generate glow layer positions with flicker variation."""
        glow = [
            # Outer orange glow
            (base_y + 8 * pixel_size * scale, [(-5, 1, '#ffa080'), (5, 1, '#ffa080')]),
            (base_y + 10 * pixel_size * scale, [(-5, 1, '#ff9070'), (5, 1, '#ff9070')]),
            (base_y + 12 * pixel_size * scale, [(-5, 1, '#ff8060'), (5, 1, '#ff8060')]),
            # Outer red glow
            (base_y + 14 * pixel_size * scale, [(-4, 1, '#ff7050'), (4, 1, '#ff7050')]),
            (base_y + 16 * pixel_size * scale, [(-4, 1, '#ff6040'), (4, 1, '#ff6040')]),
            (base_y + 18 * pixel_size * scale, [(-3, 1, '#ee5030'), (3, 1, '#ee5030')]),
        ]
        
        return glow
    
    def _adjust_color_brightness(self, hex_color, shift):
        """Adjust a hex color's brightness by shift amount (-255 to 255)."""
        # Parse hex color
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Apply shift and clamp
        r = max(0, min(255, r + shift))
        g = max(0, min(255, g + shift))
        b = max(0, min(255, b + shift))
        
        # Convert back to hex
        return f'#{r:02x}{g:02x}{b:02x}'
    
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
        
        # Delete rocket (it's off screen)
        self.canvas.delete(self.rocket_tag)
        
        print("Launch complete!")
        
        # Call completion callback if provided
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