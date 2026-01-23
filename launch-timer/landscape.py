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
    grass_colors = ['#4a7c2a', '#6a9c4a', '#5a8c3a', '#3a6c1a']
    
    # Draw grass blades throughout the grassy area
    for i in range(400):  # Increased from 100 to 400 for better coverage
        x = random.randint(0, 800)
        y = random.randint(368, 495)  # Cover the whole grass area
        color = random.choice(grass_colors)
        
        # Mix of different grass styles
        style = random.randint(1, 4)
        if style == 1:
            # Single vertical blade
            canvas.create_line(x, y, x, y-3, fill=color, width=1)
        elif style == 2:
            # Small tuft
            canvas.create_rectangle(x, y, x+2, y+3, fill=color, outline='')
        elif style == 3:
            # Tiny dot
            canvas.create_rectangle(x, y, x+1, y+1, fill=color, outline='')
        else:
            # Angled blade
            canvas.create_line(x, y, x+1, y-3, fill=color, width=1)


def draw_roads(canvas):
    """Draw simple road system."""
    road_color = '#3a3a3a'
    line_color = '#6a6a3a'
    
    # Main horizontal road
    road_y = 420
    road_height = 18
    
    # Road surface
    canvas.create_rectangle(
        0, road_y, 800, road_y + road_height,
        fill=road_color, outline='', tags='road'
    )
    
    # Road edges
    canvas.create_rectangle(
        0, road_y, 800, road_y + 2,
        fill='#5a5a5a', outline='', tags='road'
    )
    canvas.create_rectangle(
        0, road_y + road_height - 2, 800, road_y + road_height,
        fill='#5a5a5a', outline='', tags='road'
    )
    
    # Center dashed yellow line
    for x in range(0, 800, 20):
        canvas.create_rectangle(
            x, road_y + road_height // 2 - 1,
            x + 10, road_y + road_height // 2 + 1,
            fill=line_color, outline='', tags='road'
        )


def draw_back_fence(canvas):
    """Draw the top fence that goes behind the launch pad."""
    fence_color = '#8a8a8a'
    post_color = '#6a6a6a'
    
    fence_left = 520  # Updated to match new left fence position
    fence_right = 730
    fence_top = 347
    
    # Top fence (Horizontal) - drawn behind launch pad
    for x in range(fence_left, fence_right, 20):
        # Fence post
        canvas.create_rectangle(
            x, fence_top, x + 3, fence_top + 18,
            fill=post_color, outline='', tags='fence_back'
        )
        # Horizontal rails connecting posts
        if x + 20 < fence_right:
            canvas.create_rectangle(
                x + 3, fence_top + 4, x + 20, fence_top + 6,
                fill=fence_color, outline='', tags='fence_back'
            )
            canvas.create_rectangle(
                x + 3, fence_top + 12, x + 20, fence_top + 14,
                fill=fence_color, outline='', tags='fence_back'
            )


