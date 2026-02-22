# Launch Countdown — Phase 2

## Quick Start

```bash
pip install -r requirements.txt
python server.py
```

Your browser opens automatically at http://localhost:5000


## File Structure

```
phase2/
├── server.py               ← Run this. Flask backend + API proxy.
├── requirements.txt
├── static/
│   ├── index.html
│   ├── js/
│   │   └── app.js          ← All rendering, animation, countdown logic
│   └── assets/             ← Drop your PNG files here
│       ├── vab.png
│       ├── launch_tower.png
│       ├── launch_pad.png
│       ├── rocket_falcon9.png
│       ├── rocket_starship.png
│       ├── rocket_electron.png
│       ├── rocket_atlas.png
│       ├── rocket_sls.png
│       └── rocket_generic.png  ← fallback for unknown vehicles
```


## Adding PNG Assets

Drop any PNG into `static/assets/` with the exact filename shown above.
The app loads them on startup — if a file is missing it falls back to
the procedural drawing automatically. You can add assets one at a time.

**Recommended sizes (canvas is 800×600):**

| Asset          | Suggested size   | Notes                              |
|----------------|------------------|------------------------------------|
| vab.png        | 200 × 150 px     | Anchored top-left at (60, 215)     |
| launch_tower.png | 80 × 220 px   | Bottom anchored at y=340           |
| launch_pad.png | 140 × 40 px      | Drawn at (550, 320)                |
| rocket_*.png   | ~30 × 160 px     | Centred on x=620, base at y=340    |

Transparent backgrounds (RGBA PNGs) work perfectly.


## Architecture

```
Browser  ──── GET /api/launches ────► server.py ──► RocketLaunch.Live
         ◄──── JSON (launches)  ────┘
         ──── GET /api/weather  ────► server.py ──► Open-Meteo
         ◄──── JSON (weather)   ────┘
```

- **server.py** handles all external API calls with 5-min / 15-min caches.
- **app.js** computes the countdown locally every frame (no server round-trip per second).
- Weather uses Open-Meteo — free, no API key, reliable sub-10ms responses.


## Launch Trigger Fix

Phase 1 had a bug where `trigger_launch()` was called every second while
`total_seconds` was in the 0–5 window, causing multiple or missed triggers.

Phase 2 fix: a single `state.launchTriggered` boolean is set to `true` at
T-0 and only reset to `false` when a new mission is loaded. The countdown
loop checks this flag before firing so the animation runs exactly once.
