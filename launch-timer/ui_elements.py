#!/usr/bin/env python3
"""
UI elements for the launch display including countdown, info sign, and animations.
"""

import random

def draw_info_sign(canvas, launch_data, vehicle_name):
    """Draw launch info sign extending from the right edge of the screen."""
    if not launch_data:
        return
    
    # Position - extends from right edge
    sign_x = 800  # Right edge of canvas
    sign_y = 150
    sign_width = 85  # Extends leftward from edge
    sign_height = 160
    
    # Sign board - dark background with bright border
    canvas.create_rectangle(sign_x-sign_width, sign_y, sign_x, sign_y+sign_height, 
                           fill='#0a0a0a', outline='#ffd93d', width=3, tags='info_sign')
    
    # Title header with background
    canvas.create_rectangle(sign_x-sign_width, sign_y, sign_x, sign_y+24,
                           fill='#ffd93d', outline='', tags='info_sign')
    canvas.create_text(sign_x-sign_width/2, sign_y+12, text="NEXT LAUNCH",
                      font=('Courier', 10, 'bold'), fill='#000000', anchor='center', tags='info_sign')
    
    y_offset = sign_y + 36
    
    def wrap_text(text, max_chars):
        """Wrap text to multiple lines."""
        if len(text) <= max_chars:
            return [text]
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if len(test_line) <= max_chars + 1:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        
        if current_line:
            lines.append(current_line.strip())
        
        return lines[:3]
    
    # Mission name - larger, centered, prominent
    mission_name = launch_data.get('name', 'Unknown Mission')
    mission_lines = wrap_text(mission_name, 20)
    
    for line in mission_lines:
        canvas.create_text(sign_x-sign_width/2, y_offset, text=line,
                          font=('Courier', 7, 'bold'), fill='#ffffff',
                          anchor='center', tags='info_sign')
        y_offset += 9
    
    # Divider line
    y_offset += 8
    canvas.create_line(sign_x-sign_width+10, y_offset, sign_x-10, y_offset,
                      fill='#3a3a3a', width=1, tags='info_sign')
    y_offset += 12
    
    # Vehicle info
    canvas.create_text(sign_x-sign_width+12, y_offset, text="VEHICLE",
                      font=('Courier', 7, 'bold'), fill='#888888', 
                      anchor='w', tags='info_sign')
    y_offset += 10
    
    vehicle = vehicle_name
    vehicle_lines = wrap_text(vehicle, 20)
    for line in vehicle_lines[:2]:
        canvas.create_text(sign_x-sign_width/2, y_offset, text=line,
                          font=('Courier', 7), fill='#4a90e2', 
                          anchor='center', tags='info_sign')
        y_offset += 9
    
    y_offset += 7
    
    # Provider info
    canvas.create_text(sign_x-sign_width+12, y_offset, text="PROVIDER",
                      font=('Courier', 7, 'bold'), fill='#888888', 
                      anchor='w', tags='info_sign')
    y_offset += 10
    
    provider = launch_data.get('provider', {}).get('name', 'Unknown')
    provider_lines = wrap_text(provider, 20)
    for line in provider_lines[:2]:
        canvas.create_text(sign_x-sign_width/2, y_offset, text=line,
                          font=('Courier', 7), fill='#ffffff', 
                          anchor='center', tags='info_sign')
        y_offset += 9
    
    y_offset += 7
    
    # Location info
    canvas.create_text(sign_x-sign_width+12, y_offset, text="LOCATION",
                      font=('Courier', 7, 'bold'), fill='#888888', 
                      anchor='w', tags='info_sign')
    y_offset += 10
    
    pad = launch_data.get('pad', {})
    location = pad.get('location', {}).get('name', 'Unknown')
    # Shorten common location names
    location = location.replace('Space Force Station', 'SFS')
    location = location.replace('Air Force Base', 'AFB')
    location = location.replace('Space Launch Site', 'SLS')
    location_lines = wrap_text(location, 20)
    for line in location_lines[:2]:
        canvas.create_text(sign_x-sign_width/2, y_offset, text=line,
                          font=('Courier', 6), fill='#ffffff', 
                          anchor='center', tags='info_sign')
        y_offset += 8
    
    # Divider line before status
    y_offset += 6
    canvas.create_line(sign_x-sign_width+10, y_offset, sign_x-10, y_offset,
                      fill='#3a3a3a', width=1, tags='info_sign')
    y_offset += 12
    
    # Status badge at bottom - more prominent
    # launch_description can be a string or dict
    launch_desc = launch_data.get('launch_description', '')
    if isinstance(launch_desc, dict):
        status = launch_desc.get('description', 'Unknown')
    else:
        status = launch_desc if launch_desc else 'Unknown'
    
    status_colors = {
        'Go': '#00ff88',
        'Go for Launch': '#00ff88',
        'TBD': '#ffd93d', 
        'To Be Determined': '#ffd93d',
        'To Be Confirmed': '#ffd93d',
        'Success': '#00ff88',
        'Failure': '#ff4444',
        'Hold': '#ff9933',
        'In Flight': '#4a90e2'
    }
    status_color = status_colors.get(status, "#008f37")
    
    # Status box with colored background
    canvas.create_rectangle(sign_x-sign_width+12, y_offset-2, 
                           sign_x-12, y_offset+18,
                           fill=status_color, outline='', tags='info_sign')
    
    # Shorten status text if needed
    status_text = ('Go')
    canvas.create_text(sign_x-sign_width/2, y_offset+8, text=status_text.upper(),
                       font=('Courier', 9, 'bold'), fill='#00ff88', 
                       anchor='center', tags='info_sign')


