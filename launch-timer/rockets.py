def draw_falcon_9(canvas, x, y):
    """Draw Falcon 9 based on actual reference - clean and accurate with proper proportions."""
    
    # === ENGINE SECTION (Bottom - Black) ===
    # Black engine base
    canvas.create_rectangle(x-10, y-12, x+10, y-5, fill='#1a1a1a', outline='#000000', width=1)
    canvas.create_rectangle(x+7, y-12, x+10, y-5, fill='#0a0a0a', outline='')
    
    # 9 Merlin engines in octaweb pattern with proper engine bells
    engine_positions = [
        (x, y-8),  # Center
        (x-3, y-8), (x+3, y-8),    # Left and right of center
        (x-1.5, y-6), (x+1.5, y-6),  # Lower pair
        (x-1.5, y-10), (x+1.5, y-10), # Upper pair
        (x-5, y-8), (x+5, y-8),    # Far left and right
    ]
    for ex, ey in engine_positions:
        # Engine bell (black, protruding down)
        canvas.create_oval(ex-2, ey-1, ex+2, ey+3, fill='#1a1a1a', outline='#000000', width=1)
        # Inner nozzle (darker)
        canvas.create_oval(ex-1.5, ey, ex+1.5, ey+2.5, fill='#0a0a0a', outline='')
        # Throat/opening (very dark)
        canvas.create_oval(ex-1, ey+0.5, ex+1, ey+2, fill='#2a2a2a', outline='')
    
    # === LANDING LEGS (Retracted - vertical against body) ===
    # Left leg (thin vertical strip)
    canvas.create_rectangle(x-11, y-35, x-9, y-10, fill='#2a2a2a', outline='#000000', width=1)
    # Right leg (thin vertical strip)
    canvas.create_rectangle(x+9, y-35, x+11, y-10, fill='#2a2a2a', outline='#000000', width=1)
    
    # === FIRST STAGE (White body) - SHORTENED ===
    canvas.create_rectangle(x-8, y-95, x+8, y-12, fill='#f5f5f5', outline='#000000', width=1)
    # Right side shading
    canvas.create_rectangle(x+5, y-95, x+8, y-12, fill='#d5d5d5', outline='')
    
    # === SPACEX LOGO (vertical text) ===
    text_y = y-75
    # "SPACEX" written vertically - simplified as rectangles
    logo_letters = [
        (text_y),      # S
        (text_y + 8),  # P
        (text_y + 16), # A
        (text_y + 24), # C
        (text_y + 32), # E
        (text_y + 40), # X
    ]
    for letter_y in logo_letters:
        canvas.create_rectangle(x-2.5, letter_y, x+2.5, letter_y+6, fill='#2a5a9a', outline='')
    
    # === AMERICAN FLAG (small, above logo) ===
    flag_y = y-86
    canvas.create_rectangle(x-3.5, flag_y, x+3.5, flag_y+4, fill='#ffffff', outline='')
    # Red stripes
    for i in [0, 2]:
        canvas.create_rectangle(x-3.5, flag_y+i, x+3.5, flag_y+i+1, fill='#d62828', outline='')
    # Blue canton
    canvas.create_rectangle(x-3.5, flag_y, x-1, flag_y+2, fill='#003f87', outline='')
    
    # === GRID FINS (Small black rectangles on sides) ===
    # Left grid fin
    canvas.create_rectangle(x-11, y-92, x-8, y-87, fill='#2a2a2a', outline='#000000', width=1)
    # Right grid fin
    canvas.create_rectangle(x+8, y-92, x+11, y-87, fill='#2a2a2a', outline='#000000', width=1)
    
    # === BLACK INTERSTAGE ===
    canvas.create_rectangle(x-8, y-102, x+8, y-95, fill='#1a1a1a', outline='#000000', width=1)
    canvas.create_rectangle(x+5, y-102, x+8, y-95, fill='#0a0a0a', outline='')
    
    # === SECOND STAGE (White) - SHORTENED ===
    canvas.create_rectangle(x-7, y-125, x+7, y-102, fill='#f5f5f5', outline='#000000', width=1)
    # Right side shading
    canvas.create_rectangle(x+4, y-125, x+7, y-102, fill='#d5d5d5', outline='')
    
    # === PAYLOAD FAIRING (White, with 45-degree shoulder and smooth ogive taper) ===
    
    # Fairing structure from bottom to top:
    # 1. 45-degree shoulder extending outward
    # 2. Cylindrical section
    # 3. Smooth ogive taper to point
    
    # Build the complete fairing outline as a polygon
    fairing_points = [
        # Start at second stage top left
        x-7, y-125,
        # 45-degree shoulder going OUT and UP (left side)
        x-10, y-130,
        # Cylindrical section (left side)
        x-10, y-140,
        # Smooth ogive curve to point (left side)
        x-9.5, y-145,
        x-9, y-150,
        x-8, y-155,
        x-6.5, y-160,
        x-5, y-164,
        x-3.5, y-167,
        x-2, y-169,
        x-1, y-170,
        # Top point
        x, y-171,
        # Smooth ogive curve down (right side - mirror)
        x+1, y-170,
        x+2, y-169,
        x+3.5, y-167,
        x+5, y-164,
        x+6.5, y-160,
        x+8, y-155,
        x+9, y-150,
        x+9.5, y-145,
        # Cylindrical section (right side)
        x+10, y-140,
        # 45-degree shoulder going IN and DOWN (right side)
        x+10, y-130,
        x+7, y-125,
    ]
    
    # Main fairing body (light gray)
    canvas.create_polygon(fairing_points, fill='#e8e8e8', outline='#000000', width=1, smooth=True)
    
    # Shading on right side of fairing
    fairing_shade_points = [
        x+4, y-125,
        x+7, y-130,
        x+7, y-140,
        x+7.5, y-145,
        x+8, y-150,
        x+8.5, y-155,
        x+7.5, y-160,
        x+6, y-164,
        x+4, y-167,
        x+2, y-169,
        x+1, y-170,
        x, y-171,
        x+1, y-170,
        x+2, y-169,
        x+3.5, y-167,
        x+5, y-164,
        x+6.5, y-160,
        x+8, y-155,
        x+9, y-150,
        x+9.5, y-145,
        x+10, y-140,
        x+10, y-130,
        x+7, y-125,
    ]
    canvas.create_polygon(fairing_shade_points, fill='#c8c8c8', outline='', smooth=True)

