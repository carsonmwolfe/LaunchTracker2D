#!/usr/bin/env python3
"""
Kennedy Space Center landscape and background drawing functions.
Enhanced VAB building with more details based on reference image.
"""

import random
from datetime import datetime


def get_sky_colors():
    """Get sky and ocean colors based on current time of day."""
    now = datetime.now()
    hour = now.hour
    
    # 10am-4pm: Day (blue sky)
    if 10 <= hour < 16:
        return {
            'sky': '#87ceeb',
            'ocean': '#1a8b9e',
            'horizon': '#156673',
            'cloud': '#ffffff'
        }
    # 4pm-6pm: Sunset (orange)
    elif 16 <= hour < 18:
        return {
            'sky': '#ff9933',
            'ocean': '#1a5b6e',
            'horizon': '#0d3d4a',
            'cloud': '#ffd9b3'
        }
    # 6am-10am: Sunrise (orange/pink)
    elif 6 <= hour < 10:
        return {
            'sky': '#ff9966',
            'ocean': '#2a5b6e',
            'horizon': '#1d4a5a',
            'cloud': '#ffe5cc'
        }
    # 6pm-6am: Night (dark)
    else:
        return {
            'sky': '#0a0a1e',
            'ocean': '#0d1a2e',
            'horizon': '#050d1a',
            'cloud': '#d0d0d0'
        }


def draw_stars(canvas):
    """Draw stars for nighttime."""
    random.seed(42)
    for _ in range(60):
        x = random.randint(0, 800)
        y = random.randint(0, 340)
        size = random.choice([1, 2])
        brightness = random.choice(['#ffffff', '#ffff99', '#aaaaaa'])
        canvas.create_oval(x, y, x+size, y+size, fill=brightness, outline='', tags='stars')


def draw_pixel_grass(canvas):
    """Draw pixel grass details on the ground."""
    random.seed(123)
    grass_colors = ['#4a7c2a', '#6a9c4a', '#5a8c3a']
    
    for i in range(100):
        x = random.randint(0, 800)
        y = random.randint(368, 387)
        color = random.choice(grass_colors)
        if random.choice([True, False]):
            canvas.create_rectangle(x, y, x+2, y+4, fill=color, outline='')
        else:
            canvas.create_line(x, y, x, y+3, fill=color, width=1)



#!/usr/bin/env python3
"""
VAB building - exact replica of the reference image.
"""