def draw_security_fence_and_shack(canvas):
    """Draw security fence surrounding launch pad (left, right, bottom sides) and guard shack."""
    fence_color = '#8a8a8a'
    post_color = '#6a6a6a'
    
    # Define launch pad security perimeter
    fence_left = 520
    fence_right = 720
    fence_top = 340
    fence_bottom = 440  # Not on road (road is at 420)
    
    # === LEFT SIDE FENCE (Vertical) ===
    for y in range(fence_top, fence_bottom+10, 20):
        # Fence post
        canvas.create_rectangle(
            fence_left, y, fence_left + 3, y + 18,
            fill=post_color, outline='', tags='fence'
        )
        # Horizontal rails
        canvas.create_rectangle(
            fence_left, y + 4, fence_left + 3, y + 6,
            fill=fence_color, outline='', tags='fence'
        )
        canvas.create_rectangle(
            fence_left, y + 6, fence_left + 3, y + 14,
            fill=fence_color, outline='', tags='fence'
        )
    
    # === RIGHT SIDE FENCE (Vertical) ===
    for y in range(fence_top, fence_bottom, 20):
        # Fence post
        canvas.create_rectangle(
            fence_right, y, fence_right + 3, y + 18,
            fill=post_color, outline='', tags='fence'
        )
        # Horizontal rails
        canvas.create_rectangle(
            fence_right, y + 4, fence_right + 3, y + 6,
            fill=fence_color, outline='', tags='fence'
        )
        canvas.create_rectangle(
            fence_right, y + 12, fence_right + 3, y + 14,
            fill=fence_color, outline='', tags='fence'
        )
    
    # === BOTTOM FENCE (Horizontal) ===
    for x in range(fence_left, fence_right+20, 20):
        # Fence post
        canvas.create_rectangle(
            x, fence_bottom, x + 3, fence_bottom + 18,
            fill=post_color, outline='', tags='fence'
        )
        # Horizontal rails connecting posts
        if x + 30 < fence_right:
            canvas.create_rectangle(
                x + 5, fence_bottom + 4, x + 40, fence_bottom + 6,
                fill=fence_color, outline='', tags='fence'
            )
            canvas.create_rectangle(
                x + 3, fence_bottom + 12, x + 40, fence_bottom + 14,
                fill=fence_color, outline='', tags='fence'
            )
    
    # === GUARD SHACK closer to road ===
    shack_x = 490
    shack_y = 395  # Much closer to road (road is at 420)
    shack_w = 20
    shack_h = 25
    
    # Shack body
    canvas.create_rectangle(
        shack_x, shack_y, shack_x + shack_w, shack_y + shack_h,
        fill='#d8d8d8', outline='#3a3a3a', width=2, tags='fence'
    )
    
    # Shack roof
    canvas.create_polygon(
        shack_x - 2, shack_y,
        shack_x + shack_w // 2, shack_y - 8,
        shack_x + shack_w + 2, shack_y,
        fill='#8a4a4a', outline='#3a3a3a', tags='fence'
    )
    
    # Window
    canvas.create_rectangle(
        shack_x + 4, shack_y + 5, shack_x + 10, shack_y + 12,
        fill='#5a7a9a', outline='#3a3a3a', tags='fence'
    )
    
    # Door
    canvas.create_rectangle(
        shack_x + 12, shack_y + 10, shack_x + 18, shack_y + shack_h,
        fill='#5a4a3a', outline='#3a3a3a', tags='fence'
    )