def draw_starship(canvas, x, y):
    """Draw Starship style rocket - more accurate based on reference."""
    # Super Heavy Booster (first stage) - stainless steel
    booster_height = 90
    canvas.create_rectangle(x-12, y-booster_height, x+12, y-20, fill='#c8c8c8', outline='')
    canvas.create_rectangle(x+8, y-booster_height, x+12, y-20, fill='#a0a0a0', outline='')
    
    # Grid fins on booster (4 visible - 2 on each side)
    # Upper grid fins
    canvas.create_rectangle(x-16, y-75, x-12, y-65, fill='#909090', outline='')
    canvas.create_rectangle(x+12, y-75, x+16, y-65, fill='#909090', outline='')
    # Lower grid fins
    canvas.create_rectangle(x-16, y-45, x-12, y-35, fill='#909090', outline='')
    canvas.create_rectangle(x+12, y-45, x+16, y-35, fill='#909090', outline='')
    
    # Booster interstage section with vents/details
    vent_positions = [y-85, y-70, y-55, y-40, y-25]
    for vent_y in vent_positions:
        # Horizontal vent lines
        canvas.create_rectangle(x-11, vent_y, x+11, vent_y+2, fill='#b0b0b0', outline='')
    
    # Starship (second stage/ship) - stainless steel
    ship_height = 70
    canvas.create_rectangle(x-12, y-booster_height-ship_height, x+12, y-booster_height, fill='#d0d0d0', outline='')
    canvas.create_rectangle(x+8, y-booster_height-ship_height, x+12, y-booster_height, fill='#b0b0b0', outline='')
    
    # Black heat tiles on windward side (checkerboard pattern)
    for i in range(10):
        for j in range(2):
            tile_y = y-booster_height - 10 - i*6
            tile_x = x-10+j*10
            if tile_y > y-booster_height-ship_height+10:
                canvas.create_rectangle(tile_x, tile_y, tile_x+8, tile_y+5, fill='#1a1a1a', outline='')
    
    # Forward flaps (canards near nose)
    canvas.create_polygon(x-12, y-booster_height-60, x-20, y-booster_height-58, x-12, y-booster_height-56, fill='#a0a0a0', outline='')
    canvas.create_polygon(x+12, y-booster_height-60, x+20, y-booster_height-58, x+12, y-booster_height-56, fill='#a0a0a0', outline='')
    
    # Aft flaps (near base of ship)
    canvas.create_polygon(x-12, y-booster_height-15, x-22, y-booster_height-10, x-12, y-booster_height-5, fill='#a0a0a0', outline='')
    canvas.create_polygon(x+12, y-booster_height-15, x+22, y-booster_height-10, x+12, y-booster_height-5, fill='#a0a0a0', outline='')
    
    # Payload bay doors/lines on ship
    canvas.create_rectangle(x-11, y-booster_height-55, x+11, y-booster_height-53, fill='#b8b8b8', outline='')
    canvas.create_rectangle(x-11, y-booster_height-40, x+11, y-booster_height-38, fill='#b8b8b8', outline='')
    
    # Nose cone - pointed stainless steel
    canvas.create_polygon(x-12, y-booster_height-ship_height, x, y-booster_height-ship_height-20, x+12, y-booster_height-ship_height, fill='#d0d0d0', outline='')
    canvas.create_polygon(x+8, y-booster_height-ship_height, x, y-booster_height-ship_height-20, x+12, y-booster_height-ship_height, fill='#b0b0b0', outline='')
    
    # Window on nose (small black)
    canvas.create_oval(x-3, y-booster_height-ship_height-8, x+3, y-booster_height-ship_height-3, fill='#1a1a1a', outline='')
    
    # Raptor engines on Starship (6 engines - 3 sea level, 3 vacuum)
    ship_engine_y = y-booster_height-5
    ship_engines = [(x-6, ship_engine_y), (x, ship_engine_y), (x+6, ship_engine_y)]
    for ex, ey in ship_engines:
        canvas.create_oval(ex-2, ey-2, ex+2, ey+2, fill='#3a3a3a', outline='')
    
    # Super Heavy Raptor engines (33 engines in cluster)
    booster_engine_y = y-12
    # Outer ring of engines
    for i in range(8):
        angle = i * 45
        ex = x + int(7 * (1 if i % 2 == 0 else 0.7) * (1 if i in [0,4] else (0 if i in [2,6] else 0.7)))
        ey = booster_engine_y + int(7 * (1 if i % 2 == 1 else 0.7) * (1 if i in [2,6] else (0 if i in [0,4] else 0.7)))
        if i in [0, 2, 4, 6]:  # Cardinal directions
            canvas.create_oval(ex-1.5, ey-1.5, ex+1.5, ey+1.5, fill='#2a2a2a', outline='')
    
    # Inner ring
    inner_positions = [(x-4, booster_engine_y), (x+4, booster_engine_y), (x, booster_engine_y-3), (x, booster_engine_y+3)]
    for ex, ey in inner_positions:
        canvas.create_oval(ex-1.5, ey-1.5, ex+1.5, ey+1.5, fill='#2a2a2a', outline='')
    
    # Center engines
    canvas.create_oval(x-2, booster_engine_y-1, x+2, booster_engine_y+1, fill='#3a3a3a', outline='')
    
    # Engine section structure
    canvas.create_rectangle(x-13, y-20, x+13, y-10, fill='#2a2a2a', outline='')
    canvas.create_rectangle(x+9, y-20, x+13, y-10, fill='#1a1a1a', outline='')