def draw_vab_building(canvas):
    """Draw the Vehicle Assembly Building exactly matching the reference."""
    vab_x = 60
    vab_y = 200
    main_width = 140
    main_height = 150
    
    # === BACKGROUND ELEMENTS FIRST ===
    
    # Far right gray panels (background depth)
    canvas.create_rectangle(
        vab_x + main_width, vab_y + 10,
        vab_x + main_width + 25, vab_y + main_height,
        fill="#7a7e84", outline=""
    )
    canvas.create_rectangle(
        vab_x + main_width + 25, vab_y + 15,
        vab_x + main_width + 40, vab_y + main_height,
        fill="#5a5e64", outline=""
    )
    
    # === MAIN BUILDING BODY ===
    canvas.create_rectangle(
        vab_x, vab_y,
        vab_x + main_width, vab_y + main_height,
        fill="#f0ebe3", outline=""
    )
    
    # Black outline around main building
    canvas.create_rectangle(
        vab_x, vab_y,
        vab_x + main_width, vab_y + main_height,
        fill="", outline="#000000", width=2
    )
    
    # === TOP ROOF SECTION ===
    canvas.create_rectangle(
        vab_x, vab_y,
        vab_x + main_width, vab_y + 12,
        fill="#3a3e44", outline=""
    )
    
    # Roof equipment
    canvas.create_rectangle(vab_x + 25, vab_y - 8, vab_x + 33, vab_y, fill="#5a4e44", outline="")
    canvas.create_rectangle(vab_x + 50, vab_y - 6, vab_x + 57, vab_y, fill="#4a4a4a", outline="")
    canvas.create_rectangle(vab_x + 100, vab_y - 8, vab_x + 108, vab_y, fill="#4a4a4a", outline="")
    
    # === CENTER TOWER SECTION (DARK GRAY) ===
    center_x = vab_x + 50
    center_width = 44
    tower_top = vab_y + 25
    canvas.create_rectangle(
        center_x, tower_top,
        center_x + center_width, vab_y + main_height,
        fill="#5a5e64", outline=""
    )
    
    # White border around center tower
    canvas.create_rectangle(
        center_x, tower_top,
        center_x + center_width, vab_y + main_height,
        fill="", outline="#ffffff", width=2
    )
    
    # === MAIN DOOR INSIDE CENTER TOWER ===
    door_x = center_x + 8
    door_y = tower_top + 15
    door_w = 28
    door_h = 88
    
    canvas.create_rectangle(
        door_x, door_y,
        door_x + door_w, door_y + door_h,
        fill="#e0e0e0", outline=""
    )
    
    # Door horizontal lines
    for i in range(16):
        line_y = door_y + 3 + i * 5
        if line_y < door_y + door_h - 2:
            canvas.create_rectangle(
                door_x + 2, line_y,
                door_x + door_w - 2, line_y + 2,
                fill="#9a9ea4", outline=""
            )
    
    # === LOWER PROTRUDING SECTION ===
    lower_section_y = vab_y + 95
    lower_section_h = 45
    lower_section_x = center_x - 8
    lower_section_w = center_width + 16
    
    # Main protruding box (white with border)
    canvas.create_rectangle(
        lower_section_x, lower_section_y,
        lower_section_x + lower_section_w, lower_section_y + lower_section_h,
        fill="#f0ebe3", outline="#000000", width=2
    )
    
    # Door inside lower section
    lower_door_x = lower_section_x + 10
    lower_door_w = 28
    canvas.create_rectangle(
        lower_door_x, lower_section_y + 8,
        lower_door_x + lower_door_w, lower_section_y + lower_section_h - 3,
        fill="#e0e0e0", outline=""
    )
    
    # Lower door horizontal lines
    for i in range(6):
        line_y = lower_section_y + 10 + i * 5
        canvas.create_rectangle(
            lower_door_x + 2, line_y,
            lower_door_x + lower_door_w - 2, line_y + 2,
            fill="#9a9ea4", outline=""
        )
    
    # Gray side panels on lower section
    canvas.create_rectangle(
        lower_section_x + lower_section_w, lower_section_y + 5,
        lower_section_x + lower_section_w + 12, lower_section_y + lower_section_h,
        fill="#7a7e84", outline=""
    )
    
    # === AMERICAN FLAG (HORIZONTAL) ===
    flag_x = vab_x + 12
    flag_y = vab_y + 28
    flag_w = 50  # Wider
    flag_h = 70  # Taller
    
    # Horizontal stripes - 13 total (7 red, 6 white)
    stripe_h = flag_h / 13
    for i in range(13):
        if i % 2 == 0:  # Red stripes
            canvas.create_rectangle(
                flag_x, flag_y + i * stripe_h,
                flag_x + flag_w, flag_y + (i + 1) * stripe_h,
                fill="#b22234", outline=""
            )
        else:  # White stripes
            canvas.create_rectangle(
                flag_x, flag_y + i * stripe_h,
                flag_x + flag_w, flag_y + (i + 1) * stripe_h,
                fill="#ffffff", outline=""
            )
    
    # Blue canton - top left, covers first 7 stripes
    canton_h = flag_h * (7/13)
    canton_w = flag_w * 0.4
    canvas.create_rectangle(
        flag_x, flag_y,
        flag_x + canton_w, flag_y + canton_h,
        fill="#3c3b6e", outline=""
    )
    
    # Plus stars (6 rows x 5 cols)
    for row in range(6):
        for col in range(5):
            star_x = flag_x + 2 + col * 3.5
            star_y = flag_y + 2 + row * 4.5
            # Vertical bar
            canvas.create_rectangle(
                star_x + 0.5, star_y,
                star_x + 1.5, star_y + 3,
                fill="#ffffff", outline=""
            )
            # Horizontal bar
            canvas.create_rectangle(
                star_x, star_y + 1,
                star_x + 2, star_y + 2,
                fill="#ffffff", outline=""
            )
    
    # === NASA LOGO ===
    nasa_x = vab_x + 100
    nasa_y = vab_y + 42
    logo_size = 55
    
    # Blue circle
    canvas.create_oval(
        nasa_x, nasa_y,
        nasa_x + logo_size, nasa_y + logo_size,
        fill="#1f4ea8", outline=""
    )
    
    # White "NASA" text - larger
    canvas.create_text(
        nasa_x + logo_size / 2, nasa_y + logo_size / 2 - 4,
        text="NASA",
        fill="#ffffff",
        font=("Arial", 13, "bold"),
        anchor="center"
    )
    
    # White orbital ring
    canvas.create_arc(
        nasa_x + 5, nasa_y + 10,
        nasa_x + logo_size - 5, nasa_y + logo_size - 10,
        start=200, extent=160,
        outline="#ffffff", width=3, style="arc"
    )
    
    # Red chevron - more prominent
    cx = nasa_x + logo_size / 2
    cy = nasa_y + logo_size / 2
    canvas.create_polygon(
        cx - 11, cy + 6,
        cx - 3, cy - 10,
        cx + 11, cy + 6,
        cx + 3, cy + 15,
        fill="#d83b3b", outline=""
    )
    
    # White stars on logo - more visible
    star_positions = [
        (12, 16), (logo_size - 16, logo_size - 20),
        (20, logo_size - 12), (logo_size - 12, 18),
        (logo_size / 2 - 4, 8), (logo_size / 2 + 4, logo_size - 8)
    ]
    for star_pos in star_positions:
        canvas.create_oval(
            nasa_x + star_pos[0], nasa_y + star_pos[1],
            nasa_x + star_pos[0] + 3, nasa_y + star_pos[1] + 3,
            fill="#ffffff", outline=""
        )
    
    # === LOWER SECTION DETAILS ===
    
    # Three tall doors at bottom - better proportioned
    door_bottom_y = vab_y + main_height
    door_height = 38
    door_width = 14
    door_spacing = 16
    
    # Left door
    canvas.create_rectangle(
        vab_x + 8, door_bottom_y - door_height,
        vab_x + 8 + door_width, door_bottom_y,
        fill="#3a4a54", outline="#2a3a44", width=2
    )
    
    # Center door (darker)
    canvas.create_rectangle(
        center_x - 1, door_bottom_y - door_height,
        center_x - 1 + door_width, door_bottom_y,
        fill="#2a3a44", outline="#1a2a34", width=2
    )
    
    # Right door
    canvas.create_rectangle(
        center_x + 28, door_bottom_y - door_height,
        center_x + 28 + door_width, door_bottom_y,
        fill="#3a4a54", outline="#2a3a44", width=2
    )
    
    # Small blue windows bottom left
    window_y = vab_y + main_height - 8
    for i in range(3):
        canvas.create_rectangle(
            vab_x + 10 + i * 14, window_y,
            vab_x + 16 + i * 14, window_y + 6,
            fill="#4a6a8a", outline="#3a5a7a"
        )
    
    # Small blue windows bottom right
    for i in range(4):
        canvas.create_rectangle(
            vab_x + 108 + i * 8, window_y,
            vab_x + 114 + i * 8, window_y + 6,
            fill="#4a6a8a", outline="#3a5a7a"
        )