def draw_vab_building(canvas):
    """Draw the Vehicle Assembly Building matching the reference image."""
    vab_x = 60
    vab_y = 215
    main_width = 140
    main_height = 150
    
    # === BACKGROUND/DEPTH ELEMENTS (right side stepped panels) ===
    # Far right dark gray stepped panels for 3D depth effect
    canvas.create_rectangle(
        vab_x + main_width, vab_y + 10,
        vab_x + main_width + 25, vab_y + main_height,
        fill="#5a5e64", outline=""
    )
    canvas.create_rectangle(
        vab_x + main_width + 25, vab_y + 20,
        vab_x + main_width + 40, vab_y + main_height,
        fill="#4a4a4a", outline=""
    )
    
    # === MAIN BUILDING BODY (cream/beige color) ===
    canvas.create_rectangle(
        vab_x, vab_y,
        vab_x + main_width, vab_y + main_height,
        fill="#e8dfd0", outline="#000000", width=2
    )
    
    # === TOP ROOF SECTION (dark gray) ===
    canvas.create_rectangle(
        vab_x, vab_y,
        vab_x + main_width, vab_y + 10,
        fill="#4a4e54", outline=""
    )
    
    # Roof equipment (small structures on top)
    canvas.create_rectangle(vab_x + 25, vab_y - 8, vab_x + 33, vab_y, 
                          fill="#3a3a3a", outline="#000000", width=1)
    canvas.create_rectangle(vab_x + 90, vab_y - 8, vab_x + 98, vab_y, 
                          fill="#3a3a3a", outline="#000000", width=1)
    
    # === CENTER DARK GRAY TOWER SECTION ===
    center_x = vab_x + 48
    center_width = 48
    tower_top = vab_y + 15
    
    # Tower body (no outline)
    canvas.create_rectangle(
        center_x, tower_top,
        center_x + center_width, vab_y + main_height,
        fill="#5a5e64", outline=""
    )
    
    # White outline - top only
    canvas.create_line(
        center_x, tower_top,
        center_x + center_width, tower_top,
        fill="#ffffff", width=2
    )
    
    # White outline - left side
    canvas.create_line(
        center_x, tower_top,
        center_x, vab_y + main_height,
        fill="#ffffff", width=2
    )
    
    # White outline - right side
    canvas.create_line(
        center_x + center_width, tower_top,
        center_x + center_width, vab_y + main_height,
        fill="#ffffff", width=2
    )
    
    # === MAIN DOOR INSIDE CENTER TOWER (extended to ground) ===
    door_x = center_x + 10
    door_y = tower_top + 20
    door_w = 28
    door_h = (vab_y + main_height) - door_y - 2  # Stop 2 pixels before bottom to account for building border
    
    # Door frame (black border)
    canvas.create_rectangle(
        door_x - 2, door_y - 2,
        door_x + door_w + 2, door_y + door_h + 2,
        fill="#000000", outline=""
    )
    
    # Door background (lighter gray)
    canvas.create_rectangle(
        door_x, door_y,
        door_x + door_w, door_y + door_h,
        fill="#b0b0b0", outline=""
    )
    
    # Door horizontal stripes (darker gray) - more stripes to fill the height
    stripe_count = int(door_h / 5.5)
    for i in range(stripe_count):
        stripe_y = door_y + 2 + i * 5.5
        if stripe_y < door_y + door_h - 2:
            canvas.create_rectangle(
                door_x + 2, stripe_y,
                door_x + door_w - 2, stripe_y + 2,
                fill="#707070", outline=""
            )
    
    # === AMERICAN FLAG (left side, vertical orientation) ===
    flag_x = vab_x + 10
    flag_y = vab_y + 30
    flag_w = 32  
    flag_h = 55
    
    # Vertical red stripes - 13 total (7 red, 6 white)
    stripe_w = flag_w / 13
    for i in range(13):
        if i % 2 == 0:  # Red stripes
            canvas.create_rectangle(
                flag_x + i * stripe_w, flag_y,
                flag_x + (i + 1) * stripe_w, flag_y + flag_h,
                fill="#b22234", outline=""
            )
        else:  # White stripes
            canvas.create_rectangle(
                flag_x + i * stripe_w, flag_y,
                flag_x + (i + 1) * stripe_w, flag_y + flag_h,
                fill="#ffffff", outline=""
            )
    
    # Blue canton - top left, covers first 7 stripes
    canton_w = flag_w * (7/13)
    canton_h = flag_h * 0.54
    canvas.create_rectangle(
        flag_x, flag_y,
        flag_x + canton_w, flag_y + canton_h,
        fill="#3c3b6e", outline=""
    )
    
    # Plus stars in canton (arranged in grid: 5 rows x 4 cols)
    star_rows = 5
    star_cols = 4
    star_spacing_x = canton_w / (star_cols + 1)
    star_spacing_y = canton_h / (star_rows + 1)
    
    for row in range(star_rows):
        for col in range(star_cols):
            star_x = flag_x + (col + 1) * star_spacing_x
            star_y = flag_y + (row + 1) * star_spacing_y
            # Vertical bar
            canvas.create_rectangle(
                star_x - 0.5, star_y - 1.5,
                star_x + 0.5, star_y + 1.5,
                fill="#ffffff", outline=""
            )
            # Horizontal bar
            canvas.create_rectangle(
                star_x - 1.5, star_y - 0.5,
                star_x + 1.5, star_y + 0.5,
                fill="#ffffff", outline=""
            )