def draw_atlas(canvas, x, y):
    """Draw Atlas V style rocket - more accurate based on reference."""
    # Solid Rocket Boosters (SRBs) - white on sides
    # Left booster
    canvas.create_rectangle(x-17, y-75, x-12, y, fill='#ffffff', outline='')
    canvas.create_rectangle(x-15, y-75, x-12, y, fill='#e0e0e0', outline='')
    canvas.create_polygon(x-17, y-75, x-14.5, y-82, x-12, y-75, fill='#e8e8e8', outline='')
    # Left booster nozzle
    canvas.create_oval(x-16, y-6, x-13, y-3, fill='#3a3a3a', outline='')
    
    # Right booster
    canvas.create_rectangle(x+12, y-75, x+17, y, fill='#ffffff', outline='')
    canvas.create_rectangle(x+14, y-75, x+17, y, fill='#e0e0e0', outline='')
    canvas.create_polygon(x+12, y-75, x+14.5, y-82, x+17, y-75, fill='#e8e8e8', outline='')
    # Right booster nozzle
    canvas.create_oval(x+13, y-6, x+16, y-3, fill='#3a3a3a', outline='')
    
    # First stage (Centaur) - orange/gold
    canvas.create_rectangle(x-8, y-125, x+8, y-75, fill='#ff8c00', outline='')
    canvas.create_rectangle(x+5, y-125, x+8, y-75, fill='#d67300', outline='')
    
    # White separation band
    canvas.create_rectangle(x-8, y-126, x+8, y-125, fill='#f0f0f0', outline='')
    
    # Second stage - white/light gray
    canvas.create_rectangle(x-7, y-145, x+7, y-126, fill='#f8f8f8', outline='')
    canvas.create_rectangle(x+4, y-145, x+7, y-126, fill='#d8d8d8', outline='')
    
    # Payload fairing - white pointed nose
    canvas.create_polygon(x-7, y-145, x, y-158, x+7, y-145, fill='#f8f8f8', outline='')
    canvas.create_polygon(x+4, y-145, x, y-158, x+7, y-145, fill='#d8d8d8', outline='')
    
    # Red "3" circle on nose (ULA logo area)
    canvas.create_oval(x-4, y-152, x+4, y-146, fill='#d44444', outline='')
    canvas.create_text(x, y-149, text="3", font=('Arial', 6, 'bold'), fill='#ffffff')
    
    # American flag
    flag_y = y-140
    canvas.create_rectangle(x-6, flag_y, x+6, flag_y+5, fill='#ffffff', outline='')
    # Red stripes
    for i in range(3):
        if i % 2 == 0:
            canvas.create_rectangle(x-6, flag_y+i*1.5, x+6, flag_y+(i+1)*1.5, fill='#d62828', outline='')
    # Blue canton
    canvas.create_rectangle(x-6, flag_y, x-2, flag_y+2.5, fill='#003f87', outline='')
    
    # "ATLAS" text on second stage (simplified)
    text_y = y-133
    canvas.create_text(x, text_y, text="ATLAS", font=('Arial', 5, 'bold'), fill='#2a5a9a')
    
    # ULA logo text on second stage
    logo_y = y-138
    canvas.create_text(x, logo_y, text="ULA", font=('Arial', 4, 'bold'), fill='#2a5a9a')
    
    # Main engine (RD-180) - single large engine
    canvas.create_oval(x-4, y-78, x+4, y-73, fill='#4a4a4a', outline='')
    
    # Engine details on first stage
    canvas.create_rectangle(x-8, y-76, x+8, y-75, fill='#d67300', outline='')