def draw_secondary_building(canvas):
    """Draw the Launch Control Center building (left building in reference)."""
    # Position to right of VAB
    lcc_x = 320
    lcc_y = 265
    lcc_width = 50
    lcc_height = 85
    
    # Main building body - cream/tan color
    canvas.create_rectangle(lcc_x, lcc_y, lcc_x+lcc_width, lcc_y+lcc_height, 
                           fill='#e8dcc8', outline='')
    
    # Top dark section with NASA logo - dark gray
    top_height = 28
    canvas.create_rectangle(lcc_x, lcc_y, lcc_x+lcc_width, lcc_y+top_height, 
                           fill='#5a5a5a', outline='')
    
    # NASA meatball logo in top section - centered
    logo_x = lcc_x + lcc_width/2 - 12
    logo_y = lcc_y + 6
    logo_size = 24
    
    # Blue circle
    canvas.create_oval(logo_x, logo_y, logo_x+logo_size, logo_y+logo_size, 
                      fill='#1e3a8a', outline='')
    
    # Red chevron
    center_x = logo_x + logo_size/2
    center_y = logo_y + logo_size/2
    canvas.create_polygon(
        center_x-5, center_y,
        center_x, center_y-5,
        center_x+5, center_y,
        center_x, center_y+5,
        fill='#dc2626', outline=''
    )
    
    # White orbital arc
    canvas.create_arc(logo_x+2, logo_y+4, logo_x+logo_size-2, logo_y+logo_size-4, 
                     start=200, extent=140, outline='#ffffff', width=2, style='arc')
    
    # White stars on logo
    canvas.create_oval(logo_x+4, logo_y+7, logo_x+7, logo_y+10, fill='#ffffff', outline='')
    canvas.create_oval(logo_x+logo_size-7, logo_y+logo_size-10, logo_x+logo_size-4, logo_y+logo_size-7, 
                      fill='#ffffff', outline='')
    
    # Upper section windows - two rows of blue windows
    window_start_y = lcc_y + top_height + 5
    for row in range(2):
        for col in range(4):
            win_x = lcc_x + 6 + col*11
            win_y = window_start_y + row*8
            canvas.create_rectangle(win_x, win_y, win_x+7, win_y+6, 
                                   fill='#4a6a8a', outline='#3a5a7a')
    
    # Middle section - multiple rows of blue windows
    middle_start_y = lcc_y + top_height + 25
    for row in range(3):
        for col in range(4):
            win_x = lcc_x + 6 + col*11
            win_y = middle_start_y + row*12
            canvas.create_rectangle(win_x, win_y, win_x+7, win_y+8, 
                                   fill='#4a6a8a', outline='#3a5a7a')
    
    # Bottom white/light section
    bottom_y = lcc_y + lcc_height - 12
    canvas.create_rectangle(lcc_x, bottom_y, lcc_x+lcc_width, lcc_y+lcc_height, 
                           fill='#d8d8d8', outline='')
    
    # Bottom blue windows - single row
    for i in range(6):
        canvas.create_rectangle(lcc_x + 4 + i*7, bottom_y+3, 
                               lcc_x + 8 + i*7, bottom_y+8, 
                               fill='#4a6a8a', outline='#3a5a7a')
    
    # Dark right side panel for 3D depth
    canvas.create_rectangle(lcc_x+lcc_width, lcc_y+5, lcc_x+lcc_width+12, lcc_y+lcc_height, 
                           fill='#5a5a5a', outline='')
    
    # Darker far right edge
    canvas.create_rectangle(lcc_x+lcc_width+12, lcc_y+8, lcc_x+lcc_width+18, lcc_y+lcc_height, 
                           fill='#3a3a3a', outline='')


