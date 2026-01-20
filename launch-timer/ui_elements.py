#!/usr/bin/env python3
"""
UI elements for the launch display including countdown, info sign, and animations.
"""

import random


def draw_info_sign(canvas, launch_data, vehicle_name):
    """Draw launch info sign to the right of the launch pad.
    
    Position is based on launch tower location:
    - Launch tower is at x=635 (tower_x = platform_x + 85, where platform_x = 550)
    - Sign should be positioned to the right of the tower
    """
    if not launch_data:
        return
    
    # Position sign to the right of the launch tower/pad area
    # Tower is around x=635-680, so sign goes at x=720
    sign_x = 720
    sign_y = 290
    sign_width = 70
    sign_height = 55
    
    # Sign post - metal pole
    canvas.create_rectangle(sign_x-2, sign_y+sign_height, sign_x+2, sign_y+sign_height+20, 
                           fill='#5a5a5a', outline='#4a4a4a', width=1)
    
    # Sign board - dark background with bright border
    canvas.create_rectangle(sign_x-sign_width, sign_y, sign_x+sign_width, sign_y+sign_height, 
                           fill='#1a1a1a', outline='#ffd93d', width=3)
    
    # Inner border for style
    canvas.create_rectangle(sign_x-sign_width+4, sign_y+4, sign_x+sign_width-4, sign_y+sign_height-4, 
                           fill='', outline='#3a3a3a', width=1)
    
    # Mission name - top line
    mission_name = launch_data.get('name', 'Unknown Mission')
    if len(mission_name) > 22:
        mission_name = mission_name[:19] + "..."
    canvas.create_text(sign_x, sign_y+12, text=mission_name,
                       font=('Courier', 8, 'bold'), fill='#ffffff', anchor='center')
    
    # Provider - second line
    provider = launch_data.get('provider', {}).get('name', 'Unknown')
    if len(provider) > 22:
        provider = provider[:19] + "..."
    canvas.create_text(sign_x, sign_y+25, text=provider,
                       font=('Courier', 7), fill='#74b9ff', anchor='center')
    
    # Vehicle - third line
    vehicle = vehicle_name
    if len(vehicle) > 22:
        vehicle = vehicle[:19] + "..."
    canvas.create_text(sign_x, sign_y+36, text=vehicle,
                       font=('Courier', 7), fill='#a29bfe', anchor='center')
    
    # Pad name - bottom line
    pad = launch_data.get('pad', {})
    pad_name = pad.get('name', 'Unknown Pad')
    if len(pad_name) > 22:
        pad_name = pad_name[:19] + "..."
    canvas.create_text(sign_x, sign_y+47, text=pad_name,
                       font=('Courier', 6), fill='#ffd93d', anchor='center')

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
        date_str = launch_data.get('date_str', 'TBD') if launch_data else 'TBD'
        canvas.create_rectangle(250, 20, 550, 70, fill='#1a1a1a',
                                outline='#ffd93d', width=2, tags="countdown")
        canvas.create_text(400, 45, text=date_str,
                           font=('Courier', 12, 'bold'), fill='#ffd93d', tags="countdown")


def draw_smoke_effect(canvas, smoke_frame, launch_data, pad_x=605, pad_y=340):
    """Draw animated smoke rising from rocket base."""
    canvas.delete("smoke")
    
    if launch_data:
        for i in range(8):
            smoke_y = pad_y + 5 - (smoke_frame + i * 3) % 40
            smoke_x = pad_x + random.randint(-15, 15)
            opacity = 255 - ((smoke_frame + i * 3) % 40) * 6
            
            if opacity > 50:
                gray_val = hex(max(100, min(200, 150 + random.randint(-20, 20))))[2:]
                if len(gray_val) == 1:
                    gray_val = '0' + gray_val
                smoke_color = f'#{gray_val}{gray_val}{gray_val}'
                size = random.randint(3, 7)
                canvas.create_rectangle(
                    smoke_x, smoke_y, smoke_x + size, smoke_y + size,
                    fill=smoke_color, outline='', tags="smoke"
                )


def draw_attribution(canvas):
    """Draw the data source attribution at the bottom."""
    canvas.create_text(400, 580, text="Data: RocketLaunch.Live",
                       font=('Courier', 7), fill='#666666')