def draw_delta(canvas, x, y):
    """Draw Delta IV Heavy style rocket."""
    canvas.create_rectangle(x-7, y-130, x+7, y, fill='#ff8c00', outline='')
    canvas.create_rectangle(x+4, y-130, x+7, y, fill='#d67300', outline='')
    canvas.create_rectangle(x-20, y-115, x-12, y, fill='#ff8c00', outline='')
    canvas.create_rectangle(x-15, y-115, x-12, y, fill='#d67300', outline='')
    canvas.create_rectangle(x+12, y-115, x+20, y, fill='#ff8c00', outline='')
    canvas.create_rectangle(x+17, y-115, x+20, y, fill='#d67300', outline='')
    canvas.create_polygon(x-7, y-130, x, y-150, x+7, y-130, fill='#f5f5f5', outline='')
    canvas.create_polygon(x+4, y-130, x, y-150, x+7, y-130, fill='#d8d8d8', outline='')
    canvas.create_oval(x-4, y-10, x+4, y-4, fill='#6a4a3a', outline='')
    canvas.create_oval(x-17, y-8, x-13, y-4, fill='#6a4a3a', outline='')
    canvas.create_oval(x+13, y-8, x+17, y-4, fill='#6a4a3a', outline='')


def draw_sls(canvas, x, y):
    """Draw SLS (Space Launch System) style rocket - more accurate based on reference."""
    # Two white Solid Rocket Boosters (SRBs) on sides
    # Left booster
    canvas.create_rectangle(x-23, y-155, x-14, y, fill='#f8f8f8', outline='')
    canvas.create_rectangle(x-17, y-155, x-14, y, fill='#d8d8d8', outline='')
    # Left booster nose cone (white pointed)
    canvas.create_polygon(x-23, y-155, x-18.5, y-168, x-14, y-155, fill='#f0f0f0', outline='')
    # Left booster segmentation lines (white bands)
    for seg in [y-130, y-100, y-70, y-40]:
        canvas.create_rectangle(x-23, seg, x-14, seg+3, fill='#e0e0e0', outline='')
    # Left booster nozzle
    canvas.create_oval(x-21, y-8, x-16, y-3, fill='#4a4a4a', outline='')
    
    # Right booster
    canvas.create_rectangle(x+14, y-155, x+23, y, fill='#f8f8f8', outline='')
    canvas.create_rectangle(x+20, y-155, x+23, y, fill='#d8d8d8', outline='')
    # Right booster nose cone
    canvas.create_polygon(x+14, y-155, x+18.5, y-168, x+23, y-155, fill='#f0f0f0', outline='')
    # Right booster segmentation lines
    for seg in [y-130, y-100, y-70, y-40]:
        canvas.create_rectangle(x+14, seg, x+23, seg+3, fill='#e0e0e0', outline='')
    # Right booster nozzle
    canvas.create_oval(x+16, y-8, x+21, y-3, fill='#4a4a4a', outline='')
    
    # Core stage (main body) - ORANGE
    canvas.create_rectangle(x-9, y-170, x+9, y, fill='#ff8c00', outline='')
    canvas.create_rectangle(x+6, y-170, x+9, y, fill='#d67300', outline='')
    
    # Core stage segmentation bands (darker orange)
    for seg in [y-140, y-105, y-70, y-35]:
        canvas.create_rectangle(x-9, seg, x+9, seg+2, fill='#d67300', outline='')
    
    # Upper stage - orange (ICPS)
    canvas.create_rectangle(x-8, y-180, x+8, y-170, fill='#ff9933', outline='')
    canvas.create_rectangle(x+5, y-180, x+8, y-170, fill='#d67300', outline='')
    
    # Orion spacecraft capsule at top - dark gray/black
    canvas.create_oval(x-8, y-195, x+8, y-180, fill='#4a4a4a', outline='')
    canvas.create_oval(x+4, y-195, x+8, y-187, fill='#3a3a3a', outline='')
    
    # Orion windows (small light rectangles)
    canvas.create_rectangle(x-5, y-188, x-2, y-185, fill='#6a7a8a', outline='')
    canvas.create_rectangle(x+2, y-188, x+5, y-185, fill='#6a7a8a', outline='')
    
    # Launch Abort System (LAS) tower on top - red
    canvas.create_rectangle(x-2, y-210, x+2, y-195, fill='#d44444', outline='')
    # LAS nozzles
    canvas.create_rectangle(x-3, y-208, x-1, y-205, fill='#a03333', outline='')
    canvas.create_rectangle(x+1, y-208, x+3, y-205, fill='#a03333', outline='')
    # LAS tip
    canvas.create_polygon(x-2, y-210, x, y-215, x+2, y-210, fill='#d44444', outline='')
    
    # NASA text on core stage (simplified)
    text_y = y-120
    canvas.create_text(x, text_y, text="NASA", font=('Arial', 6, 'bold'), fill='#ffffff')
    
    # American flag on core stage
    flag_y = y-145
    canvas.create_rectangle(x-7, flag_y, x+7, flag_y+6, fill='#ffffff', outline='')
    # Red stripes
    for i in range(4):
        if i % 2 == 0:
            canvas.create_rectangle(x-7, flag_y+i*1.5, x+7, flag_y+(i+1)*1.5, fill='#d62828', outline='')
    # Blue canton
    canvas.create_rectangle(x-7, flag_y, x-2, flag_y+3, fill='#003f87', outline='')
    
    # Four RS-25 engines at base (arranged in square pattern)
    engine_positions = [(x-4, y-10), (x+4, y-10), (x-4, y-6), (x+4, y-6)]
    for ex, ey in engine_positions:
        canvas.create_oval(ex-2, ey-2, ex+2, ey+2, fill='#6a4a3a', outline='')
    
    # Engine mounting structure
    canvas.create_rectangle(x-10, y-12, x+10, y-5, fill='#2a2a2a', outline='')