def draw_operations_building(canvas):
    """Draw the OPF (Orbiter Processing Facility) building (right building in reference)."""
    # Position closer to the secondary building
    opf_x = 400
    opf_y = 260
    opf_width = 100
    opf_height = 90
    
    # Main building body - cream/tan
    canvas.create_rectangle(opf_x, opf_y, opf_x+opf_width, opf_y+opf_height, 
                           fill='#e8dcc8', outline='')
    
    # Stepped/curved roofline - multiple dark sections at different heights
    roof_sections = [
        (opf_x+8, 5, 18),
        (opf_x+28, 7, 18),
        (opf_x+48, 6, 18),
        (opf_x+68, 4, 15),
    ]
    
    for x_pos, height, width in roof_sections:
        canvas.create_rectangle(x_pos, opf_y-height, x_pos+width, opf_y, 
                               fill='#4a4a4a', outline='')
    
    # Top section with OPF text and NASA logo
    top_section_height = 35
    
    # "OPF" text - blue letters
    canvas.create_text(opf_x + 20, opf_y + 18, 
                      text="O P F", fill='#2a4a8a', 
                      font=('Courier', 11, 'bold'), anchor='w')
    
    # NASA logo - top right
    logo_x = opf_x + opf_width - 32
    logo_y = opf_y + 10
    logo_size = 24
    
    # Blue circle
    canvas.create_oval(logo_x, logo_y, logo_x+logo_size, logo_y+logo_size, 
                      fill='#1e3a8a', outline='')
    
    # Red chevron
    center_x = logo_x + logo_size/2
    center_y = logo_y + logo_size/2
    canvas.create_polygon(
        center_x-5, center_y,
        center_x, center_y-5,
        center_x+5, center_y,
        center_x, center_y+5,
        fill='#dc2626', outline=''
    )
    
    # White orbital arc
    canvas.create_arc(logo_x+2, logo_y+4, logo_x+logo_size-2, logo_y+logo_size-4, 
                     start=200, extent=140, outline='#ffffff', width=2, style='arc')
    
    # White stars on logo
    canvas.create_oval(logo_x+4, logo_y+7, logo_x+7, logo_y+10, fill='#ffffff', outline='')
    canvas.create_oval(logo_x+logo_size-7, logo_y+logo_size-10, logo_x+logo_size-4, logo_y+logo_size-7, 
                      fill='#ffffff', outline='')
    
    # Small windows on upper right
    for i in range(3):
        canvas.create_rectangle(opf_x + opf_width - 15, opf_y + 12 + i*7, 
                               opf_x + opf_width - 9, opf_y + 17 + i*7, 
                               fill='#4a6a8a', outline='#3a5a7a')
    
    # Large door/bay opening - very dark blue
    door_x = opf_x + 25
    door_y = opf_y + 50
    door_width = 50
    
    canvas.create_rectangle(door_x, door_y, door_x+door_width, opf_y+opf_height, 
                           fill='#1a3a5a', outline='')
    
    # Door inner darker section
    canvas.create_rectangle(door_x+6, door_y+6, door_x+door_width-6, opf_y+opf_height-12, 
                           fill='#0a2a4a', outline='')
    
    # Door frame - very dark
    canvas.create_rectangle(door_x-3, door_y, door_x, opf_y+opf_height, 
                           fill='#2a2a2a', outline='')
    canvas.create_rectangle(door_x+door_width, door_y, door_x+door_width+3, opf_y+opf_height, 
                           fill='#2a2a2a', outline='')
    
    # Small windows on left side of door
    for i in range(2):
        canvas.create_rectangle(opf_x + 10, opf_y + 55 + i*13, 
                               opf_x + 18, opf_y + 63 + i*13, 
                               fill='#4a6a8a', outline='#3a5a7a')
    
    # Small windows on right side of door
    for i in range(2):
        canvas.create_rectangle(opf_x + opf_width - 18, opf_y + 55 + i*13, 
                               opf_x + opf_width - 10, opf_y + 63 + i*13, 
                               fill='#4a6a8a', outline='#3a5a7a')
    
    # Bottom white section
    bottom_y = opf_y + opf_height - 12
    canvas.create_rectangle(opf_x, bottom_y, opf_x+opf_width, opf_y+opf_height, 
                           fill='#d8d8d8', outline='')
    
    # Bottom windows
    for i in range(10):
        canvas.create_rectangle(opf_x + 5 + i*9, bottom_y + 3, 
                               opf_x + 10 + i*9, bottom_y + 8, 
                               fill='#4a6a8a', outline='#3a5a7a')
    
    # Dark right side for depth
    canvas.create_rectangle(opf_x+opf_width, opf_y+8, opf_x+opf_width+15, opf_y+opf_height, 
                           fill='#4a4a4a', outline='')
