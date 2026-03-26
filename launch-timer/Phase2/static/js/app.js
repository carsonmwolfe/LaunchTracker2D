/**
 * Launch Countdown — Phase 2
 * 800×600 canvas renderer, mirrors Phase 1 layout.
 *
 * Asset loading:  All PNGs live in /static/assets/.
 * Fallback:       If a PNG fails to load the canvas falls back to drawing
 *                 the same coloured shapes as Phase 1 so the app always works.
 *
 * Launch fix:     A single `launchTriggered` flag prevents the T-0 event from
 *                 firing more than once per mission.
 */

'use strict';

// ─────────────────────────────────────────────────────────────────────────────
//  ASSET MANIFEST
//  Add real PNGs to /static/assets/ with these exact filenames and they will
//  be used automatically.  Anything that fails to load falls back gracefully.
// ─────────────────────────────────────────────────────────────────────────────
const ASSETS = {
  // Landscape / structures
  vab:             'ground-VAB.png',  // Updated to new VAB
  launchTower:     'ground-LaunchPad.png',  // This file contains both tower AND pad
  launchPad:       'ground-LaunchPad.png',
  countdownClock:  'ground-countdownclock.png',  // New countdown clock display
  hif:             'ground-HIF.png',
  te:              'ground-TE.png',
  rocket_falcon9:   'rocket-falcon9.png',
  rocket_atlas:     'rocket-atlasV.png',
  rocket_vulcan:    'rocket-vulcan.png',
  rocket_electron:  'rocket-electron.png',
  rocket_ng:        'rocket-NG.png',
  rocket_kairos:    'rocket-KAIROS.png',
  rocket_longmarch: 'rocket-longmarch.png',
  rocket_generic:   'rocket-falcon9.png',
  rocket_starship:  'rocket-starship.png',
  rocket_soyuz:     'rocket-Soyuz.png',
  rocket_ariane6:   'rocket-Ariane6.png',
  rocket_sls:       'rocket-SLS.png',
  rocket_kinetica:  'rocket-Kinetica2.png',
  rocket_gslv:      'rocket-GSLV.png',
  rocket_firefly:   'rocket-firefly.png',
};

// Loaded Image objects (null = not yet loaded / unavailable)
const IMG = {};

function loadAssets() {
  return Promise.all(
    Object.entries(ASSETS).map(([key, file]) =>
      new Promise(resolve => {
        const img = new Image();
        img.onload  = () => { IMG[key] = img; resolve(); };
        img.onerror = () => { IMG[key] = null;  resolve(); };   // graceful fallback
        img.src = `/static/assets/${file}`;
      })
    )
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  STATE
// ─────────────────────────────────────────────────────────────────────────────
const canvas  = document.getElementById('c');
const ctx     = canvas.getContext('2d');

const W = 800, H = 480;

let state = {
  launches:    [],
  currentIdx:  0,
  _ll2ProbFetched: false,
  weather:     { condition: 'clear', temp_f: 75, wind_speed: 10, wind_dir: 'E', cloud_cover: 0, label: 'Clear sky' },
  settings:    { temp_unit: 'f', time_format: 'utc' },
  // Countdown / launch
  launchTriggered: false,     // ← THE FIX: set true at T-0, reset on new mission
  isLaunching:     false,
  launchFrame:     0,
  rocketY:         340,       // current rocket base Y during launch
  rocketOffscreen: false,
  launchComplete:  false,

  // Rocket flame particles
  flameParticles: [],
  ventParticles:  [],
  flameIntensity: 0,

  // Smoke (pre-launch vent on pad)
  smokeFrame: 0,

  // Clouds
  clouds: [
    { x: 150, y: 60 },
    { x: 420, y: 90 },
    { x: 650, y: 50 },
  ],

  // Birds
  birds: [],

  // Cars
  cars: [],
  gateTimer: 0,
  lastGateOpen: 0,

  // Gator
  gatorTimer: 0,
  gatorPhase: 0,

  // Tower lights
  lightOn: false,
  lightCounter: 0,

  // Post-launch cooldown
  lastFetchAt: Date.now(),
  postLaunchCooldown:   false,
  cooldownEndsAt:       0,
  launchedMissionName:  '',
  nextMissionName:      '',
  nextMissionT0:        null,
  buriedLaunchId: null,

  // Notification banner
  notification: null,

  now: Date.now(),
};

// ─────────────────────────────────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function ts() {
  return new Date().toLocaleTimeString('en-US', { hour12: false });
}

function getHour() { return new Date().getHours(); }

function lerp(a, b, t) { return a + (b - a) * t; }

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return [r, g, b];
}

function lerpColor(c1, c2, t) {
  const [r1,g1,b1] = hexToRgb(c1);
  const [r2,g2,b2] = hexToRgb(c2);
  const r = Math.round(r1 + (r2-r1)*t);
  const g = Math.round(g1 + (g2-g1)*t);
  const b = Math.round(b1 + (b2-b1)*t);
  return `rgb(${r},${g},${b})`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  SKY / TIME-OF-DAY
// ─────────────────────────────────────────────────────────────────────────────
function getSkyColors() {
  const h = getHour();
  const cond = state.weather.condition;
  const isRainy = ['rain','thunderstorm','light_rain'].includes(cond);

  if (isRainy) return { sky:'#3a4a5a', ocean:'#0d1a2e', cloud:'#505050' };
  if (cond === 'cloudy') return { sky:'#7a9ab8', ocean:'#1a5b6e', cloud:'#b0b0b0' };
  if (cond === 'fog')    return { sky:'#8a9aaa', ocean:'#1a5b6e', cloud:'#c0c8d0' };

  if (h >= 10 && h < 16) return { sky:'#87ceeb', ocean:'#1a8b9e', cloud:'#ffffff' };
  if (h >= 16 && h < 18) return { sky:'#ff9933', ocean:'#1a5b6e', cloud:'#ffd9b3' };
  if (h >= 6  && h < 10) return { sky:'#ff9966', ocean:'#2a5b6e', cloud:'#ffe5cc' };
  return { sky:'#0a0a1e', ocean:'#0d1a2e', cloud:'#d0d0d0' };
}

function isNight() { const h = getHour(); return h >= 18 || h < 6; }

// ─────────────────────────────────────────────────────────────────────────────
//  DRAW HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function drawRect(x, y, w, h, fill, stroke, lw=1) {
  ctx.fillStyle = fill;
  ctx.fillRect(x, y, w, h);
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.strokeRect(x, y, w, h); }
}

function drawOval(x, y, rx, ry, fill) {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
}

function roundRectPath(x, y, w, h, r) {
  var tl, tr, br, bl;
  if (Array.isArray(r)) { tl=r[0]||0; tr=r[1]||0; br=r[2]||0; bl=r[3]||0; }
  else { tl=tr=br=bl=r||0; }
  ctx.moveTo(x+tl,y); ctx.lineTo(x+w-tr,y); ctx.quadraticCurveTo(x+w,y,x+w,y+tr);
  ctx.lineTo(x+w,y+h-br); ctx.quadraticCurveTo(x+w,y+h,x+w-br,y+h);
  ctx.lineTo(x+bl,y+h); ctx.quadraticCurveTo(x,y+h,x,y+h-bl);
  ctx.lineTo(x,y+tl); ctx.quadraticCurveTo(x,y,x+tl,y); ctx.closePath();
}

// ─────────────────────────────────────────────────────────────────────────────
//  BACKGROUND
// ─────────────────────────────────────────────────────────────────────────────
function drawBackground() {
  const colors = getSkyColors();

  // Sky
  ctx.fillStyle = colors.sky;
  ctx.fillRect(0, 0, W, 400);

  // Stars (night only)
  if (isNight() && !['cloudy','rain','thunderstorm','fog'].includes(state.weather.condition)) {
    ctx.fillStyle = '#ffffff';
    const rng = mulberry32(42);
    for (let i = 0; i < 60; i++) {
      const sx = rng() * W;
      const sy = rng() * 340;
      const sz = rng() > 0.7 ? 2 : 1;
      ctx.fillRect(sx, sy, sz, sz);
    }
  }

  // Grass
  ctx.fillStyle = '#5a8c3a';
  ctx.fillRect(0, 365, W, BAR_Y - 365);

  // Road
  drawRoad();

  // Pixel grass details
  drawPixelGrass();

  // Bottom info bar background
  ctx.fillStyle = 'rgba(8,8,18,0.97)';
  ctx.fillRect(0, BAR_Y, W, BAR_H);
  ctx.strokeStyle = 'rgba(0,232,122,0.35)';
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(0, BAR_Y); ctx.lineTo(W, BAR_Y); ctx.stroke();
}