def draw_electron(canvas, x, y):
    """Draw Electron style rocket (small) - more accurate based on reference."""
    # Main body - black carbon composite
    canvas.create_rectangle(x-5, y-105, x+5, y, fill='#1a1a1a', outline='')
    # Body shading
    canvas.create_rectangle(x+3, y-105, x+5, y, fill='#0a0a0a', outline='')
    
    # Payload fairing - black pointed nose cone
    canvas.create_polygon(x-5, y-105, x, y-120, x+5, y-105, fill='#1a1a1a', outline='')
    canvas.create_polygon(x+3, y-105, x, y-120, x+5, y-105, fill='#0a0a0a', outline='')
    
    # White/silver separation bands
    canvas.create_rectangle(x-5, y-100, x+5, y-97, fill='#d0d0d0', outline='')
    canvas.create_rectangle(x-5, y-65, x+5, y-62, fill='#d0d0d0', outline='')
    
    # "ELECTRON" text vertically on body (simplified white dots)
    text_start_y = y-55
    text_positions = [0, 6, 12, 18, 24, 30, 36, 42]  # 8 letters
    for i, offset in enumerate(text_positions):
        canvas.create_rectangle(x-3, text_start_y+offset, x-1, text_start_y+offset+3, fill='#e0e0e0', outline='')
    
    # Small American flag near bottom
    flag_y = y-18
    canvas.create_rectangle(x-4, flag_y, x+4, flag_y+5, fill='#ffffff', outline='')
    # Red stripes (simplified)
    canvas.create_rectangle(x-4, flag_y, x+4, flag_y+1, fill='#d62828', outline='')
    canvas.create_rectangle(x-4, flag_y+2, x+4, flag_y+3, fill='#d62828', outline='')
    canvas.create_rectangle(x-4, flag_y+4, x+4, flag_y+5, fill='#d62828', outline='')
    # Blue canton
    canvas.create_rectangle(x-4, flag_y, x-1, flag_y+3, fill='#003f87', outline='')
    
    # Landing legs (small triangular)
    canvas.create_polygon(x-5, y-15, x-9, y-5, x-5, y-8, fill='#2a2a2a', outline='')
    canvas.create_polygon(x+5, y-15, x+9, y-5, x+5, y-8, fill='#2a2a2a', outline='')
    
    # Engine section at base - Rutherford engines (9 small engines)
    engine_base_y = y-8
    # Engine cluster pattern (3x3 grid simplified)
    engine_positions = [
        (x-3, engine_base_y), (x, engine_base_y), (x+3, engine_base_y),
        (x-2, engine_base_y+2), (x+2, engine_base_y+2),
        (x-1, engine_base_y+4), (x+1, engine_base_y+4)
    ]
    for ex, ey in engine_positions:
        canvas.create_oval(ex-1, ey, ex+1, ey+2, fill='#4a3a2a', outline='')
    
    # Engine mounting structure
    canvas.create_rectangle(x-6, y-12, x+6, y-8, fill='#2a2a2a', outline='')


