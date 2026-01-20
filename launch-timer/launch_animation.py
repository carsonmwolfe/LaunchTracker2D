#!/usr/bin/env python3
"""
Launch animation - handles rocket liftoff sequence at T-0.
"""

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
        self.acceleration = 0.08  # Slower acceleration
        self.max_velocity = 4  # Slower max speed
        
        # Flame parameters
        self.flame_ids = []
        self.flame_intensity = 0
        
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
        """Draw realistic rocket exhaust flame with gradients."""
        # Clear previous flames
        for flame_id in self.flame_ids:
            try:
                self.canvas.delete(flame_id)
            except:
                pass
        self.flame_ids = []
        
        if self.flame_intensity == 0:
            return
        
        # Flame position (below rocket)
        flame_x = self.initial_x
        flame_y = self.current_y + 8
        
        # Pixel size for blocky look
        pixel_size = 3
        
        # Scale based on intensity
        scale = self.flame_intensity
        
        # Define flame pattern - wider at top, narrower at bottom, with gradient layers
        # Format: (row, [(x_offset, width, color)])
        flame_layers = [
            # Row 0 - Bottom tip (brightest white)
            (0, [(0, 1, '#ffffff')]),
            
            # Row 1-2 - Bright white core expanding
            (1, [(0, 2, '#ffffff')]),
            (2, [(-1, 1, '#ffffee'), (0, 2, '#ffffff'), (1, 1, '#ffffee')]),
            
            # Row 3-5 - Brilliant yellow
            (3, [(-1, 1, '#ffff99'), (-0.5, 2, '#ffffcc'), (0.5, 2, '#ffffff'), (1.5, 1, '#ffffcc'), (2, 1, '#ffff99')]),
            (4, [(-2, 1, '#ffee66'), (-1, 2, '#ffffaa'), (0, 2, '#ffffdd'), (1, 2, '#ffffaa'), (2, 1, '#ffee66')]),
            (5, [(-2, 1, '#ffdd55'), (-1, 1, '#ffee88'), (0, 3, '#ffffbb'), (1, 1, '#ffee88'), (2, 1, '#ffdd55')]),
            
            # Row 6-8 - Yellow to orange transition
            (6, [(-3, 1, '#ffcc44'), (-2, 2, '#ffdd77'), (-0.5, 3, '#ffee99'), (1.5, 2, '#ffdd77'), (3, 1, '#ffcc44')]),
            (7, [(-3, 1, '#ffbb33'), (-2, 1, '#ffcc66'), (-1, 2, '#ffdd88'), (0, 2, '#ffee99'), (1, 2, '#ffdd88'), (2, 1, '#ffcc66'), (3, 1, '#ffbb33')]),
            (8, [(-3, 1, '#ffaa22'), (-2, 2, '#ffbb55'), (0, 3, '#ffcc77'), (2, 2, '#ffbb55'), (3, 1, '#ffaa22')]),
            
            # Row 9-11 - Orange
            (9, [(-4, 1, '#ff9911'), (-3, 2, '#ffaa44'), (-1, 3, '#ffbb66'), (1, 3, '#ffbb66'), (3, 2, '#ffaa44'), (4, 1, '#ff9911')]),
            (10, [(-4, 1, '#ff8800'), (-3, 1, '#ff9922'), (-2, 2, '#ffaa55'), (0, 2, '#ffbb77'), (1, 2, '#ffaa55'), (2, 1, '#ff9922'), (4, 1, '#ff8800')]),
            (11, [(-4, 1, '#ff7700'), (-3, 2, '#ff8833'), (-1, 2, '#ff9955'), (0, 2, '#ffaa66'), (1, 2, '#ff9955'), (2, 2, '#ff8833'), (4, 1, '#ff7700')]),
            
            # Row 12-14 - Orange to red
            (12, [(-4, 1, '#ff6600'), (-3, 1, '#ff7722'), (-2, 2, '#ff8844'), (0, 3, '#ff9955'), (2, 2, '#ff8844'), (3, 1, '#ff7722'), (4, 1, '#ff6600')]),
            (13, [(-4, 1, '#ff5500'), (-3, 2, '#ff6633'), (-1, 2, '#ff7755'), (1, 2, '#ff7755'), (2, 2, '#ff6633'), (4, 1, '#ff5500')]),
            (14, [(-4, 1, '#ff4400'), (-3, 1, '#ff5522'), (-2, 2, '#ff6644'), (0, 2, '#ff7766'), (1, 2, '#ff6644'), (2, 1, '#ff5522'), (3, 1, '#ff4400')]),
            
            # Row 15-17 - Red
            (15, [(-3, 1, '#ff3300'), (-2, 2, '#ff4422'), (0, 2, '#ff5544'), (1, 2, '#ff4422'), (3, 1, '#ff3300')]),
            (16, [(-3, 1, '#ee2200'), (-2, 1, '#ff3311'), (-1, 2, '#ff4433'), (1, 2, '#ff4433'), (2, 1, '#ff3311'), (3, 1, '#ee2200')]),
            (17, [(-3, 1, '#dd1100'), (-2, 2, '#ee2222'), (0, 2, '#ff3333'), (1, 2, '#ee2222'), (2, 1, '#dd1100')]),
            
            # Row 18-20 - Deep red tips
            (18, [(-2, 1, '#cc0000'), (-1, 2, '#dd1111'), (1, 2, '#dd1111'), (2, 1, '#cc0000')]),
            (19, [(-2, 1, '#bb0000'), (-1, 1, '#cc1100'), (0, 1, '#dd2200'), (1, 1, '#cc1100'), (2, 1, '#bb0000')]),
            (20, [(-1, 1, '#aa0000'), (0, 1, '#bb0000'), (1, 1, '#aa0000')]),
        ]
        
        # Add outer glow layers for more realistic gradient effect (using lighter solid colors)
        glow_layers = [
            # Outer orange glow (lighter tints)
            (8, [(-5, 1, '#ffa080'), (5, 1, '#ffa080')]),
            (10, [(-5, 1, '#ff9070'), (5, 1, '#ff9070')]),
            (12, [(-5, 1, '#ff8060'), (5, 1, '#ff8060')]),
            # Outer red glow
            (14, [(-4, 1, '#ff7050'), (4, 1, '#ff7050')]),
            (16, [(-4, 1, '#ff6040'), (4, 1, '#ff6040')]),
            (18, [(-3, 1, '#ee5030'), (3, 1, '#ee5030')]),
        ]
        
        # Draw glow first (behind)
        for row_offset, pixels in glow_layers:
            y = flame_y + row_offset * pixel_size * scale
            for x_offset, width, color in pixels:
                x = flame_x + x_offset * pixel_size * scale
                
                pixel_id = self.canvas.create_rectangle(
                    x - pixel_size * width / 2, y,
                    x + pixel_size * width / 2, y + pixel_size,
                    fill=color, outline='', tags='launch_flame'
                )
                self.flame_ids.append(pixel_id)
        
        # Draw main flame
        for row_offset, pixels in flame_layers:
            y = flame_y + row_offset * pixel_size * scale
            for x_offset, width, color in pixels:
                x = flame_x + x_offset * pixel_size * scale
                
                # Create pixel with proper width
                pixel_id = self.canvas.create_rectangle(
                    x - pixel_size * width / 2, y,
                    x + pixel_size * width / 2, y + pixel_size,
                    fill=color, outline='', tags='launch_flame'
                )
                self.flame_ids.append(pixel_id)


    
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