def draw_launch_tower(canvas):
    """Draw the launch tower structure based on Saturn V Mobile Launcher."""
    # Mobile Launcher Platform positioning
    platform_x = 550
    platform_y = 340
    platform_width = 140
    platform_height = 12
    
    # Tower is slightly taller than rocket
    tower_x = platform_x + 85  # Position tower to right, next to where rocket will be
    tower_top_y = 140  # Shorter tower, just taller than rocket
    tower_base_y = platform_y
    tower_height = tower_base_y - tower_top_y
    
    # Main platform deck - DRAW FIRST
    canvas.create_rectangle(platform_x, platform_y, platform_x+platform_width, platform_y+platform_height, fill='#6a6a6a', outline='#4a4a4a', width=2)
    
    # Platform support structure underneath
    canvas.create_rectangle(platform_x+10, platform_y+platform_height, platform_x+platform_width-10, platform_y+platform_height+18, fill='#5a5a5a', outline='')
    # Support pillars
    for i in range(6):
        pillar_x = platform_x + 15 + i*20
        canvas.create_rectangle(pillar_x, platform_y+platform_height, pillar_x+4, platform_y+platform_height+18, fill='#4a4a4a', outline='')
    
    # Exhaust flame trench below
    trench_y = platform_y + platform_height + 18
    canvas.create_rectangle(platform_x+15, trench_y, platform_x+platform_width-15, trench_y+12, fill='#2a2a2a', outline='')
    canvas.create_rectangle(platform_x+15, trench_y, platform_x+20, trench_y+12, fill='#6a5a4a', outline='')
    canvas.create_rectangle(platform_x+platform_width-20, trench_y, platform_x+platform_width-15, trench_y+12, fill='#6a5a4a', outline='')
    
    # TALL RED TOWER - lattice structure (4 vertical legs)
    tower_width = 45
    leg_width = 6
    
    # Four corner legs of the tower
    canvas.create_rectangle(tower_x, tower_top_y, tower_x+leg_width, tower_base_y, fill='#c84040', outline='')
    canvas.create_rectangle(tower_x+tower_width-leg_width, tower_top_y, tower_x+tower_width, tower_base_y, fill='#c84040', outline='')
    
    # Interior vertical supports (for lattice look)
    canvas.create_rectangle(tower_x+15, tower_top_y, tower_x+17, tower_base_y, fill='#a83838', outline='')
    canvas.create_rectangle(tower_x+28, tower_top_y, tower_x+30, tower_base_y, fill='#a83838', outline='')
    
    # Horizontal cross beams at regular intervals
    num_beams = int(tower_height / 15)
    for i in range(num_beams):
        beam_y = tower_top_y + 10 + i*15
        if beam_y < tower_base_y:
            canvas.create_rectangle(tower_x, beam_y, tower_x+tower_width, beam_y+3, fill='#a83838', outline='')
    
    # Diagonal cross-bracing (X pattern) - creates lattice look
    num_braces = int(tower_height / 20)
    for i in range(num_braces):
        brace_y = tower_top_y + 15 + i*20
        if brace_y < tower_base_y - 20:
            # Left side X-bracing
            canvas.create_line(tower_x+3, brace_y, tower_x+18, brace_y+15, fill='#983030', width=1)
            canvas.create_line(tower_x+18, brace_y, tower_x+3, brace_y+15, fill='#983030', width=1)
            # Right side X-bracing
            canvas.create_line(tower_x+27, brace_y, tower_x+42, brace_y+15, fill='#983030', width=1)
            canvas.create_line(tower_x+42, brace_y, tower_x+27, brace_y+15, fill='#983030', width=1)
    
    # SERVICE ARMS extending from tower to LEFT (toward rocket) - ONLY 2 ARMS
    # Arms should reach to where rocket will be (pad_x = 620)
    rocket_x = 620  # Where the rocket center will be
    
    arm_configs = [
        (tower_top_y + 120, rocket_x - tower_x + 8),  # Lower arm reaches to rocket
        (tower_top_y + 70, rocket_x - tower_x + 8),   # Upper arm reaches to rocket
    ]
    
    for arm_y, arm_length in arm_configs:
        if arm_y < tower_base_y:
            # Main arm beam extending left from tower to rocket
            canvas.create_rectangle(tower_x-arm_length, arm_y, tower_x, arm_y+3, fill='#d85050', outline='')
            # Support truss under arm
            canvas.create_line(tower_x-arm_length, arm_y+3, tower_x-arm_length+8, arm_y+8, fill='#b84040', width=1)
            canvas.create_line(tower_x-5, arm_y+3, tower_x-13, arm_y+8, fill='#b84040', width=1)
            # Umbilical connection plate at end (touching rocket)
            canvas.create_rectangle(tower_x-arm_length-4, arm_y-1, tower_x-arm_length, arm_y+5, fill='#808080', outline='')
            # Connection line to rocket body
            canvas.create_rectangle(tower_x-arm_length-5, arm_y+1, tower_x-arm_length-4, arm_y+2, fill='#505050', outline='')
    
    # Hammerhead crane at very top
    crane_y = tower_top_y
    # Vertical crane mast
    canvas.create_rectangle(tower_x+18, crane_y-20, tower_x+27, crane_y+5, fill='#d84040', outline='')
    # Horizontal crane boom
    canvas.create_rectangle(tower_x-15, crane_y-20, tower_x+60, crane_y-16, fill='#d84040', outline='')
    # Crane counterweight
    canvas.create_rectangle(tower_x-15, crane_y-16, tower_x-2, crane_y-10, fill='#a03030', outline='')
    # Hook
    canvas.create_rectangle(tower_x+45, crane_y-16, tower_x+47, crane_y-8, fill='#808080', outline='')
    
    # Lightning rod at very top
    canvas.create_rectangle(tower_x+21, crane_y-30, tower_x+24, crane_y-20, fill='#909090', outline='')
    canvas.create_oval(tower_x+19, crane_y-33, tower_x+26, crane_y-30, fill='#ff0000', outline='')
    
    # Warning lights on tower
    light_heights = [tower_top_y+40, tower_top_y+100, tower_top_y+160]
    for light_y in light_heights:
        if light_y < tower_base_y:
            canvas.create_oval(tower_x-2, light_y, tower_x+2, light_y+4, fill='#ff4444', outline='')
            canvas.create_oval(tower_x+tower_width-2, light_y, tower_x+tower_width+2, light_y+4, fill='#ff4444', outline='')