def draw_generic_rocket(canvas, x, y):
    """Draw a generic rocket."""
    canvas.create_rectangle(x-8, y-115, x+8, y, fill='#f5f5f5', outline='')
    canvas.create_rectangle(x+5, y-115, x+8, y, fill='#d0d0d0', outline='')
    canvas.create_rectangle(x-8, y-70, x+8, y-60, fill='#d44444', outline='')
    canvas.create_rectangle(x-8, y-55, x+8, y-50, fill='#4a69bd', outline='')
    canvas.create_polygon(x-8, y-115, x, y-135, x+8, y-115, fill='#d44444', outline='')
    canvas.create_polygon(x+5, y-115, x, y-135, x+8, y-115, fill='#b03333', outline='')
    canvas.create_polygon(x-8, y-25, x-16, y-5, x-8, y, fill='#c0c0c0', outline='')
    canvas.create_polygon(x+8, y-25, x+16, y-5, x+8, y, fill='#a0a0a0', outline='')
    canvas.create_oval(x-5, y-10, x+5, y-3, fill='#4a4a4a', outline='')


def draw_rocket_on_pad(canvas, vehicle_name, pad_x=605, pad_y=340):
    """Draw different rockets based on vehicle name with appropriate scaling."""
    vehicle_lower = vehicle_name.lower() if vehicle_name else ''
    
    # Determine if this is a large rocket that needs scaling
    is_large_rocket = any(keyword in vehicle_lower for keyword in ['starship', 'sls', 'space launch system'])
    
    # Adjust position for larger rockets (draw them lower/bigger)
    if is_large_rocket:
        # Scale factor and adjust Y position to keep base at same level
        scale_y_offset = 60  # Draw higher up to accommodate larger size
        actual_pad_y = pad_y + scale_y_offset
    else:
        actual_pad_y = pad_y
    
    if 'falcon 9' in vehicle_lower or 'falcon' in vehicle_lower:
        draw_falcon_9(canvas, pad_x, actual_pad_y)
    elif 'starship' in vehicle_lower:
        draw_starship_large(canvas, pad_x, actual_pad_y)
    elif 'atlas' in vehicle_lower:
        draw_atlas(canvas, pad_x, actual_pad_y)
    elif 'delta' in vehicle_lower:
        draw_delta(canvas, pad_x, actual_pad_y)
    elif 'sls' in vehicle_lower or 'space launch system' in vehicle_lower:
        draw_sls_large(canvas, pad_x, actual_pad_y)
    elif 'electron' in vehicle_lower:
        draw_electron(canvas, pad_x, actual_pad_y)
    else:
        draw_generic_rocket(canvas, pad_x, actual_pad_y)