def draw_secondary_building(canvas):
    """Draw an OPF-style hangar building matching the reference."""
    # Position moved right, away from VAB, and decreased height
    hangar_x = 250
    hangar_y = 305
    hangar_width = 70
    hangar_height = 60
    
    # More rounded roof using arc - properly positioned to attach to building
    roof_height = 10
    canvas.create_arc(
        hangar_x - 5, hangar_y - roof_height,
        hangar_x + hangar_width + 5, hangar_y + 5,
        start=0, extent=180,
        fill='#5a5e64', outline='#3a3a3a', width=2, style='chord'
    )
    
    # Main building body - cream/white color
    canvas.create_rectangle(
        hangar_x, hangar_y, 
        hangar_x + hangar_width, hangar_y + hangar_height,
        fill='#e8e8e8', outline='#3a3a3a', width=2
    )
    
    # Small blue windows on right side
    for i in range(2):
        canvas.create_rectangle(
            hangar_x + hangar_width - 12, hangar_y + 8 + i * 10,
            hangar_x + hangar_width - 6, hangar_y + 13 + i * 10,
            fill='#4a6a8a', outline='#3a5a7a'
        )
    
    # Horizontal line separator
    canvas.create_line(
        hangar_x + 5, hangar_y + 18,
        hangar_x + hangar_width - 5, hangar_y + 18,
        fill='#5a7a9a', width=2
    )
    
    # Large hangar door - dark blue
    door_x = hangar_x + 10
    door_y = hangar_y + 22
    door_w = 50
    door_h = hangar_height - 24
    
    # Door opening (dark blue interior)
    canvas.create_rectangle(
        door_x, door_y,
        door_x + door_w, door_y + door_h,
        fill='#1a3a5a', outline='#2a2a2a', width=2
    )
    
    # Darker inner door section
    canvas.create_rectangle(
        door_x + 5, door_y + 3,
        door_x + door_w - 5, door_y + door_h - 3,
        fill='#0a2a4a', outline=''
    )
    
    # Side windows next to door
    # Left windows
    canvas.create_rectangle(
        hangar_x + 5, door_y + 3,
        hangar_x + 9, door_y + 9,
        fill='#4a6a8a', outline='#3a5a7a'
    )