function mulberry32(seed) {
  return function() {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function drawRoad() {
  drawRect(0, ROAD_Y, W, 18, '#3a3a3a');
  drawRect(0, ROAD_Y, W, 2,  '#5a5a5a');
  drawRect(0, ROAD_Y+16, W, 2,  '#5a5a5a');
  ctx.fillStyle = '#6a6a3a';
  for (let x = 0; x < W; x += 20) ctx.fillRect(x, ROAD_Y+8, 10, 2);
}

function drawPixelGrass() {
  const rng = mulberry32(123);
  const colors = ['#4a7c2a','#6a9c4a','#5a8c3a','#3a6c1a'];
  for (let i = 0; i < 400; i++) {
    const gx = rng() * W;
    const gy = 368 + rng() * (BAR_Y - 368 - 20);
    ctx.fillStyle = colors[Math.floor(rng() * 4)];
    const style = Math.floor(rng() * 4);
    if (style === 0)      { ctx.fillRect(gx, gy-3, 1, 3); }
    else if (style === 1) { ctx.fillRect(gx, gy, 2, 3); }
    else if (style === 2) { ctx.fillRect(gx, gy, 1, 1); }
    else                  { ctx.fillRect(gx, gy-3, 1, 3); }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  HIF BUILDING
// ─────────────────────────────────────────────────────────────────────────────
function drawHIF() {
  if (!IMG.hif) return;
  const TARGET_HEIGHT = 207;
  const scale = TARGET_HEIGHT / IMG.hif.height;
  const scaledW = Math.round(IMG.hif.width * scale);
  // Default position: left side, sitting on grass. Adjust x/y to reposition.
  ctx.drawImage(IMG.hif, -30, 229, scaledW, 216);
}

// ─────────────────────────────────────────────────────────────────────────────
//  LAUNCH TOWER + PAD
// ─────────────────────────────────────────────────────────────────────────────
function drawLaunchTower() {
  if (IMG.launchTower) {
    const TARGET_HEIGHT = 275;
    const scale = TARGET_HEIGHT / IMG.launchTower.height;
    const scaledW = Math.round(IMG.launchTower.width * scale);
    ctx.drawImage(IMG.launchTower, 454, 153, scaledW, TARGET_HEIGHT);
  }
}

function drawLaunchPad() {
  // Skip - the pad is already included in the tower image
  // Only draw if we have a separate pad asset AND no tower
  if (IMG.launchPad && !IMG.launchTower) {
    ctx.drawImage(IMG.launchPad, 550, 320, 140, 40);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  POND + GATOR
// ─────────────────────────────────────────────────────────────────────────────
function drawPond() {
  drawOval(765, 393, 30, 12, '#2a5a4a');
  ctx.strokeStyle='#1a4a3a'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.ellipse(765,393,30,12,0,0,Math.PI*2); ctx.stroke();
  // Lily pad
  drawOval(755, 390, 4, 3, '#4a7a3a');

  // Gator
  const gp = state.gatorPhase;
  if(gp > 0){
    const gx=790, gy=393;
    const sub = Math.round(8*(1-gp));
    if(gp>0.2){
      drawOval(gx-15, gy+5+Math.round(sub*0.5), 3, 2, '#3a5a3a');
      drawOval(gx-21, gy+7+Math.round(sub*0.5), 3, 2, '#3a5a3a');
    }
    if(gp>0.5){
      drawOval(gx, gy-1+sub, 8, 4, '#3a5a3a');
      drawOval(gx+7, gy+1+sub, 3, 2, '#4a6a4a');
    }
    if(gp>0.3){
      drawOval(gx-4, gy-2+Math.round(sub*0.7), 2, 2, '#ffa500');
      drawOval(gx+1, gy-2+Math.round(sub*0.7), 2, 2, '#ffa500');
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  SPOTLIGHTS
// ─────────────────────────────────────────────────────────────────────────────
function drawSpotlights() {
  const groundY = 370;
  const poleH   = 30;
  const lx      = NOZZLE_X - 90;
  const rx      = NOZZLE_X + 75;
  const targetX = NOZZLE_X;
  const targetY = NOZZLE_Y - 80;
  drawRect(lx + 4, groundY - poleH, 3, poleH, '#505050');
  drawRect(rx + 4, groundY - poleH, 3, poleH, '#505050');
  drawRect(lx,     groundY - poleH - 5, 12, 6, '#404040');
  drawRect(rx,     groundY - poleH - 5, 12, 6, '#404040');
  if (isNight()) {
    ctx.save();
    ctx.globalAlpha = 0.28;
    const g1 = ctx.createLinearGradient(lx+6, groundY-poleH, targetX, targetY);
    g1.addColorStop(0, '#ffffcc'); g1.addColorStop(1, 'rgba(255,255,180,0)');
    ctx.fillStyle = g1;
    ctx.beginPath(); ctx.moveTo(lx+6, groundY-poleH); ctx.lineTo(targetX-18, targetY); ctx.lineTo(targetX+18, targetY); ctx.lineTo(lx+8, groundY-poleH); ctx.fill();
    ctx.globalAlpha = 0.28;
    const g2 = ctx.createLinearGradient(rx+6, groundY-poleH, targetX, targetY);
    g2.addColorStop(0, '#ffffcc'); g2.addColorStop(1, 'rgba(255,255,180,0)');
    ctx.fillStyle = g2;
    ctx.beginPath(); ctx.moveTo(rx+6, groundY-poleH); ctx.lineTo(targetX-18, targetY); ctx.lineTo(targetX+18, targetY); ctx.lineTo(rx+8, groundY-poleH); ctx.fill();
    ctx.globalAlpha = 1; ctx.restore();
    drawRect(lx+3, groundY-poleH-4, 6, 4, '#ffffcc');
    drawRect(rx+3, groundY-poleH-4, 6, 4, '#ffffcc');
  } else {
    drawRect(lx+3, groundY-poleH-4, 6, 4, '#2a2a2a');
    drawRect(rx+3, groundY-poleH-4, 6, 4, '#2a2a2a');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  CLOUDS
// ─────────────────────────────────────────────────────────────────────────────
function drawClouds() {
  const col = getSkyColors().cloud;
  ctx.fillStyle = col;
  state.clouds.forEach(c => {
    ctx.beginPath(); ctx.ellipse(c.x,    c.y+12, 12, 8, 0, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(c.x+20, c.y+7,  12, 9, 0, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(c.x+40, c.y+12, 12, 8, 0, 0, Math.PI*2); ctx.fill();
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  BIRDS
// ─────────────────────────────────────────────────────────────────────────────
function spawnBirds() {
  for(let i=0;i<3;i++){
    state.birds.push({
      x: -100 - i*150, y: 80 + Math.random()*200,
      vx: 0.8 + Math.random()*1.0,
      vy: (Math.random()-0.5)*0.3,
      flap: 0, flapUp: true,
    });
  }
}

function drawBirds() {
  ctx.strokeStyle='#2a2a2a'; ctx.lineWidth=2;
  state.birds.forEach(b => {
    const wing = b.flapUp ? -4 : -1;
    ctx.beginPath();
    ctx.moveTo(b.x,    b.y);
    ctx.lineTo(b.x+4,  b.y+wing);
    ctx.lineTo(b.x+8,  b.y);
    ctx.stroke();
    drawOval(b.x+3, b.y, 1.5, 1, '#2a2a2a');
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  CARS
// ─────────────────────────────────────────────────────────────────────────────
const CAR_COLORS = ['#3a7bc8','#d44444','#f5f5f5','#2a2a2a','#ffd93d','#4a9d5f'];
const GATE_X = 490;
const ROAD_Y = 375;
const BAR_H  = 80;
const BAR_Y  = H - BAR_H;

function spawnCars() {
  for(let i=0;i<6;i++){
    state.cars.push({
      x: -50 - i*80, y: ROAD_Y+6,
      speed: 0.8 + Math.random()*0.4,
      baseSpeed: 0.8 + Math.random()*0.4,
      color: CAR_COLORS[i % CAR_COLORS.length],
      state: 'approaching',
      waitStart: 0,
    });
  }
}

function drawCars() {
  state.cars.forEach(car => {
    const x=car.x, y=car.y;
    ctx.fillStyle = car.color;
    ctx.fillRect(x,y,12,6);
    ctx.fillRect(x+2,y-3,8,3);
    ctx.fillStyle='#add8e6';
    ctx.fillRect(x+3,y-2,2,2);
    ctx.fillRect(x+7,y-2,2,2);
    ctx.fillStyle='#1a1a1a';
    drawOval(x+2.5,y+6,2,2,'#1a1a1a');
    drawOval(x+9.5,y+6,2,2,'#1a1a1a');
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  ROCKET  (PNG or procedural, vehicle-aware)
// ─────────────────────────────────────────────────────────────────────────────
// Rocket position — tuned via Asset Positioner
// Positioner output: ctx.drawImage(IMG.rocket_falcon9, 264, 97, rw, 267)
// top-left x=264, top y=97, height=267 → bottom y=364
// rw at that scale ≈ 80px → center x ≈ 264 + 40 = 304


function getRocketAssetKey(vehicle) {
  if (!vehicle) return 'rocket_generic';
  const v = vehicle.toLowerCase();
  if (v.includes('starship'))  return 'rocket_starship';
  if (v.includes('soyuz'))     return 'rocket_soyuz';
  if (v.includes('ariane'))    return 'rocket_ariane6';
  if (v.includes('sls') || v.includes('space launch system')) return 'rocket_sls';
  if (v.includes('kinetica'))  return 'rocket_kinetica';
  if (v.includes('gslv') || v.includes('geosynchronous')) return 'rocket_gslv';
  if (v.includes('falcon'))    return 'rocket_falcon9';
  if (v.includes('firefly') || v.includes('alpha'))  return 'rocket_firefly';
  if (v.includes('atlas'))                             return 'rocket_atlas';
  if (v.includes('vulcan'))                            return 'rocket_vulcan';
  if (v.includes('electron'))                          return 'rocket_electron';
  if (v.includes('new glenn') || v.includes(' ng'))    return 'rocket_ng';
  if (v.includes('kairos'))                            return 'rocket_kairos';
  if (v.includes('long march') || v.includes('longmarch') || v.includes('chang zheng')) return 'rocket_longmarch';
  return 'rocket_generic';
}

const ROCKET_CONFIG = {
  rocket_falcon9:   { pad: { x: 410, y: 165, h: 200 }, te: { tx: 269, ty: 293, h: 204, offsetY: -102 } },
  rocket_atlas:     { pad: { x: 433, y: 130, h: 250 }, te: { tx: 280, ty: 332, h: 200, offsetY: -100 } },
  rocket_vulcan:    { pad: { x: 315, y: 160, h: 209 }, te: { tx: 264, ty: 374, h: 211, offsetY: -106 } },
  rocket_electron:  { pad: { x: 466, y: 219, h: 158 }, te: { tx: 287, ty: 335, h: 200, offsetY: -100 } },
  rocket_ng:        { pad: { x: 428, y: 114, h: 268 }, te: { tx: 267, ty: 334, h: 229, offsetY: -115 } },
  rocket_kairos:    { pad: { x: 450, y: 173, h: 200 }, te: { tx: 282, ty: 336, h: 185, offsetY:  -93 } },
  rocket_longmarch: { pad: { x: 440, y: 136, h: 234 }, te: { tx: 269, ty: 334, h: 200, offsetY: -100 } },
  rocket_generic:   { pad: { x: 410, y: 165, h: 200 }, te: { tx: 269, ty: 293, h: 204, offsetY: -102 } },
  rocket_firefly:   { pad: { x: 450, y: 193, h: 200 }, te: { tx: 282, ty: 336, h: 185, offsetY:  -93 } },
  rocket_starship:  { pad: { x: 423, y:  92, h: 280 }, te: { tx: 261, ty: 331, h: 242, offsetY: -121 } },
  rocket_soyuz:     { pad: { x: 459, y: 176, h: 177 }, te: { tx: 270, ty: 331, h: 177, offsetY:  -89 } },
  rocket_ariane6:   { pad: { x: 430, y: 140, h: 230 }, te: { tx: 269, ty: 293, h: 204, offsetY: -102 } },
  rocket_sls:       { pad: { x: 433, y:  88, h: 294 }, te: { tx: 277, ty: 334, h: 193, offsetY:  -97 } },
  rocket_kinetica:  { pad: { x: 450, y: 180, h: 190 }, te: { tx: 269, ty: 293, h: 204, offsetY: -102 } },
  rocket_gslv:      { pad: { x: 440, y: 150, h: 220 }, te: { tx: 269, ty: 293, h: 204, offsetY: -102 } },
};
const PAD_Y_BASE = 366;
const NOZZLE_X   = 517;
const NOZZLE_Y   = 340;

function drawTE() {
  if (!IMG.te) return;
  const TARGET_HEIGHT = 135;
  const teScale = TARGET_HEIGHT / IMG.te.height;
  const scaledW = Math.round(IMG.te.width * teScale);
  ctx.drawImage(IMG.te, 167, 288, scaledW, TARGET_HEIGHT);
  const nextLaunch = state.launches[state.currentIdx + 1] || null;
  const vehicle2   = (nextLaunch ? nextLaunch.vehicle : null) || (currentLaunch() ? currentLaunch().vehicle : null) || '';
  const assetKey2  = getRocketAssetKey(vehicle2);
  const rocketImg  = IMG[assetKey2];
  if (!rocketImg) return;
  const cfg    = (ROCKET_CONFIG[assetKey2] || ROCKET_CONFIG.rocket_generic).te;
  const rScale = cfg.h / rocketImg.height;
  const rw2    = Math.round(rocketImg.width * rScale);
  ctx.save();
  ctx.translate(cfg.tx, cfg.ty);
  ctx.rotate(-1.5708);
  ctx.drawImage(rocketImg, -rw2 / 2, cfg.offsetY, rw2, cfg.h);
  ctx.restore();
}

function drawRocket() {
  if (state.rocketOffscreen) return;
  if (state.launchComplete) return;
  if (state.postLaunchCooldown) return;
  const vehicle  = (currentLaunch() ? currentLaunch().vehicle : null) || '';
  const assetKey = getRocketAssetKey(vehicle);
  const launchOffset = state.isLaunching ? state.rocketY - PAD_Y_BASE : 0;
  if (IMG[assetKey]) {
    const img = IMG[assetKey];
    const cfg = (ROCKET_CONFIG[assetKey] || ROCKET_CONFIG.rocket_generic).pad;
    const scale = cfg.h / img.height;
    const rw = Math.round(img.width * scale);
    ctx.drawImage(img, cfg.x, cfg.y + launchOffset, rw, cfg.h);
    return;
  }
  const v = vehicle.toLowerCase();
  if (v.includes('falcon')) drawFalcon9(NOZZLE_X, PAD_Y_BASE + launchOffset);
  else if (v.includes('electron')) drawElectron(NOZZLE_X, PAD_Y_BASE + launchOffset);
  else drawGenericRocket(NOZZLE_X, PAD_Y_BASE + launchOffset);
}

function drawGenericRocket(x, y) {
  // Simple white cylinder rocket
  drawRect(x-8, y-100, 16, 100, '#f0f0f0', '#aaaaaa', 1);
  ctx.fillStyle='#e0e0e0';
  ctx.beginPath(); ctx.moveTo(x-8,y-100); ctx.lineTo(x,y-120); ctx.lineTo(x+8,y-100); ctx.fill();
  drawRect(x-10, y-15, 20, 6, '#888888');  // engine section
}

function drawFalcon9(x, y) {
  // Simplified Phase-1-faithful Falcon 9
  drawRect(x-8,  y-95,  16, 83, '#f5f5f5', '#000000', 1);
  drawRect(x+5,  y-95,  3,  83, '#d5d5d5');
  drawRect(x-8,  y-102, 16, 7,  '#1a1a1a', '#000000', 1);
  drawRect(x-7,  y-125, 14, 23, '#f5f5f5', '#000000', 1);
  ctx.fillStyle='#f5f5f5';
  ctx.beginPath(); ctx.moveTo(x-7,y-125); ctx.lineTo(x,y-140); ctx.lineTo(x+7,y-125); ctx.fill();
  drawRect(x-10, y-12,  5,  18, '#2a2a2a');
  drawRect(x+5,  y-12,  5,  18, '#2a2a2a');
  drawRect(x-11, y-92,  3,  5,  '#2a2a2a');
  drawRect(x+8,  y-92,  3,  5,  '#2a2a2a');
  // Engines
  for(let i=-1;i<=1;i++) drawOval(x+i*4, y-7, 2, 3, '#1a1a1a');
}

function drawStarship(x, y) {
  const sc=1.4;
  drawRect(x-Math.round(12*sc), y-Math.round(120*sc), Math.round(24*sc), Math.round(120*sc), '#c0c0c0', '#888888', 1);
  drawRect(x-Math.round(12*sc), y-Math.round(220*sc), Math.round(24*sc), Math.round(100*sc), '#d0d0d0', '#888888', 1);
  ctx.fillStyle='#b0b0b0';
  ctx.beginPath();
  ctx.moveTo(x-Math.round(12*sc), y-Math.round(220*sc));
  ctx.lineTo(x, y-Math.round(240*sc));
  ctx.lineTo(x+Math.round(12*sc), y-Math.round(220*sc));
  ctx.fill();
}

function drawElectron(x, y) {
  drawRect(x-5, y-80, 10, 80, '#1a1a1a', '#333333', 1);
  ctx.fillStyle='#1a1a1a';
  ctx.beginPath(); ctx.moveTo(x-5,y-80); ctx.lineTo(x,y-95); ctx.lineTo(x+5,y-80); ctx.fill();
  drawRect(x-6, y-12, 12, 8, '#333333');
}

// ─────────────────────────────────────────────────────────────────────────────
//  PRE-LAUNCH VENT SMOKE
// ─────────────────────────────────────────────────────────────────────────────
function drawSmoke() {
  if (state.isLaunching) return;
  if (!currentLaunch()) return;
  if (state.launchComplete) return;
  if (state.postLaunchCooldown) return;
  const vehicle  = (currentLaunch() ? currentLaunch().vehicle : null) || '';
  const assetKey = getRocketAssetKey(vehicle);
  const cfg      = (ROCKET_CONFIG[assetKey] || ROCKET_CONFIG.rocket_generic).pad;
  const ventX    = NOZZLE_X;
  const ventY    = cfg.y + cfg.h * 0.5;
  const f        = state.smokeFrame;

  for(let i=0;i<12;i++){
    const dist    = (f*0.5 + i*6) % 100;
    const smx     = ventX - dist;
    const smy     = ventY + dist*0.08 + (i%3-1)*2;
    const opacity = 1 - dist/100;
    if(opacity > 0.08){
      const sz = dist < 20 ? 4 + i%3 : 4 + i%3 + Math.floor(dist/6);
      const gray = dist < 20 ? 245 : 220;
      ctx.globalAlpha = opacity * 0.7;
      ctx.fillStyle = `rgb(${gray},${gray},${gray})`;
      ctx.beginPath();
      ctx.ellipse(smx, smy, sz/2, sz/2, 0, 0, Math.PI*2);
      ctx.fill();
    }
  }
  ctx.globalAlpha = 1;
}

// ─────────────────────────────────────────────────────────────────────────────
//  LAUNCH FLAME PARTICLES
// ─────────────────────────────────────────────────────────────────────────────
const FLAME_COLORS = {
  core:  ['#ffffff','#ffffcc','#ffff88','#ffdd44'],
  mid:   ['#ffcc00','#ffaa00','#ff8800','#ff6600'],
  outer: ['#ff6600','#ff4400','#dd2200','#aa1100'],
};

function spawnFlameParticles(flameX, flameY, intensity) {
  const n = Math.floor(20 * intensity);
  for(let i=0;i<n;i++){
    state.flameParticles.push({
      x:   flameX + (Math.random()-0.5)*16,
      y:   flameY,
      vx:  (Math.random()-0.5)*1,
      vy:  2.0 + Math.random()*2.5,
      age: 0,
      life: 12 + Math.floor(Math.random()*13),
      size: 3 + Math.random()*5,
      type: Math.random()<0.5 ? 'core' : Math.random()<0.5 ? 'mid' : 'outer',
    });
  }
}

function drawFlameParticles() {
  state.flameParticles = state.flameParticles.filter(p => p.age < p.life);
  state.flameParticles.forEach(p => {
    const t = p.age / p.life;
    const cols = FLAME_COLORS[p.type];
    const ci = Math.min(Math.floor(t * cols.length), cols.length-1);
    if(t > 0.85 && Math.random() > 0.7) return;
    const sz = p.size * (1.2 - t*0.8);
    const wx = Math.sin(p.age*0.3)*1.5;
    const wy = Math.cos(p.age*0.4)*0.8;
    ctx.fillStyle = cols[ci];
    ctx.beginPath();
    ctx.ellipse(p.x+wx, p.y+wy, sz/2, sz/2, 0, 0, Math.PI*2);
    ctx.fill();
    p.age++; p.x += p.vx; p.y += p.vy;
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  COUNTDOWN UI
// ─────────────────────────────────────────────────────────────────────────────
function drawCountdown() {
  const launch = currentLaunch();
  if (!launch) return;
  const cd = computeCountdown(launch.t0);
  const vals = (cd && cd !== 'LAUNCHED') ? [cd.days, cd.hours, cd.minutes, cd.seconds] : [0,0,0,0];
  const LABELS = ['DAYS','HOURS','MINS','SECS'];

  const BW = 80, BH = 80, GAP = 7;
  const TOTAL_W = 4*BW + 3*GAP;
  const BX = Math.round((W - TOTAL_W) / 2);
  const BY = 8;

  // Dark bar background
  ctx.fillStyle = 'rgba(20,20,28,0.88)';
  ctx.beginPath(); roundRectPath(BX-16, BY-6, TOTAL_W+32, BH+30, 5); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.07)'; ctx.lineWidth=1; ctx.stroke();

  // T-MINUS label
  ctx.fillStyle='rgba(255,255,255,0.25)';
  ctx.font='bold 7px Courier New'; ctx.textAlign='center';
  ctx.fillText('T  —  M I N U S', BX+TOTAL_W/2, BY+2);

  if (cd === 'LAUNCHED' || state.postLaunchCooldown) {
    ctx.fillStyle='#ff4444'; ctx.shadowColor='#ff2200'; ctx.shadowBlur=10;
    ctx.font='bold 30px Courier New'; ctx.textAlign='center';
    ctx.fillText('LAUNCHED', BX+TOTAL_W/2, BY+BH/2+4);
    ctx.shadowBlur=0;
    if (state.postLaunchCooldown) {
      const remSec = Math.max(0, Math.floor((state.cooldownEndsAt - Date.now()) / 1000));
      const remM = Math.floor(remSec / 60), remS = remSec % 60;
      ctx.fillStyle = 'rgba(255,255,255,0.55)';
      ctx.font = 'bold 11px Courier New';
      ctx.fillText('NEXT ROCKET ON STAND IN  ' + remM + ':' + String(remS).padStart(2,'0'), BX+TOTAL_W/2, BY+BH-4);
    }
    return;
  }
  if (!cd) {
    ctx.fillStyle='#ffd93d'; ctx.font='bold 9px Courier New'; ctx.textAlign='center';
    ctx.fillText('LAUNCH TIME TBD', BX+TOTAL_W/2, BY+BH/2+10); return;
  }

  LABELS.forEach((lbl, i) => {
    const bx = BX + i*(BW+GAP);
    const by = BY + 10;

    // Plastic body
    ctx.fillStyle='#c8d4e0'; ctx.fillRect(bx, by, BW, BH);
    // Bevels
    ctx.fillStyle='#e2ecf4'; ctx.fillRect(bx, by, BW, 2); ctx.fillRect(bx, by, 2, BH);
    ctx.fillStyle='#8a9db0'; ctx.fillRect(bx, by+BH-2, BW, 2); ctx.fillRect(bx+BW-2, by, 2, BH);
    ctx.strokeStyle='#6080a0'; ctx.lineWidth=1; ctx.strokeRect(bx+0.5, by+0.5, BW-1, BH-1);

    // LCD screen
    const px=7, py=6, sw=BW-14, sh=BH-py*2-16;
    const sx=bx+px, sy=by+py;
    ctx.fillStyle='#12202e'; ctx.fillRect(sx, sy, sw, sh);
    ctx.strokeStyle='#1e3048'; ctx.lineWidth=1; ctx.strokeRect(sx+0.5, sy+0.5, sw-1, sh-1);

    // Segment ghost lines
    ctx.strokeStyle='rgba(50,90,130,0.45)'; ctx.lineWidth=1; ctx.setLineDash([2,3]);
    const hw=(sw-4)/2;
    ctx.strokeRect(sx+2, sy+2, hw-1, sh-4);
    ctx.strokeRect(sx+2+hw+1, sy+2, hw-1, sh-4);
    ctx.beginPath();
    ctx.moveTo(sx+2, sy+2+(sh-4)/2); ctx.lineTo(sx+2+hw-1, sy+2+(sh-4)/2);
    ctx.moveTo(sx+2+hw+1, sy+2+(sh-4)/2); ctx.lineTo(sx+2+hw*2+1, sy+2+(sh-4)/2);
    ctx.stroke(); ctx.setLineDash([]);

    // Green digit — centred both axes inside the LCD screen
    // Gradually shift color based on time remaining
    const secs = cd.total_seconds;
    let digitColor;
    if (secs > 3600) {
      digitColor = '#00e87a';
    } else if (secs > 1800) {
      digitColor = '#ffd93d';
    } else {
      digitColor = '#ff4422';
    }
    ctx.shadowColor = digitColor;
    ctx.shadowBlur = 9;
    ctx.fillStyle = digitColor;
    ctx.font='bold 32px Courier New';
    ctx.textAlign='center';
    ctx.textBaseline='middle';
    ctx.fillText(String(vals[i]).padStart(2,'0'), sx + sw/2, sy + sh/2);
    ctx.textBaseline='alphabetic';
    ctx.shadowBlur=0;

    // Label
    ctx.fillStyle='#4a7aaa'; ctx.font='bold 7px Courier New'; ctx.textAlign='center';
    ctx.fillText(lbl, bx+BW/2, by+BH-3);
  });
}


// ─────────────────────────────────────────────────────────────────────────────
//  BOTTOM INFO BAR
// ─────────────────────────────────────────────────────────────────────────────
function drawInfoBar() {

  return;
  const BY = BAR_Y, BH = BAR_H, IX = 20;

  if (state.postLaunchCooldown) {
    ctx.fillStyle = '#ff6644'; ctx.font = 'bold 14px monospace'; ctx.textAlign = 'left';
    ctx.fillText('LAUNCHED:', IX, BY + 24);
    const lw = ctx.measureText('LAUNCHED:').width;
    ctx.fillStyle = '#ffffff';
    ctx.fillText('  ' + state.launchedMissionName, IX + lw, BY + 24);
    if (state.nextMissionName) {
      let tStr = '';
      if (state.nextMissionT0) {
        const cd2 = computeCountdown(state.nextMissionT0);
        if (cd2 && cd2 !== 'LAUNCHED') {
          tStr = cd2.days > 0
            ? 'T−' + cd2.days + 'd ' + String(cd2.hours).padStart(2,'0') + ':' + String(cd2.minutes).padStart(2,'0') + ':' + String(cd2.seconds).padStart(2,'0')
            : 'T−' + String(cd2.hours).padStart(2,'0') + ':' + String(cd2.minutes).padStart(2,'0') + ':' + String(cd2.seconds).padStart(2,'0');
        }
      }
      ctx.fillStyle = 'rgba(255,255,255,0.45)'; ctx.font = '12px monospace';
      ctx.fillText('UPCOMING:', IX, BY + 50);
      const uw = ctx.measureText('UPCOMING:').width;
      ctx.fillStyle = '#ffd93d';
      ctx.fillText('  ' + state.nextMissionName, IX + uw, BY + 50);
      if (tStr) {
        ctx.fillStyle = '#00e87a'; ctx.font = 'bold 12px monospace';
        const nw = ctx.measureText('  ' + state.nextMissionName).width;
        ctx.fillText('  IN ' + tStr, IX + uw + nw, BY + 50);
      }
    }
    return;
  }
  const launch = currentLaunch();
  if (!launch) {
    ctx.fillStyle = 'rgba(255,100,50,0.7)';
    ctx.font = 'bold 13px monospace';
    ctx.textAlign = 'left';
    ctx.fillText('NO LAUNCH DATA', 20, BAR_Y + 24);
    ctx.fillStyle = 'rgba(255,255,255,0.25)';
    ctx.font = '11px monospace';
    ctx.fillText('Check network connection or API status', 20, BAR_Y + 46);
    return;
  }
  const statusColors = { 'Go':'#00e87a','Go for Launch':'#00e87a','TBD':'#ffd93d','To Be Determined':'#ffd93d','To Be Confirmed':'#ffd93d' };
  const statusCol = statusColors[launch.status] || '#4a9ede';
  const formatT0 = t0 => {
    if (!t0) return { date:'TBD', time:'' };
    try {
      const useLocal = localStorage.getItem('lt_time_format') === 'local';
      const tz = useLocal ? undefined : 'UTC';
      const tzLabel = useLocal ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'UTC';
      const d = new Date(t0);
      return {
        date: d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:tz}),
        time: d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz}) + ' ' + (useLocal ? 'LOCAL' : 'UTC'),
      };
    } catch(e) { return { date:t0, time:'' }; }
  };
  const shorten = s => (s||'').replace('Space Launch Complex','SLC').replace('Launch Complex','LC')
    .replace('Space Force Station','SFS').replace('Kennedy Space Center','KSC')
    .replace('Cape Canaveral','CC').replace('Vandenberg Space Force Base','VSFB');
  const lt = formatT0(launch.t0 || launch.win_open);
  const availW = W - IX - 100;
  ctx.fillStyle = '#ffffff'; ctx.font = 'bold 22px monospace'; ctx.textAlign = 'left';
  let missionName = launch.name || 'Unknown';
  while (ctx.measureText(missionName).width > availW && missionName.length > 4) missionName = missionName.slice(0,-1);
  ctx.fillText(missionName, IX, BY + 24);

  // Tap hint inline next to mission name
  const nameWidth = ctx.measureText(missionName).width;
  ctx.fillStyle = 'rgba(0,232,122,0.5)';
  ctx.font = 'bold 11px Courier New';
  ctx.textAlign = 'left';
  ctx.fillText('  TAP FOR DETAILS →', IX + nameWidth, BY + 24);
  const dateStr = lt.date + (lt.time ? '  ·  ' + lt.time : '');
  const vehStr  = (launch.vehicle||'') + '  ·  ' + (launch.provider||'') + '  ·  ' + shorten(launch.pad||launch.location||'');
  ctx.fillStyle = '#ffd93d'; ctx.font = '13px monospace';
  ctx.fillText(dateStr, IX, BY + 44);
  const dw = ctx.measureText(dateStr).width;
  ctx.fillStyle = '#4a9ede';
  ctx.fillText('  ·  ' + vehStr, IX + dw, BY + 44);
  const badgeW = 80, badgeH = 26, badgeX = W - badgeW - 14, badgeY = BY + 12;
  ctx.fillStyle = statusCol + '28';
  ctx.beginPath(); roundRectPath(badgeX, badgeY, badgeW, badgeH, 4); ctx.fill();
  ctx.strokeStyle = statusCol; ctx.lineWidth = 2; ctx.stroke();
  ctx.fillStyle = statusCol; ctx.font = 'bold 12px monospace'; ctx.textAlign = 'center';
  ctx.fillText((launch.status||'TBD').toUpperCase(), badgeX + badgeW/2, badgeY + 17);
  const minAgo = Math.floor((Date.now() - state.lastFetchAt) / 60000);
  ctx.fillStyle = 'rgba(255,255,255,0.18)';
  ctx.font = '9px monospace';
  ctx.textAlign = 'right';
  ctx.fillText('v2.0.0  ·  data ' + minAgo + 'm ago', W - 130, BAR_Y + BAR_H - 35);
}

function updateInfoBar() {

  // Post-launch cooldown state
  if (state.postLaunchCooldown) {
    document.getElementById('ib-name').textContent = 'LAUNCHED: ' + state.launchedMissionName;
    document.getElementById('ib-badge').textContent = '✓';
    document.getElementById('ib-badge').className = 'go';
    document.getElementById('ib-sub').textContent = state.nextMissionName ? 'UPCOMING: ' + state.nextMissionName : '—';
    document.getElementById('ib-cd').textContent = '—';
    document.getElementById('ib-tap').onclick = null;
    return;
  }

  const launch = currentLaunch();
  if (!launch) {
    document.getElementById('ib-name').textContent = 'NO LAUNCH DATA';
    document.getElementById('ib-badge').textContent = '—';
    document.getElementById('ib-sub').textContent = 'Check network connection or API status';
    document.getElementById('ib-cd').textContent = '—';
    return;
  }

  // Name
  const fullName = launch.name || '—';
  const nameEl = document.getElementById('ib-name');
  nameEl.textContent = fullName;
  nameEl.style.fontSize = fullName.length > 30 ? '16px' : fullName.length > 22 ? '18px' : '20px';

  // Badge
  const badge = document.getElementById('ib-badge');
  const sl = (launch.status||'').toLowerCase();
  if (sl.includes('go')) { badge.textContent='GO'; badge.className='go'; }
  else if (sl.includes('hold')) { badge.textContent='HOLD'; badge.className='hold'; }
  else { badge.textContent=(launch.status||'TBD').toUpperCase(); badge.className=''; }

  // Sub line — vehicle · provider · pad (shortened)
  const shorten = s => (s||'').replace('Space Launch Complex','SLC').replace('Launch Complex','LC')
    .replace('Space Force Station','SFS').replace('Kennedy Space Center','KSC')
    .replace('Cape Canaveral','CC').replace('Vandenberg Space Force Base','VSFB');
  document.getElementById('ib-sub').textContent =
    (launch.vehicle||'') + ' · ' + (launch.provider||'') + ' · ' + shorten(launch.pad||'');

  // Location — city/state from launch.location
  const locShorten = s => (s||'')
    .replace('Cape Canaveral, Florida, USA','Cape Canaveral, FL')
    .replace('Vandenberg Space Force Base, California, USA','Vandenberg, CA')
    .replace('Kennedy Space Center, Florida, USA','Kennedy SC, FL')
    .replace('Boca Chica, Texas, USA','Boca Chica, TX')
    .replace('Mahia Peninsula, New Zealand','Mahia, NZ')
    .replace('Wallops Island, Virginia, USA','Wallops Island, VA')
    .replace(', USA','').replace(', United States','');
  document.getElementById('ib-location').textContent = locShorten(launch.location||'');

  // Tap hint
  document.getElementById('ib-tap').onclick = () => {
    window.location = `http://localhost:5001/mission?id=${launch.id}&name=${encodeURIComponent(launch.name||'')}`;
  };

  // Date + countdown (hidden elements kept for compat)
  const useLocal = state.settings?.time_format === 'local';
  const tz = useLocal ? undefined : 'UTC';
  const t0 = launch.t0 || launch.win_open;
  if (t0) {
    const d = new Date(t0);
    document.getElementById('ib-date').textContent =
      d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:tz}) + ' · ' +
      d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz,hour12:false}) +
      (useLocal ? ' LOCAL' : ' UTC');
    // T-0 display in new detail row
    const t0Label = d.toLocaleDateString('en-US',{day:'numeric',month:'short',timeZone:tz}).toUpperCase()
      + ' · ' + d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz,hour12:false})
      + (useLocal ? ' LOCAL' : ' UTC');
    document.getElementById('ib-t0').textContent = t0Label;
    const cd = computeCountdown(t0);
    if (cd && cd !== 'LAUNCHED') {
      const {days,hours,minutes,seconds} = cd;
      const hh=String(hours).padStart(2,'0'), mm=String(minutes).padStart(2,'0'), ss=String(seconds).padStart(2,'0');
      document.getElementById('ib-cd').textContent = days>0 ? `T− ${days}d ${hh}:${mm}:${ss}` : `T− ${hh}:${mm}:${ss}`;
    } else if (cd === 'LAUNCHED') {
      document.getElementById('ib-cd').textContent = 'LAUNCHED';
      document.getElementById('ib-cd').style.color = '#4a9ede';
    }
    const winOpen = launch.win_open || t0;
    if (winOpen) {
      document.getElementById('ib-win-open').textContent =
        new Date(winOpen).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz,hour12:false});
    }
    // win_close not in API so just show — for now
    const winCloseEl = document.getElementById('ib-win-close');
    winCloseEl.textContent = '—:—';

    // T-0 dot position on window track
    // If we have win_open and t0, place dot proportionally
    // For instantaneous windows dot sits at left edge (0%)
    const dotEl = document.getElementById('ib-win-dot');
    if (dotEl && winOpen && t0 && winOpen !== t0) {
      const openMs = new Date(winOpen).getTime();
      const t0Ms   = new Date(t0).getTime();
      // Assume 2hr window max for scaling if no close time
      const windowMs = 2 * 3600 * 1000;
      const pct = Math.min(100, Math.max(0, (t0Ms - openMs) / windowMs * 100));
      dotEl.style.left = pct + '%';
    } else if (dotEl) {
      dotEl.style.left = '0%';
    }
  }

  // Weather
  const wx = state.weather;
  if (wx) {
    const useCelsius = state.settings?.temp_unit === 'c';
    document.getElementById('ib-temp').textContent   = useCelsius ? Math.round(wx.temp_c)+'°C' : Math.round(wx.temp_f)+'°F';
    document.getElementById('ib-wind').textContent   = Math.round(wx.wind_speed)+' '+(wx.wind_dir||'');
    document.getElementById('ib-cloud').textContent  = (wx.cloud_cover||0)+'%';
    document.getElementById('ib-precip').textContent = (wx.precip||0).toFixed(1)+'"';
  }
    // Version + data age
  const minAgo = Math.floor((Date.now() - state.lastFetchAt) / 60000);
  document.getElementById('ib-ver').textContent = `v1.0.0 · data ${minAgo}m ago`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  UPDATE NOTIFICATION  (slides in from right like Phase 1)
// ─────────────────────────────────────────────────────────────────────────────
function showNotification(text) {
  state.notification = { text, alpha: 1, offset: 200, sliding: true };
}

function drawNotification() {
  if (!state.notification) return;
  const n = state.notification;
  const nx = 800 - (200 - n.offset);   // slides in
  drawRect(nx-140, 10, 140, 30, '#2a2a2a', '#4a90e2', 2);
  drawOval(nx-130, 25, 4, 4, '#00ff88');
  ctx.fillStyle='#ffffff'; ctx.font='bold 8px Courier New'; ctx.textAlign='center';
  ctx.fillText('DATA UPDATED', nx-68, 22);
  ctx.fillStyle='#aaaaaa'; ctx.font='7px Courier New';
  ctx.fillText(ts(), nx-68, 33);
}

// ─────────────────────────────────────────────────────────────────────────────
//  COUNTDOWN COMPUTATION  (runs locally from server-provided t0)
// ─────────────────────────────────────────────────────────────────────────────
function computeCountdown(t0) {
  if (!t0) return null;
  try {
    const launch = new Date(t0);
    const now    = new Date();
    const diffMs = launch - now;
    if (diffMs < 0) return 'LAUNCHED';
    const totalSec = Math.floor(diffMs / 1000);
    const days    = Math.floor(totalSec / 86400);
    const hours   = Math.floor((totalSec % 86400) / 3600);
    const minutes = Math.floor((totalSec % 3600) / 60);
    const seconds = totalSec % 60;
    return { days, hours, minutes, seconds, total_seconds: totalSec };
  } catch(e) { return null; }
}

// ─────────────────────────────────────────────────────────────────────────────
//  LAUNCH SEQUENCE  (T-0 trigger with single-fire guard)
// ─────────────────────────────────────────────────────────────────────────────
function checkLaunchTrigger() {
  if (state.launchTriggered || state.isLaunching) return;

  const launch = currentLaunch();
  if (!launch || !launch.t0) return;

  const cd = computeCountdown(launch.t0);

  if (cd === 'LAUNCHED') {
  const launchTime = new Date(launch.t0).getTime();
  const minsAgo = (Date.now() - launchTime) / 60000;

  if (minsAgo > 30) {
    console.log(`[${ts()}] Stale launch (${Math.floor(minsAgo)}m ago) — burying and skipping`);
    state.launchTriggered = true;
    state.buriedLaunchId  = launch.id;
    fetchLaunches(true);
    return;
  }

  console.log(`[${ts()}] Missed launch detected — starting cooldown`);
  state.launchTriggered     = true;
  state.launchComplete      = true;
  state.rocketOffscreen     = true;
  state.buriedLaunchId      = launch.id;
  state.launchedMissionName = launch.name || '';
  state.postLaunchCooldown  = true;
  state.cooldownEndsAt      = Date.now() + 10 * 60 * 1000;
  fetch('/api/launches').then(r => r.json()).then(data => {
    const all = data.launches || [];
    const next = all.find(l => l.id !== launch.id) || all[1] || all[0];
    state.nextMissionName = next ? (next.name || '') : '';
    state.nextMissionT0   = next ? (next.t0 || null) : null;
  }).catch(() => {});
  return;
}

  if (!cd) return;

  // Fire at T-0 (within a 3-second window)
  if (cd.total_seconds <= 3 && cd.total_seconds >= 0) {
    console.log(`[${ts()}] T-0! Ignition sequence start`);
    state.launchTriggered = true;   // ← prevents re-trigger every second
    startLaunchAnimation();
  }
}

function startLaunchAnimation() {
  state.isLaunching    = true;
  state.launchFrame    = 0;
  state.rocketY        = PAD_Y_BASE;
  state.flameParticles = [];
  state.ventParticles  = [];
  state.flameIntensity = 0;
  state.rocketOffscreen = false;
}

function updateLaunch() {
  if (!state.isLaunching) return;

  state.launchFrame++;

  // Phase 1: ignition build-up (150 frames ≈ 5s at 30fps)
  if (state.launchFrame < 150) {
    state.flameIntensity = state.launchFrame / 150;
  } else {
    // Phase 2: liftoff
    const vel = Math.min(0.08 * (state.launchFrame - 150) * 0.5, 4);
    state.rocketY -= vel;

    if (state.rocketY < -200) {
      state.isLaunching    = false;
      state.rocketOffscreen = true;
      state.launchComplete  = true;
      state.flameParticles  = [];
      const _launched           = currentLaunch();
      state.buriedLaunchId      = _launched ? _launched.id : null;  
      state.launchedMissionName = _launched ? (_launched.name || '') : '';
      state.postLaunchCooldown  = true;
      state.cooldownEndsAt      = Date.now() + 10 * 60 * 1000;
      if (!state.testMode) {
        fetch('/api/launches/invalidate', { method: 'POST' })
          .then(() => fetch('/api/launches')).then(r => r.json())
          .then(data => {
            const all = data.launches || [];
            const prevId = _launched ? _launched.id : null;
            const next = all.find(l => l.id !== prevId) || all[1] || all[0];
            state.nextMissionName = next ? (next.name || '') : '';
            state.nextMissionT0   = next ? (next.t0 || null) : null;
          }).catch(() => {});
      } else {
        fetch('/api/launches').then(r => r.json()).then(data => {
          const all = data.launches || [];
          const prevId = _launched ? _launched.id : null;
          const next = all.find(l => l.id !== prevId) || all[1] || all[0];
          state.nextMissionName = next ? (next.name || '') : '';
          state.nextMissionT0   = next ? (next.t0 || null) : null;
        }).catch(() => {});
      }
    }
  }

  const flameX = NOZZLE_X;
  const flameY = NOZZLE_Y + (state.rocketY - PAD_Y_BASE) + 8;
  if (state.flameIntensity > 0) {
    spawnFlameParticles(flameX, flameY, state.flameIntensity);
  }
}

function drawNoSignal() {
  if (Date.now() - state.lastFetchAt < 15 * 60 * 1000) return;
  // Small L.O.S indicator under the countdown clock
  const cx = W / 2;
  const by = 108; // just below the countdown box
  ctx.fillStyle = 'rgba(255,68,34,0.7)';
  ctx.font = 'bold 9px Courier New';
  ctx.textAlign = 'center';
  ctx.fillText('L.O.S', cx, by);
  const minAgo = Math.floor((Date.now() - state.lastFetchAt) / 60000);
  ctx.fillStyle = 'rgba(255,255,255,0.2)';
  ctx.font = '8px Courier New';
  ctx.fillText('signal lost · ' + minAgo + 'm ago', cx, by + 12);
}

// ─────────────────────────────────────────────────────────────────────────────
//  DATA FETCHING
// ─────────────────────────────────────────────────────────────────────────────
function currentLaunch() {
  return state.launches[state.currentIdx] || null;
}

async function fetchLaunches(afterLaunch=false) {
  try {
    const res  = await fetch('/api/launches');
    const data = await res.json();
    const _cl = currentLaunch(); const prev = _cl ? _cl.id : undefined;

    const newLaunches = data.launches || [];
    if (newLaunches.length === 0 && state.launches.length > 0) return;
    state.launches = newLaunches;
    state.lastFetchAt = Date.now();

    if (afterLaunch) {
      const newLaunch = state.launches.find(l => l.id !== state.buriedLaunchId) || state.launches[0];
      state.currentIdx      = newLaunch ? state.launches.indexOf(newLaunch) : 0;
      state.launchTriggered = false;
      state.isLaunching     = false;
      state.rocketOffscreen = false;
      state.launchComplete  = false;
      state.rocketY         = PAD_Y_BASE;
      state.flameParticles  = [];
      showNotification('NEXT MISSION');
    } else {
      // Skip buried launch on every regular poll
      const firstValid = state.launches.findIndex(l => l.id !== state.buriedLaunchId);
      state.currentIdx = firstValid >= 0 ? firstValid : 0;
    }
  } catch(e) {
    console.error('Launch fetch error:', e);
  }
}

async function fetchWeather() {
  try {
    const res  = await fetch('/api/weather');
    state.weather = await res.json();
  } catch(e) {
    console.error('Weather fetch error:', e);
  }
}

async function fetchSettings() {
  try {
    const r = await fetch('/api/settings');
    state.settings = await r.json();
  } catch(e) {}
}

// ─────────────────────────────────────────────────────────────────────────────
//  ANIMATION UPDATES
// ─────────────────────────────────────────────────────────────────────────────
function updateClouds() {
  state.clouds.forEach(c => {
    c.x += 0.3;
    if (c.x > 900) c.x = -60;
  });
}

function updateBirds() {
  state.birds.forEach(b => {
    b.flap++;
    if(b.flap >= 8){ b.flap=0; b.flapUp=!b.flapUp; }
    b.x += b.vx; b.y += b.vy;
    if(b.y<60||b.y>300) b.vy*=-1;
    if(b.x>860){
      b.x=-50;
      b.y=80+Math.random()*200;
      b.vx=0.8+Math.random()*1;
      b.vy=(Math.random()-0.5)*0.3;
    }
  });
}

function updateCars() {
  const now = Date.now();
  // Open gate every 3 seconds
  if (now - state.lastGateOpen >= 3000) {
    state.lastGateOpen = now;
    const waiting = state.cars.find(c => c.state === 'waiting');
    if (waiting) { waiting.state = 'entering'; waiting.waitStart = now; }
  }

  state.cars.forEach(car => {
    if (car.state === 'approaching') {
      const ahead = state.cars.filter(c =>
        (c.state === 'waiting' || c.state === 'approaching') &&
        c.x < car.x && c.x > car.x - 100
      );
      if (ahead.length) {
        const closest = ahead.reduce((a,b) => a.x>b.x?a:b);
        if (car.x >= closest.x - 15) { car.state='waiting'; return; }
      }
      if (car.x >= GATE_X - 20) { car.state='waiting'; return; }
      car.x += car.baseSpeed;
    } else if (car.state === 'entering') {
      if (now - car.waitStart < 2000) car.x += car.baseSpeed;
      else car.state = 'driving';
    } else if (car.state === 'driving') {
      car.x += car.baseSpeed;
      if (car.x > 860) {
        car.x = -50;
        car.baseSpeed = 0.8 + Math.random()*0.4;
        car.state = 'approaching';
      }
    }
  });
}

function updateGator() {
  state.gatorTimer++;
  if (state.gatorTimer < 25) {
    state.gatorPhase = 0;
  } else if (state.gatorTimer < 30) {
    state.gatorPhase = (state.gatorTimer - 25) / 5;
  } else if (state.gatorTimer < 50) {
    state.gatorPhase = 1;
  } else if (state.gatorTimer < 55) {
    state.gatorPhase = 1 - (state.gatorTimer - 50) / 5;
  } else {
    state.gatorPhase = 0;
    if (state.gatorTimer > 90) state.gatorTimer = 0;
  }
}

function updateTowerLights() {
  state.lightCounter++;
  if (state.lightCounter >= 30) {
    state.lightCounter = 0;
    state.lightOn = !state.lightOn;
  }
}

function updateNotification() {
  if (!state.notification) return;
  const n = state.notification;
  if (n.sliding && n.offset > 0) {
    n.offset = Math.max(0, n.offset - 8);
  } else {
    n.sliding = false;
    n.alpha  -= 0.008;
    if (n.alpha <= 0) state.notification = null;
  }
}

function updateSmoke() {
  state.smokeFrame = (state.smokeFrame + 1) % 1000;
}

function drawWifiIcon() {
  const x = W - 36, y = 16;
  const connected = Date.now() - state.lastFetchAt < 20 * 60 * 1000;
  const col = connected ? '#00e87a' : '#ff4422';
  
  ctx.strokeStyle = col;
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  
  // Dot
  ctx.fillStyle = col;
  drawOval(x, y + 18, 2, 2, col);
  
  // Arc 1 (small)
  ctx.beginPath();
  ctx.arc(x, y + 18, 6, Math.PI * 1.25, Math.PI * 1.75);
  ctx.stroke();
  
  // Arc 2 (medium)
  ctx.beginPath();
  ctx.arc(x, y + 18, 11, Math.PI * 1.2, Math.PI * 1.8);
  ctx.stroke();
  
  // Arc 3 (large)
  ctx.beginPath();
  ctx.arc(x, y + 18, 16, Math.PI * 1.15, Math.PI * 1.85);
  ctx.stroke();
}

function drawGearIcon() {
  const x = W - 20, y = 16;
  const col = 'rgba(255,255,255,0.4)';
  ctx.strokeStyle = col;
  ctx.lineWidth = 1.5;
  ctx.lineCap = 'round';
  // Outer circle
  ctx.beginPath();
  ctx.arc(x, y + 10, 5, 0, Math.PI * 2);
  ctx.stroke();
  // Teeth
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i;
    const ix = x + Math.cos(a) * 5;
    const iy = y + 10 + Math.sin(a) * 5;
    const ox = x + Math.cos(a) * 8;
    const oy = y + 10 + Math.sin(a) * 8;
    ctx.beginPath();
    ctx.moveTo(ix, iy);
    ctx.lineTo(ox, oy);
    ctx.stroke();
  }
  // Center dot
  ctx.fillStyle = col;
  ctx.beginPath();
  ctx.arc(x, y + 10, 2, 0, Math.PI * 2);
  ctx.fill();
}

// ── Weather Particles ─────────────────────────────────────────────────────────
let rainParticles = [];
let fogOffset = 0;

function initWeatherParticles() {
  rainParticles = [];
  for (let i = 0; i < 120; i++) {
    rainParticles.push({
      x: Math.random() * W,
      y: Math.random() * 400,
      speed: 4 + Math.random() * 4,
      length: 14 + Math.random() * 12,
      opacity: 0.2 + Math.random() * 0.4,
    });
  }
}

function drawRain(heavy) {
  const count = heavy ? 120 : 60;
  ctx.strokeStyle = 'rgba(174,214,241,0.8)';
  ctx.lineWidth = 1.5;
  for (let i = 0; i < count; i++) {
    const p = rainParticles[i];
    ctx.globalAlpha = p.opacity;
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(p.x - 1, p.y + p.length);
    ctx.stroke();
    p.y += p.speed;
    p.x -= 0.5;
    if (p.y > 400) { p.y = -10; p.x = Math.random() * W; }
  }
  ctx.globalAlpha = 1;
}

function drawLightning() {
  if (Math.random() > 0.004) return;
  ctx.fillStyle = 'rgba(255,255,255,0.08)';
  ctx.fillRect(0, 0, W, 400);
  const bx = 200 + Math.random() * 400;
  ctx.strokeStyle = 'rgba(255,255,200,0.9)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(bx, 0);
  ctx.lineTo(bx - 10, 60);
  ctx.lineTo(bx + 8, 60);
  ctx.lineTo(bx - 15, 140);
  ctx.stroke();
}

function drawFog() {
  fogOffset = (fogOffset + 0.3) % W;
  for (let i = 0; i < 3; i++) {
    const x = ((fogOffset + i * 280) % (W + 200)) - 100;
    const grad = ctx.createRadialGradient(x, 340, 0, x, 340, 200);
    grad.addColorStop(0, 'rgba(200,210,220,0.18)');
    grad.addColorStop(1, 'rgba(200,210,220,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 260, W, 160);
  }
}

function getMilestones(vehicle) {
  const v = (vehicle||'').toLowerCase();
  if (v.includes('falcon')) return [{label:'PROP LOAD',t:-2280},{label:'ENGINE CHILL',t:-420},{label:'STRONGBACK',t:-270},{label:'STARTUP',t:-60},{label:'IGNITION',t:-3},{label:'LIFTOFF',t:0},{label:'MAX-Q',t:72},{label:'MECO',t:145},{label:'STAGE SEP',t:149},{label:'FAIRING SEP',t:178},{label:'ENTRY BURN',t:361},{label:'LANDING',t:500},{label:'SECO-1',t:532},{label:'DEPLOY',t:3691}];
  if (v.includes('electron')) return [{label:'AUTO SEQ',t:-120},{label:'IGNITION',t:-2},{label:'LIFTOFF',t:0},{label:'SUPERSONIC',t:60},{label:'MAX-Q',t:71},{label:'MECO',t:149},{label:'STAGE SEP',t:152},{label:'FAIRING SEP',t:191},{label:'SECO',t:570},{label:'DEPLOY',t:3180}];
  if (v.includes('starship')) return [{label:'PROP LOAD',t:-3600},{label:'IGNITION',t:-3},{label:'LIFTOFF',t:0},{label:'MAX-Q',t:58},{label:'MECO',t:169},{label:'STAGE SEP',t:175},{label:'BOOSTER CATCH',t:420},{label:'SECO',t:540},{label:'DEPLOY',t:3600}];
  return [{label:'IGNITION',t:-3},{label:'LIFTOFF',t:0},{label:'MAX-Q',t:75},{label:'MECO',t:160},{label:'STAGE SEP',t:163},{label:'FAIRING SEP',t:200},{label:'SECO',t:520},{label:'DEPLOY',t:3600}];
}

let _tlSmooth = 0;

function drawMilestoneTimeline() {
  const launch = currentLaunch();
  if (!launch || !launch.t0) return;
  const cd = computeCountdown(launch.t0);
  if (!cd || cd === 'LAUNCHED') return;
  if (cd.total_seconds > 1800) return;

  const elapsed = (Date.now() - new Date(launch.t0).getTime()) / 1000;
  const milestones = getMilestones(launch.vehicle || '');
  let currentIdx = 0;
  for (let i = 0; i < milestones.length; i++) {
    if (elapsed >= milestones[i].t) currentIdx = i;
    else break;
  }

  _tlSmooth += (currentIdx * 62 - _tlSmooth) * 0.08;

  const dotX = W - 38;
  const centerY = 195;
  const spacing = 62;
  const opacities = {'-2':0.18,'-1':0.45,'0':1.0,'1':0.45,'2':0.18};
  const scales    = {'-2':0.6, '-1':0.75,'0':1.0,'1':0.75,'2':0.6};
  const visible   = [currentIdx-2, currentIdx-1, currentIdx, currentIdx+1, currentIdx+2];

  function tStr(t){const a=Math.abs(t),m=Math.floor(a/60),s=a%60;return(t<0?'T-':'T+')+m+':'+String(s).padStart(2,'0');}

  visible.forEach(i => {
    if (i < 0 || i >= milestones.length) return;
    const m   = milestones[i];
    const y   = centerY + (i * spacing) - _tlSmooth;
    if (y < 15 || y > 365) return;

    const isDone    = elapsed > m.t;
    const isCurrent = i === currentIdx && !isDone;
    const dist      = i - currentIdx;
    const opacity   = opacities[String(dist)] ?? 0.15;
    const scale     = scales[String(dist)] ?? 0.6;

    // Connecting line
    const ni = i + 1;
    if (visible.includes(ni) && ni < milestones.length) {
      const ny = centerY + ni*spacing - _tlSmooth;
      if (ny < 368) {
        ctx.strokeStyle = isDone ? `rgba(0,232,122,${opacity*0.5})` : `rgba(255,255,255,${opacity*0.15})`;
        ctx.lineWidth = 1;
        ctx.beginPath();ctx.moveTo(dotX,y+7);ctx.lineTo(dotX,Math.min(ny-7,365));ctx.stroke();
      }
    }

    // Dot
    const r = Math.max(2, Math.round(5*scale));
    if (isDone) {
      ctx.fillStyle=`rgba(0,232,122,${opacity})`;
      ctx.beginPath();ctx.arc(dotX,y,r,0,Math.PI*2);ctx.fill();
    } else if (isCurrent) {
      const pulse=0.5+0.5*Math.sin(Date.now()/300);
      ctx.fillStyle=`rgba(255,211,61,${0.15*pulse})`;
      ctx.beginPath();ctx.arc(dotX,y,r+5,0,Math.PI*2);ctx.fill();
      ctx.fillStyle='#ffd93d';
      ctx.beginPath();ctx.arc(dotX,y,r,0,Math.PI*2);ctx.fill();
    } else {
      ctx.strokeStyle=`rgba(255,255,255,${opacity*0.5})`;
      ctx.lineWidth=1;
      ctx.beginPath();ctx.arc(dotX,y,r,0,Math.PI*2);ctx.stroke();
    }

    // Labels
    const ls=Math.max(5,Math.round(9*scale));
    const ts=Math.max(4,Math.round(6*scale));
    ctx.textAlign='right';
    ctx.font=`bold ${ls}px Courier New`;
    ctx.fillStyle=isCurrent?`rgba(255,211,61,${opacity})`:isDone?`rgba(0,232,122,${opacity})`:`rgba(255,255,255,${opacity})`;
    ctx.fillText(m.label, dotX-12, y+3);
    ctx.font=`${ts}px Courier New`;
    ctx.fillStyle=`rgba(255,255,255,${opacity*0.5})`;
    ctx.fillText(tStr(m.t), dotX-12, y+ls+4);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  MAIN RENDER LOOP
// ─────────────────────────────────────────────────────────────────────────────
let lastFrame = 0;
const TARGET_FPS = 30;
const FRAME_MS   = 1000 / TARGET_FPS;

function render(now) {
  requestAnimationFrame(render);
  if (now - lastFrame < FRAME_MS) return;
  lastFrame = now;

  // ── Updates ──
  updateClouds();
  updateBirds();
  updateCars();
  updateGator();
  updateTowerLights();
  updateNotification();
  updateSmoke();
  checkLaunchTrigger();
  updateLaunch();
  updateCooldown();

  // ── Draw (back to front) ──
  ctx.clearRect(0, 0, W, H);

  drawBackground();
  drawClouds();

  // Weather effects
  const cond = state.weather.condition;
  if (cond === 'rain' || cond === 'light_rain') drawRain(false);
  if (cond === 'thunderstorm') { drawRain(true); drawLightning(); }
  if (cond === 'fog') drawFog();
  // drawVAB();  // VAB removed for now
  drawTE();
  drawHIF();
  // drawFences();
  drawRocket();         // ← Draw rocket FIRST (behind)
  drawLaunchTower();    // ← Draw tower AFTER (in front)
  drawLaunchPad();
  //drawPond();
  drawBirds();
  drawCars();
  drawSpotlights();
  drawSmoke();
  drawFlameParticles();
  updateInfoBar();
  drawCountdown();
  drawMilestoneTimeline();
  drawGearIcon();
  drawNoSignal();
  if (state.notification) drawNotification();
  drawNoSignal();
}

// ─────────────────────────────────────────────────────────────────────────────
//  POLLING
// ─────────────────────────────────────────────────────────────────────────────
function updateCooldown() {
  if (!state.postLaunchCooldown) return;
  if (Date.now() >= state.cooldownEndsAt) {
    state.postLaunchCooldown  = false;
    state.cooldownEndsAt      = 0;
    state.launchedMissionName = '';
    state.nextMissionName     = '';
    state.nextMissionT0       = null;
    fetchLaunches(true);
  }
}

async function fetchProbability() {
  const launch = currentLaunch();
  if (!launch) return;
  if (!state._ll2ProbFetched) {
    state._ll2ProbFetched = true;
    fetch(`/api/ll2?name=${encodeURIComponent(launch.name||'')}&id=${encodeURIComponent(launch.id||'')}`)
      .then(r => r.json())
      .then(ll2 => {
        const prob = ll2?.probability ?? null;
        if (prob !== null) {
          document.getElementById('ib-prob-wrap').style.display = 'block';
          document.getElementById('ib-prob-fill').style.width = prob + '%';
          document.getElementById('ib-prob-fill').style.background = prob>=80?'#00e87a':prob>=50?'#ffd93d':'#ff4422';
          document.getElementById('ib-prob-pct').textContent = prob + '%';
          document.getElementById('ib-prob-pct').style.color = prob>=80?'#00e87a':prob>=50?'#ffd93d':'#ff4422';
          // prob badge in new info bar
          const probBadge = document.getElementById('ib-prob-badge');
          probBadge.textContent = prob + '%';
          probBadge.style.display = 'block';
          const pc = prob>=80?'#00e87a':prob>=50?'#ffd93d':'#ff4422';
          probBadge.style.color = pc;
          probBadge.style.borderColor = pc.replace(')',',0.3)').replace('rgb','rgba');
        }
      }).catch(() => {});
  }
}

function startPolling() {
  fetchProbability();
  setInterval(() => {
    if (!state.isLaunching && !state.postLaunchCooldown) {
      fetchLaunches().then(() => showNotification('DATA UPDATED'));
      state._ll2ProbFetched = false;
    }
  }, 5 * 60 * 1000);

  // Canvas snapshot for launches page
  setInterval(() => {
    try {
      fetch('/api/snapshot', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ data: canvas.toDataURL('image/jpeg', 0.6) })
      });
    } catch(e) {}
  }, 500);

  // Refresh weather every 15 minutes
  setInterval(fetchWeather, 15 * 60 * 1000);

  // Fetch LL2 probability once on load, then every 5 minutes
  fetchProbability();
  setInterval(fetchProbability, 5 * 60 * 1000);

  // Update HTML info bar every second
  setInterval(updateInfoBar, 1000);
}

// ─────────────────────────────────────────────────────────────────────────────
//  TEST LAUNCH BUTTON
// ─────────────────────────────────────────────────────────────────────────────
document.getElementById('btn-test').addEventListener('click', () => {
  if (state.isLaunching || state.testMode) return;
  const launch = currentLaunch();
  if (!launch) return;
  console.log(`[${ts()}] TEST MODE — overriding t0 to T-3s`);
  const originalT0        = launch.t0;
  const originalTriggered = state.launchTriggered;
  state.testMode          = true;
  launch.t0               = new Date(Date.now() + 3000).toISOString();
  state.launchTriggered   = false;

  const checkReset = setInterval(() => {
    if (!state.rocketOffscreen) return;
    clearInterval(checkReset);

    // Show cooldown for 10s in test mode (not 10 min)
    const launchedName = launch.name || '';
    state.launchedMissionName = launchedName;
    state.nextMissionName     = launchedName;  // same mission coming back
    state.nextMissionT0       = originalT0;    // real t0 = the "next" launch
    state.postLaunchCooldown  = true;
    state.cooldownEndsAt      = Date.now() + 10 * 1000; // 10 seconds for testing

    // When cooldown ends, restore everything back to normal
    const cooldownEnd = setInterval(() => {
      if (Date.now() < state.cooldownEndsAt) return;
      clearInterval(cooldownEnd);
      launch.t0                 = originalT0;
      state.launchTriggered     = originalTriggered;
      state.testMode            = false;
      state.postLaunchCooldown  = false;
      state.launchedMissionName = '';
      state.nextMissionName     = '';
      state.nextMissionT0       = null;
      state.rocketOffscreen     = false;
      state.launchComplete      = false;
      state.rocketY             = PAD_Y_BASE;
      state.flameParticles      = [];
      state.flameIntensity      = 0;
      console.log(`[${ts()}] TEST MODE complete — restored`);
    }, 500);

    console.log(`[${ts()}] TEST MODE rocket offscreen — cooldown demo started`);
  }, 200);
});

canvas.addEventListener('click', function(e) {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;


  // Gear icon tap zone (next to wifi) — goes to settings too
  if (x > W - 40 && x < W  && y > 0 && y < 40) {
    window.location = 'http://localhost:5001/settings';
  }

  // Mission name tap zone (bottom info bar)
  if (x > 0 && x < 400 && y > BAR_Y && y < BAR_Y + 35) {
    const launch = currentLaunch();
    if (launch) {
      window.location = `http://localhost:5001/mission?id=${launch.id}&name=${encodeURIComponent(launch.name)}`;
    }
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  BOOT
// ─────────────────────────────────────────────────────────────────────────────
(async function boot() {
  await loadAssets();
  spawnBirds();
  spawnCars();
  await Promise.all([fetchLaunches(), fetchWeather(), fetchSettings()]);
  initWeatherParticles();
  startPolling();
  requestAnimationFrame(render);
  console.log(`[${ts()}] Launch Countdown Phase 2 ready`);
})();