def draw_starship_large(canvas, x, y):
    """Draw larger Starship for proper scale."""
    # Scale up by ~1.4x
    scale = 1.4
    
    # Super Heavy Booster (first stage)
    booster_height = int(90 * scale)
    canvas.create_rectangle(x-int(12*scale), y-booster_height, x+int(12*scale), y-int(20*scale), fill='#c8c8c8', outline='')
    canvas.create_rectangle(x+int(8*scale), y-booster_height, x+int(12*scale), y-int(20*scale), fill='#a0a0a0', outline='')
    
    # Grid fins on booster
    canvas.create_rectangle(x-int(16*scale), y-int(75*scale), x-int(12*scale), y-int(65*scale), fill='#909090', outline='')
    canvas.create_rectangle(x+int(12*scale), y-int(75*scale), x+int(16*scale), y-int(65*scale), fill='#909090', outline='')
    canvas.create_rectangle(x-int(16*scale), y-int(45*scale), x-int(12*scale), y-int(35*scale), fill='#909090', outline='')
    canvas.create_rectangle(x+int(12*scale), y-int(45*scale), x+int(16*scale), y-int(35*scale), fill='#909090', outline='')
    
    # Booster vent lines
    vent_positions = [y-int(85*scale), y-int(70*scale), y-int(55*scale), y-int(40*scale), y-int(25*scale)]
    for vent_y in vent_positions:
        canvas.create_rectangle(x-int(11*scale), vent_y, x+int(11*scale), vent_y+int(2*scale), fill='#b0b0b0', outline='')
    
    # Starship (second stage)
    ship_height = int(70 * scale)
    canvas.create_rectangle(x-int(12*scale), y-booster_height-ship_height, x+int(12*scale), y-booster_height, fill='#d0d0d0', outline='')
    canvas.create_rectangle(x+int(8*scale), y-booster_height-ship_height, x+int(12*scale), y-booster_height, fill='#b0b0b0', outline='')
    
    # Heat tiles
    for i in range(10):
        for j in range(2):
            tile_y = y-booster_height - int(10*scale) - i*int(6*scale)
            tile_x = x-int(10*scale)+j*int(10*scale)
            if tile_y > y-booster_height-ship_height+int(10*scale):
                canvas.create_rectangle(tile_x, tile_y, tile_x+int(8*scale), tile_y+int(5*scale), fill='#1a1a1a', outline='')
    
    # Flaps
    canvas.create_polygon(x-int(12*scale), y-booster_height-int(60*scale), x-int(20*scale), y-booster_height-int(58*scale), 
                         x-int(12*scale), y-booster_height-int(56*scale), fill='#a0a0a0', outline='')
    canvas.create_polygon(x+int(12*scale), y-booster_height-int(60*scale), x+int(20*scale), y-booster_height-int(58*scale), 
                         x+int(12*scale), y-booster_height-int(56*scale), fill='#a0a0a0', outline='')
    canvas.create_polygon(x-int(12*scale), y-booster_height-int(15*scale), x-int(22*scale), y-booster_height-int(10*scale), 
                         x-int(12*scale), y-booster_height-int(5*scale), fill='#a0a0a0', outline='')
    canvas.create_polygon(x+int(12*scale), y-booster_height-int(15*scale), x+int(22*scale), y-booster_height-int(10*scale), 
                         x+int(12*scale), y-booster_height-int(5*scale), fill='#a0a0a0', outline='')
    
    # Nose cone
    canvas.create_polygon(x-int(12*scale), y-booster_height-ship_height, x, y-booster_height-ship_height-int(20*scale), 
                         x+int(12*scale), y-booster_height-ship_height, fill='#d0d0d0', outline='')
    canvas.create_oval(x-int(3*scale), y-booster_height-ship_height-int(8*scale), 
                      x+int(3*scale), y-booster_height-ship_height-int(3*scale), fill='#1a1a1a', outline='')
    
    # Engines
    canvas.create_rectangle(x-int(13*scale), y-int(20*scale), x+int(13*scale), y-int(10*scale), fill='#2a2a2a', outline='')