def draw_pond_with_gator(canvas, gator_visible=False, gator_animation_phase=0):
    """Draw a small pond with occasional alligator.
    
    Args:
        canvas: The canvas to draw on
        gator_visible: Whether gator should be visible at all
        gator_animation_phase: 0-1 float for animation (0=submerged, 1=fully surfaced)
    """
    pond_x = 720
    pond_y = 370
    
    # Pond water - dark blue/green
    canvas.create_oval(pond_x, pond_y, pond_x+60, pond_y+25, fill='#2a5a4a', outline='#1a4a3a', width=2, tags='pond')
    
    # Water ripples/details
    canvas.create_arc(pond_x+10, pond_y+8, pond_x+25, pond_y+18, start=0, extent=180, outline='#3a6a5a', width=1, tags='pond', style='arc')
    canvas.create_arc(pond_x+35, pond_y+10, pond_x+50, pond_y+20, start=0, extent=180, outline='#3a6a5a', width=1, tags='pond', style='arc')
    
    # Lily pad
    canvas.create_oval(pond_x+15, pond_y+5, pond_x+22, pond_y+10, fill='#4a7a3a', outline='#3a6a2a', tags='pond')
    
    # Alligator (only if visible)
    if gator_visible and gator_animation_phase > 0:
        gator_x = pond_x + 35
        gator_y = pond_y + 12
        
        # Calculate vertical offset based on animation phase
        # Phase 0 = +8 pixels down (submerged), Phase 1 = 0 pixels (surfaced)
        submerge_offset = int(8 * (1 - gator_animation_phase))
        
        # Calculate opacity/visibility for parts based on phase
        # Eyes and nostrils appear first (phase > 0.3), then full head (phase > 0.5)
        show_eyes = gator_animation_phase > 0.3
        show_full_head = gator_animation_phase > 0.5
        show_ridges = gator_animation_phase > 0.2
        
        # Back ridges poking out of water (appear first as gator surfaces)
        if show_ridges:
            ridge_offset = int(submerge_offset * 0.5)  # Ridges surface faster
            canvas.create_oval(gator_x-12, gator_y+3+ridge_offset, gator_x-8, gator_y+6+ridge_offset, 
                             fill='#3a5a3a', outline='#2a4a2a', tags='gator')
            canvas.create_oval(gator_x-18, gator_y+5+ridge_offset, gator_x-14, gator_y+8+ridge_offset, 
                             fill='#3a5a3a', outline='#2a4a2a', tags='gator')
        
        # Gator head (dark green) - appears gradually
        if show_full_head:
            canvas.create_oval(gator_x-8, gator_y-3+submerge_offset, gator_x+8, gator_y+5+submerge_offset, 
                             fill='#3a5a3a', outline='#2a4a2a', tags='gator')
            
            # Snout
            canvas.create_oval(gator_x+5, gator_y+submerge_offset, gator_x+10, gator_y+3+submerge_offset, 
                             fill='#4a6a4a', outline='#2a4a2a', tags='gator')
        
        # Eyes and nostrils (appear early in animation)
        if show_eyes:
            eye_offset = int(submerge_offset * 0.7)  # Eyes surface a bit faster
            
            # Eyes (yellow/orange)
            canvas.create_oval(gator_x-4, gator_y-2+eye_offset, gator_x-1, gator_y+1+eye_offset, 
                             fill='#ffa500', outline='#000000', tags='gator')
            canvas.create_oval(gator_x+1, gator_y-2+eye_offset, gator_x+4, gator_y+1+eye_offset, 
                             fill='#ffa500', outline='#000000', tags='gator')
            
            # Pupils
            canvas.create_oval(gator_x-3, gator_y-1+eye_offset, gator_x-2, gator_y+eye_offset, 
                             fill='#000000', outline='', tags='gator')
            canvas.create_oval(gator_x+2, gator_y-1+eye_offset, gator_x+3, gator_y+eye_offset, 
                             fill='#000000', outline='', tags='gator')
            
            # Nostrils (appear with eyes)
            if show_full_head:
                canvas.create_oval(gator_x+7, gator_y+1+eye_offset, gator_x+8, gator_y+2+eye_offset, 
                                 fill='#1a1a1a', outline='', tags='gator')
        
        # Extra ripples when gator is moving
        if 0.1 < gator_animation_phase < 0.9:
            # Animated ripples around the gator
            canvas.create_arc(gator_x-15, gator_y+submerge_offset, gator_x+15, gator_y+15+submerge_offset, 
                            start=0, extent=180, outline='#4a7a6a', width=2, tags='gator', style='arc')