def draw_countdown_display(canvas, countdown, launch_data):
    """Draw the countdown display at the top of the screen."""
    canvas.delete("countdown")
    
    y_top = 20
    
    if countdown == "LAUNCHED":
        canvas.create_rectangle(250, 10, 550, 80, fill='#1a1a1a', 
                                outline='#ff4444', width=3, tags="countdown")
        canvas.create_text(400, 45, text="LAUNCHED",
                           font=('Courier', 28, 'bold'), fill='#ff4444', tags="countdown")
    elif countdown:
        canvas.create_text(400, y_top, text="T-MINUS",
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
            
            canvas.create_rectangle(x, y_pos, x+box_width, y_pos+box_height,
                                    fill='#1a1a1a', outline=color, width=2, tags="countdown")
            
            canvas.create_text(x+box_width/2, y_pos+22, text=f"{value:02d}",
                               font=('Courier', 20, 'bold'), fill=color, tags="countdown")
            
            canvas.create_text(x+box_width/2, y_pos+40, text=label,
                               font=('Courier', 7), fill='#666666', tags="countdown")
    else:
        date_str = launch_data.get('sort_date', 'TBD') if launch_data else 'TBD'
        canvas.create_rectangle(250, 20, 550, 70, fill='#1a1a1a',
                                outline='#ffd93d', width=2, tags="countdown")
        canvas.create_text(400, 45, text=date_str,
                           font=('Courier', 12, 'bold'), fill='#ffd93d', tags="countdown")


def draw_smoke_effect(canvas, smoke_frame, launch_data, pad_x=620, pad_y=340, is_launching=False):
    """Draw slow horizontal white venting from left side of rocket that expands as it drifts."""
    canvas.delete("smoke")
    
    # Don't draw smoke if rocket is launching
    if is_launching:
        return
    
    if launch_data:
        # Vent position - halfway up the rocket on left side
        vent_y = pad_y - 60  # Halfway up a typical rocket
        vent_x_start = pad_x - 12  # Left side of rocket
        
        # Left side venting only - slow billowing cloud
        for i in range(12):  # More particles for continuous cloud
            # Slow horizontal movement to the left
            distance = (smoke_frame * 0.5 + i * 6) % 100  # Slower movement
            smoke_x = vent_x_start - distance
            
            # Slight vertical drift - less random jitter
            vertical_drift = (distance * 0.08)
            smoke_y = vent_y + vertical_drift + (i % 3 - 1) * 2  # Reduced random positioning
            
            # Opacity fades as it gets further away
            opacity = 255 - (distance * 2.5)
            
            if opacity > 20:
                # White/light gray colors - brighter near source
                if distance < 20:
                    # Start small and bright near rocket
                    gray_val = hex(max(235, min(255, 245 + (i % 5 - 2) * 3)))[2:]  # Less variation
                    size = 4 + (i % 3)  # Consistent small size
                else:
                    # Expand and become slightly darker as it drifts
                    gray_val = hex(max(200, min(240, 220 + (i % 5 - 2) * 5)))[2:]  # Less variation
                    # Size grows with distance - starts at 4-6, grows to 10-16
                    size = 4 + (i % 3) + int(distance / 6)
                
                if len(gray_val) == 1:
                    gray_val = '0' + gray_val
                smoke_color = f'#{gray_val}{gray_val}{gray_val}'
                
                # Draw as oval for softer, cloudier appearance
                canvas.create_oval(
                    smoke_x - size/2, smoke_y - size/2, 
                    smoke_x + size/2, smoke_y + size/2,
                    fill=smoke_color, outline='', tags="smoke"
                )


def draw_attribution(canvas):
    """Draw the data source attribution at the bottom."""
    canvas.create_text(400, 580, text="Data: RocketLaunch.Live",
                       font=('Courier', 7), fill='#666666')
    