def draw_sls_large(canvas, x, y):
    """Draw larger SLS for proper scale."""
    # Scale up by ~1.3x
    scale = 1.3
    
    # SRBs
    canvas.create_rectangle(x-int(23*scale), y-int(155*scale), x-int(14*scale), y, fill='#f8f8f8', outline='')
    canvas.create_rectangle(x-int(17*scale), y-int(155*scale), x-int(14*scale), y, fill='#d8d8d8', outline='')
    canvas.create_polygon(x-int(23*scale), y-int(155*scale), x-int(18.5*scale), y-int(168*scale), 
                         x-int(14*scale), y-int(155*scale), fill='#f0f0f0', outline='')
    for seg in [y-int(130*scale), y-int(100*scale), y-int(70*scale), y-int(40*scale)]:
        canvas.create_rectangle(x-int(23*scale), seg, x-int(14*scale), seg+int(3*scale), fill='#e0e0e0', outline='')
    canvas.create_oval(x-int(21*scale), y-int(8*scale), x-int(16*scale), y-int(3*scale), fill='#4a4a4a', outline='')
    
    canvas.create_rectangle(x+int(14*scale), y-int(155*scale), x+int(23*scale), y, fill='#f8f8f8', outline='')
    canvas.create_rectangle(x+int(20*scale), y-int(155*scale), x+int(23*scale), y, fill='#d8d8d8', outline='')
    canvas.create_polygon(x+int(14*scale), y-int(155*scale), x+int(18.5*scale), y-int(168*scale), 
                         x+int(23*scale), y-int(155*scale), fill='#f0f0f0', outline='')
    for seg in [y-int(130*scale), y-int(100*scale), y-int(70*scale), y-int(40*scale)]:
        canvas.create_rectangle(x+int(14*scale), seg, x+int(23*scale), seg+int(3*scale), fill='#e0e0e0', outline='')
    canvas.create_oval(x+int(16*scale), y-int(8*scale), x+int(21*scale), y-int(3*scale), fill='#4a4a4a', outline='')
    
    # Core stage
    canvas.create_rectangle(x-int(9*scale), y-int(170*scale), x+int(9*scale), y, fill='#ff8c00', outline='')
    canvas.create_rectangle(x+int(6*scale), y-int(170*scale), x+int(9*scale), y, fill='#d67300', outline='')
    
    for seg in [y-int(140*scale), y-int(105*scale), y-int(70*scale), y-int(35*scale)]:
        canvas.create_rectangle(x-int(9*scale), seg, x+int(9*scale), seg+int(2*scale), fill='#d67300', outline='')
    
    # Upper stage
    canvas.create_rectangle(x-int(8*scale), y-int(180*scale), x+int(8*scale), y-int(170*scale), fill='#ff9933', outline='')
    
    # Orion
    canvas.create_oval(x-int(8*scale), y-int(195*scale), x+int(8*scale), y-int(180*scale), fill='#4a4a4a', outline='')
    
    # LAS
    canvas.create_rectangle(x-int(2*scale), y-int(210*scale), x+int(2*scale), y-int(195*scale), fill='#d44444', outline='')
    canvas.create_polygon(x-int(2*scale), y-int(210*scale), x, y-int(215*scale), x+int(2*scale), y-int(210*scale), fill='#d44444', outline='')
    
    # Flag
    flag_y = y-int(145*scale)
    canvas.create_rectangle(x-int(7*scale), flag_y, x+int(7*scale), flag_y+int(6*scale), fill='#ffffff', outline='')
    for i in range(4):
        if i % 2 == 0:
            canvas.create_rectangle(x-int(7*scale), flag_y+i*int(1.5*scale), x+int(7*scale), flag_y+(i+1)*int(1.5*scale), fill='#d62828', outline='')
    canvas.create_rectangle(x-int(7*scale), flag_y, x-int(2*scale), flag_y+int(3*scale), fill='#003f87', outline='')
    
    # Engines
    canvas.create_rectangle(x-int(10*scale), y-int(12*scale), x+int(10*scale), y-int(5*scale), fill='#2a2a2a', outline='')