def draw_spotlights(canvas, vehicle_name=None):
    """Draw spotlights on the ground - always visible, but only lit at night."""
    from datetime import datetime
    
    hour = datetime.now().hour
    # Check if it's nighttime (6pm-6am)
    is_night = hour >= 18 or hour < 6
    
    rocket_x = 620
    rocket_base_y = 340
    rocket_mid_y = rocket_base_y - 90
    ground_y = 385
    
    # Check if rocket is dark (Electron) to make lights brighter when on
    is_dark_rocket = vehicle_name and 'electron' in vehicle_name.lower()
    
    # Left spotlight structure (always visible)
    spotlight_left_x = rocket_x - 80
    # Spotlight housing
    canvas.create_rectangle(spotlight_left_x, ground_y, spotlight_left_x+12, ground_y+8, fill='#505050', outline='', tags='spotlight')
    canvas.create_rectangle(spotlight_left_x+2, ground_y+8, spotlight_left_x+10, ground_y+12, fill='#404040', outline='', tags='spotlight')
    # Spotlight lens/front
    canvas.create_rectangle(spotlight_left_x+3, ground_y+1, spotlight_left_x+9, ground_y+7, fill='#2a2a2a', outline='', tags='spotlight')
    
    # Right spotlight structure (always visible)
    spotlight_right_x = rocket_x + 68
    # Spotlight housing
    canvas.create_rectangle(spotlight_right_x, ground_y, spotlight_right_x+12, ground_y+8, fill='#505050', outline='', tags='spotlight')
    canvas.create_rectangle(spotlight_right_x+2, ground_y+8, spotlight_right_x+10, ground_y+12, fill='#404040', outline='', tags='spotlight')
    # Spotlight lens/front
    canvas.create_rectangle(spotlight_right_x+3, ground_y+1, spotlight_right_x+9, ground_y+7, fill='#2a2a2a', outline='', tags='spotlight')
    
    # Only draw light beams at night
    if is_night:
        # Adjust light colors based on rocket type
        if is_dark_rocket:
            beam_color = '#ffffee'  # Much brighter yellow/white for dark rockets
            beam_outline = '#ffffaa'  # Bright yellow outline
            outline_width = 3  # Thicker outline
        else:
            beam_color = '#ffffaa'
            beam_outline = '#ffff66'
            outline_width = 2
        
        # Left light beam
        canvas.create_polygon(
            spotlight_left_x+6, ground_y,
            rocket_x-18, rocket_mid_y,
            rocket_x-8, rocket_mid_y,
            spotlight_left_x+8, ground_y,
            fill=beam_color, outline=beam_outline, width=outline_width, tags='spotlight'
        )
        
        # Right light beam
        canvas.create_polygon(
            spotlight_right_x+6, ground_y,
            rocket_x+8, rocket_mid_y,
            rocket_x+18, rocket_mid_y,
            spotlight_right_x+8, ground_y,
            fill=beam_color, outline=beam_outline, width=outline_width, tags='spotlight'
        )
        
        # Bright lens when lights are on
        canvas.create_rectangle(spotlight_left_x+3, ground_y+1, spotlight_left_x+9, ground_y+7, fill='#ffffcc', outline='', tags='spotlight')
        canvas.create_rectangle(spotlight_right_x+3, ground_y+1, spotlight_right_x+9, ground_y+7, fill='#ffffcc', outline='', tags='spotlight')