def draw_operations_building(canvas):
    """Draw the Launch Control Center (LCC) from Kennedy Space Center."""
    # Position closer to hangar (moved left)
    lcc_x = 330
    lcc_y = 255
    lcc_width = 80
    lcc_height = 110
    
    # Main building body - cream/beige color
    canvas.create_rectangle(
        lcc_x, lcc_y, 
        lcc_x + lcc_width, lcc_y + lcc_height,
        fill='#e8dfd0', outline='#000000', width=2
    )
    
    # Top section - dark gray roof area
    roof_height = 15
    canvas.create_rectangle(
        lcc_x, lcc_y,
        lcc_x + lcc_width, lcc_y + roof_height,
        fill='#4a4e54', outline=''
    )
    
    # Roof equipment (small structures on top)
    canvas.create_rectangle(
        lcc_x + 15, lcc_y - 6,
        lcc_x + 23, lcc_y,
        fill='#3a3a3a', outline='#000000', width=1
    )
    canvas.create_rectangle(
        lcc_x + 55, lcc_y - 6,
        lcc_x + 63, lcc_y,
        fill='#3a3a3a', outline='#000000', width=1
    )
    
    # Famous "Firing Room" windows - multiple rows of blue/dark windows
    firing_room_top = lcc_y + roof_height + 5
    firing_room_height = 45
    
    # Dark section behind windows
    canvas.create_rectangle(
        lcc_x + 5, firing_room_top,
        lcc_x + lcc_width - 5, firing_room_top + firing_room_height,
        fill='#2a2a2a', outline=''
    )
    
    # Multiple rows of windows (the iconic firing room windows)
    window_rows = 4
    window_cols = 8
    window_w = 7
    window_h = 8
    
    for row in range(window_rows):
        for col in range(window_cols):
            win_x = lcc_x + 8 + col * 9
            win_y = firing_room_top + 4 + row * 10
            canvas.create_rectangle(
                win_x, win_y,
                win_x + window_w, win_y + window_h,
                fill='#4a6a8a', outline='#3a5a7a'
            )
    
    # Middle section - regular office windows
    middle_start = firing_room_top + firing_room_height + 8
    
    for row in range(3):
        for col in range(6):
            win_x = lcc_x + 10 + col * 12
            win_y = middle_start + row * 12
            canvas.create_rectangle(
                win_x, win_y,
                win_x + 8, win_y + 8,
                fill='#5a7a9a', outline='#4a6a8a'
            )
    
    # Bottom section - entrance area
    bottom_start = lcc_y + lcc_height - 15
    
    # Entrance door
    door_x = lcc_x + lcc_width // 2 - 10
    canvas.create_rectangle(
        door_x, bottom_start,
        door_x + 20, lcc_y + lcc_height - 2,
        fill='#3a3a3a', outline='#2a2a2a', width=1
    )
    
    # Small windows on sides of entrance
    for i in range(2):
        # Left side
        canvas.create_rectangle(
            lcc_x + 8, bottom_start + 3,
            lcc_x + 14, bottom_start + 9,
            fill='#5a7a9a', outline='#4a6a8a'
        )
        # Right side
        canvas.create_rectangle(
            lcc_x + lcc_width - 14, bottom_start + 3,
            lcc_x + lcc_width - 8, bottom_start + 9,
            fill='#5a7a9a', outline='#4a6a8a'
        )
    
    # Right side depth panels (3D effect)
    canvas.create_rectangle(
        lcc_x + lcc_width, lcc_y + 8,
        lcc_x + lcc_width + 12, lcc_y + lcc_height,
        fill='#6a6e74', outline=''
    )
    
    canvas.create_rectangle(
        lcc_x + lcc_width + 12, lcc_y + 12,
        lcc_x + lcc_width + 20, lcc_y + lcc_height,
        fill='#5a5e64', outline=''
    )

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
    
    # Warning lights on tower (red - always on)
    light_heights = [tower_top_y+40, tower_top_y+100, tower_top_y+160]
    for light_y in light_heights:
        if light_y < tower_base_y:
            canvas.create_oval(tower_x-2, light_y, tower_x+2, light_y+4, fill='#ff4444', outline='')
            canvas.create_oval(tower_x+tower_width-2, light_y, tower_x+tower_width+2, light_y+4, fill='#ff4444', outline='')
    
    # Blinking white lights on the right-hand side thick red beam
    # Position them on the right vertical leg at different heights
    white_light_positions = [
        (tower_x + tower_width - 3, tower_top_y + 60),   # Upper light on right beam
        (tower_x + tower_width - 3, tower_top_y + 140),  # Lower light on right beam
    ]
    
    for light_x, light_y in white_light_positions:
        if light_y < tower_base_y:
            # Draw white light (will be toggled on/off)
            canvas.create_oval(
                light_x, light_y, 
                light_x + 6, light_y + 6, 
                fill='#3a3a3a', outline='#2a2a2a',  # Start off
                tags='tower_light'
            )


def draw_pond_with_gator(canvas, gator_visible=False, gator_animation_phase=0):
    """Draw a small pond with occasional alligator."""
    # Move pond up to area between buildings and launch pad
    pond_x = 735
    pond_y = 380
    
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
        submerge_offset = int(8 * (1 - gator_animation_phase))
        
        # Calculate opacity/visibility for parts based on phase
        show_eyes = gator_animation_phase > 0.3
        show_full_head = gator_animation_phase > 0.5
        show_ridges = gator_animation_phase > 0.2
        
        # Back ridges poking out of water
        if show_ridges:
            ridge_offset = int(submerge_offset * 0.5)
            canvas.create_oval(gator_x-12, gator_y+3+ridge_offset, gator_x-8, gator_y+6+ridge_offset, 
                             fill='#3a5a3a', outline='#2a4a2a', tags='gator')
            canvas.create_oval(gator_x-18, gator_y+5+ridge_offset, gator_x-14, gator_y+8+ridge_offset, 
                             fill='#3a5a3a', outline='#2a4a2a', tags='gator')
        
        # Gator head
        if show_full_head:
            canvas.create_oval(gator_x-8, gator_y-3+submerge_offset, gator_x+8, gator_y+5+submerge_offset, 
                             fill='#3a5a3a', outline='#2a4a2a', tags='gator')
            
            # Snout
            canvas.create_oval(gator_x+5, gator_y+submerge_offset, gator_x+10, gator_y+3+submerge_offset, 
                             fill='#4a6a4a', outline='#2a4a2a', tags='gator')
        
        # Eyes and nostrils
        if show_eyes:
            eye_offset = int(submerge_offset * 0.7)
            
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
            
            # Nostrils
            if show_full_head:
                canvas.create_oval(gator_x+7, gator_y+1+eye_offset, gator_x+8, gator_y+2+eye_offset, 
                                 fill='#1a1a1a', outline='', tags='gator')
        
        # Extra ripples when gator is moving
        if 0.1 < gator_animation_phase < 0.9:
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
            beam_color = '#ffffee'
            beam_outline = '#ffffaa'
            outline_width = 3
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
    """Draw a simple pixel car (horizontal orientation) and return IDs."""
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


def draw_car_vertical(canvas, x, y, car_color='#3a7bc8'):
    """Draw a simple pixel car (vertical orientation for parking) and return IDs."""
    car_ids = []
    # Car body (rotated 90 degrees - now vertical)
    car_ids.append(canvas.create_rectangle(x, y, x+6, y+12, fill=car_color, outline='', tags='car'))
    # Car top/cabin (front of car when vertical)
    car_ids.append(canvas.create_rectangle(x-3, y+2, x, y+10, fill=car_color, outline='', tags='car'))
    # Windows
    car_ids.append(canvas.create_rectangle(x-2, y+3, x, y+5, fill='#add8e6', outline='', tags='car'))
    car_ids.append(canvas.create_rectangle(x-2, y+7, x, y+9, fill='#add8e6', outline='', tags='car'))
    # Wheels
    car_ids.append(canvas.create_oval(x+5, y+1, x+8, y+4, fill='#1a1a1a', outline='', tags='car'))
    car_ids.append(canvas.create_oval(x+5, y+8, x+8, y+11, fill='#1a1a1a', outline='', tags='car'))
    return car_ids

def draw_background(canvas):
    """Draw the complete Kennedy Space Center background."""
    colors = get_sky_colors()
    
    # Sky - changes based on time of day - ADD TAGS
    canvas.create_rectangle(0, 0, 800, 400, fill=colors['sky'], outline='', tags='sky')
    
    # Add stars if nighttime - ADD TAGS
    hour = datetime.now().hour
    if hour >= 18 or hour < 6:
        draw_stars(canvas)
    
    # Ocean - teal/turquoise (lower on screen now) - ADD TAGS
    canvas.create_rectangle(0, 500, 800, 600, fill=colors['ocean'], outline='', tags='ocean')
    
    # Horizon line - darker teal - ADD TAGS
    canvas.create_rectangle(0, 500, 800, 515, fill=colors['horizon'], outline='', tags='horizon')
    
    # Grassy ground area (extended downwards to y=500)
    canvas.create_rectangle(0, 365, 800, 500, fill='#5a8c3a', outline='')
    
    # Extra grass coverage to ensure no gaps or blue blocks
    canvas.create_rectangle(0, 388, 800, 500, fill='#5a8c3a', outline='')
    
    # Draw roads BEFORE grass so grass appears on top
    draw_roads(canvas)
    
    # Add pixel grass details
    draw_pixel_grass(canvas)
    
    # Draw all buildings and structures
    draw_vab_building(canvas)
    draw_secondary_building(canvas)
    draw_operations_building(canvas)
    
    # Draw back fence BEFORE launch tower/pad so it appears behind
    draw_back_fence(canvas)
    
    draw_launch_tower(canvas)
    draw_launch_pad(canvas)
    
    # Draw remaining fence sides (left, right, bottom) and guard shack
    draw_security_fence_and_shack(canvas)
    
    # Draw pond (gator will be animated separately)
    draw_pond_with_gator(canvas, gator_visible=False)
    
    # Draw clouds - ALREADY HAVE TAGS
    cloud1 = draw_flat_cloud(canvas, 150, 60, colors['cloud'])
    cloud2 = draw_flat_cloud(canvas, 420, 90, colors['cloud'])
    cloud3 = draw_flat_cloud(canvas, 650, 50, colors['cloud'])
    
    return [cloud1, cloud2, cloud3]