def draw_launch_pad(canvas):
    """This function is now integrated into draw_launch_tower - kept for compatibility."""
    pass


def draw_flat_cloud(canvas, x, y, cloud_color='#ffffff'):
    """Draw a flat pixel cloud and return cloud IDs."""
    cloud_ids = []
    cloud_ids.append(canvas.create_oval(x, y+5, x+25, y+20, fill=cloud_color, outline='', tags='cloud'))
    cloud_ids.append(canvas.create_oval(x+15, y, x+40, y+18, fill=cloud_color, outline='', tags='cloud'))
    cloud_ids.append(canvas.create_oval(x+30, y+5, x+55, y+20, fill=cloud_color, outline='', tags='cloud'))
    return cloud_ids


def draw_bird(canvas, x, y, flap_up=True, bird_color='#2a2a2a'):
    """Draw a simple pixel bird with wing animation and return IDs."""
    bird_ids = []
    if flap_up:
        # Wings up position
        bird_ids.append(canvas.create_line(x, y, x+4, y-4, fill=bird_color, width=2, tags='bird'))
        bird_ids.append(canvas.create_line(x+4, y-4, x+8, y, fill=bird_color, width=2, tags='bird'))
    else:
        # Wings down position
        bird_ids.append(canvas.create_line(x, y, x+4, y-1, fill=bird_color, width=2, tags='bird'))
        bird_ids.append(canvas.create_line(x+4, y-1, x+8, y, fill=bird_color, width=2, tags='bird'))
    # Body dot
    bird_ids.append(canvas.create_oval(x+3, y-1, x+5, y+1, fill=bird_color, outline='', tags='bird'))
    return bird_ids


def draw_car(canvas, x, y, car_color='#3a7bc8'):
    """Draw a simple pixel car and return IDs."""
    car_ids = []
    # Car body
    car_ids.append(canvas.create_rectangle(x, y, x+12, y+6, fill=car_color, outline='', tags='car'))
    # Car top/cabin
    car_ids.append(canvas.create_rectangle(x+2, y-3, x+10, y, fill=car_color, outline='', tags='car'))
    # Windows
    car_ids.append(canvas.create_rectangle(x+3, y-2, x+5, y, fill='#add8e6', outline='', tags='car'))
    car_ids.append(canvas.create_rectangle(x+7, y-2, x+9, y, fill='#add8e6', outline='', tags='car'))
    # Wheels
    car_ids.append(canvas.create_oval(x+1, y+5, x+4, y+8, fill='#1a1a1a', outline='', tags='car'))
    car_ids.append(canvas.create_oval(x+8, y+5, x+11, y+8, fill='#1a1a1a', outline='', tags='car'))
    return car_ids


def draw_background(canvas):
    """Draw the complete Kennedy Space Center background."""
    colors = get_sky_colors()
    
    # Sky - changes based on time of day
    canvas.create_rectangle(0, 0, 800, 350, fill=colors['sky'], outline='')
    
    # Add stars if nighttime
    hour = datetime.now().hour
    if hour >= 18 or hour < 6:
        draw_stars(canvas)
    
    # Ocean - teal/turquoise
    canvas.create_rectangle(0, 350, 800, 600, fill=colors['ocean'], outline='')
    
    # Horizon line - darker teal
    canvas.create_rectangle(0, 350, 800, 365, fill=colors['horizon'], outline='')
    
    # Grassy ground area
    canvas.create_rectangle(0, 365, 800, 390, fill='#5a8c3a', outline='')
    
    # Add pixel grass details
    draw_pixel_grass(canvas)
    
    # Draw all buildings and structures
    draw_vab_building(canvas)
    draw_secondary_building(canvas)
    draw_operations_building(canvas)
    draw_launch_tower(canvas)
    draw_launch_pad(canvas)
    
    # Draw pond (gator will be animated separately)
    draw_pond_with_gator(canvas, gator_visible=False)
    
    # Draw clouds
    cloud1 = draw_flat_cloud(canvas, 150, 60, colors['cloud'])
    cloud2 = draw_flat_cloud(canvas, 420, 90, colors['cloud'])
    cloud3 = draw_flat_cloud(canvas, 650, 50, colors['cloud'])
    
    return [cloud1, cloud2, cloud3]