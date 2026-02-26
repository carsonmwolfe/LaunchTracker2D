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

const W = 800, H = 600;

let state = {
  launches:    [],
  currentIdx:  0,
  weather:     { condition: 'clear', temp_f: 75, wind_speed: 10, wind_dir: 'E', cloud_cover: 0, label: 'Clear sky' },

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

  // Notification banner
  notification: null,   // { text, alpha, offset }

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
  if (h >= 10 && h < 16) {
    if (['rain','thunderstorm'].includes(cond)) return { sky:'#5a6a7a', ocean:'#0d1a2e', cloud:'#606060' };
    if (cond === 'cloudy')  return { sky:'#9ab8d3', ocean:'#1a5b6e', cloud:'#c8c8c8' };
    return { sky:'#87ceeb', ocean:'#1a8b9e', cloud:'#ffffff' };
  }
  if (h >= 16 && h < 18)
    return { sky:'#ff9933', ocean:'#1a5b6e', cloud:'#ffd9b3' };
  if (h >= 6  && h < 10)
    return { sky:'#ff9966', ocean:'#2a5b6e', cloud:'#ffe5cc' };
  if (['rain','thunderstorm'].includes(cond))
    return { sky:'#0a0a0a', ocean:'#050510', cloud:'#404040' };
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

// Polyfill for ctx.roundRect (not available in older Chromium)
function roundRectPath(x, y, w, h, r) {
  var tl, tr, br, bl;
  if (Array.isArray(r)) {
    tl = r[0]||0; tr = r[1]||0; br = r[2]||0; bl = r[3]||0;
  } else {
    tl = tr = br = bl = r||0;
  }
  ctx.moveTo(x + tl, y);
  ctx.lineTo(x + w - tr, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + tr);
  ctx.lineTo(x + w, y + h - br);
  ctx.quadraticCurveTo(x + w, y + h, x + w - br, y + h);
  ctx.lineTo(x + bl, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - bl);
  ctx.lineTo(x, y + tl);
  ctx.quadraticCurveTo(x, y, x + tl, y);
  ctx.closePath();
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

  // Ocean
  ctx.fillStyle = colors.ocean;
  ctx.fillRect(0, 500, W, 100);
  ctx.fillStyle = '#156673';
  ctx.fillRect(0, 500, W, 15);

  // Grass
  ctx.fillStyle = '#5a8c3a';
  ctx.fillRect(0, 365, W, 135);

  // Road
  drawRoad();

  // Pixel grass details (seeded so stable)
  drawPixelGrass();
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
  drawRect(0, 420, W, 18, '#3a3a3a');
  drawRect(0, 420, W, 2,  '#5a5a5a');
  drawRect(0, 436, W, 2,  '#5a5a5a');
  ctx.fillStyle = '#6a6a3a';
  for (let x = 0; x < W; x += 20) ctx.fillRect(x, 428, 10, 2);
}

function drawPixelGrass() {
  const rng = mulberry32(123);
  const colors = ['#4a7c2a','#6a9c4a','#5a8c3a','#3a6c1a'];
  for (let i = 0; i < 400; i++) {
    const gx = rng() * W;
    const gy = 368 + rng() * 127;
    ctx.fillStyle = colors[Math.floor(rng() * 4)];
    const style = Math.floor(rng() * 4);
    if (style === 0)      { ctx.fillRect(gx, gy-3, 1, 3); }
    else if (style === 1) { ctx.fillRect(gx, gy, 2, 3); }
    else if (style === 2) { ctx.fillRect(gx, gy, 1, 1); }
    else                  { ctx.fillRect(gx, gy-3, 1, 3); }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  VAB BUILDING
// ─────────────────────────────────────────────────────────────────────────────
function drawVAB() {
  if (IMG.vab) {
    // Draw the new VAB PNG - much bigger and sitting on grass
    const vw = IMG.vab.width;
    const vh = IMG.vab.height;
    
    // Make VAB much bigger (was 150, now 220)
    const TARGET_HEIGHT = 350;
    const scale = TARGET_HEIGHT / vh;
    const scaledW = vw * scale;
    const scaledH = TARGET_HEIGHT;
    
    // Position on grass: x=60, bottom at y=365 (top of grass)
    const vabX = 40;
    const vabY = 108;
    
    ctx.drawImage(IMG.vab, vabX, vabY, scaledW, scaledH);
    return;
  }

  // Fallback: procedural draw (Phase 1 faithful)
  const vx = 60, vy = 215, vw = 140, vh = 150;

  // Depth panels
  drawRect(vx+vw, vy+10, 25, vh-10, '#5a5e64');
  drawRect(vx+vw+25, vy+20, 15, vh-20, '#4a4a4a');

  // Main body
  drawRect(vx, vy, vw, vh, '#e8dfd0', '#000000', 2);

  // Roof strip
  drawRect(vx, vy, vw, 10, '#4a4e54');

  // Roof equipment
  drawRect(vx+25, vy-8, 8, 8, '#3a3a3a', '#000000', 1);
  drawRect(vx+90, vy-8, 8, 8, '#3a3a3a', '#000000', 1);

  // Centre tower
  const cx = vx+48, cw = 48, ct = vy+15;
  drawRect(cx, ct, cw, vh-(15), '#5a5e64');
  ctx.strokeStyle='#ffffff'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.moveTo(cx,ct); ctx.lineTo(cx+cw,ct); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx,ct); ctx.lineTo(cx,vy+vh); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx+cw,ct); ctx.lineTo(cx+cw,vy+vh); ctx.stroke();

  // Door
  const dx=cx+10, dy=ct+20, dw=28, dh=(vy+vh)-dy-2;
  drawRect(dx-2,dy-2,dw+4,dh+4,'#000000');
  drawRect(dx,dy,dw,dh,'#b0b0b0');
  const stripes=Math.floor(dh/5.5);
  for(let i=0;i<stripes;i++){
    const sy=dy+2+i*5.5;
    if(sy<dy+dh-2) drawRect(dx+2,sy,dw-4,2,'#707070');
  }

  // American flag
  const fx=vx+10, fy=vy+30, fw=32, fh=55;
  const sw=fw/13;
  for(let i=0;i<13;i++){
    drawRect(fx+i*sw, fy, sw, fh, i%2===0?'#b22234':'#ffffff');
  }
  drawRect(fx, fy, fw*(7/13), fh*0.54, '#3c3b6e');
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
//  FENCES
// ─────────────────────────────────────────────────────────────────────────────
function drawFences() {
  const fc='#8a8a8a', pc='#6a6a6a';
  // Back fence
  for(let x=520;x<730;x+=20){
    drawRect(x,347,3,18,pc);
    if(x+20<730){
      drawRect(x+3,351,17,2,fc);
      drawRect(x+3,359,17,2,fc);
    }
  }
  // Left fence
  for(let y=340;y<450;y+=20){
    drawRect(520,y,3,18,pc);
    drawRect(520,y+4,3,2,fc);
    drawRect(520,y+6,3,8,fc);
  }
  // Right fence
  for(let y=340;y<440;y+=20){
    drawRect(720,y,3,18,pc);
    drawRect(720,y+4,3,2,fc);
    drawRect(720,y+12,3,2,fc);
  }
  // Bottom fence
  for(let x=520;x<=740;x+=20){
    drawRect(x,440,3,18,pc);
    if(x+30<720) drawRect(x+5,444,35,2,fc);
  }
  // Guard shack
  drawRect(490,395,20,25,'#d8d8d8','#3a3a3a',2);
  ctx.fillStyle='#8a4a4a';
  ctx.beginPath(); ctx.moveTo(488,395); ctx.lineTo(500,387); ctx.lineTo(512,395); ctx.fill();
  drawRect(494,400,6,7,'#5a7a9a','#3a3a3a',1);
  drawRect(502,405,6,15,'#5a4a3a','#3a3a3a',1);
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
const ROAD_Y = 429;

function spawnCars() {
  for(let i=0;i<6;i++){
    state.cars.push({
      x: -50 - i*80, y: ROAD_Y,
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
  if (v.includes('falcon') || v.includes('starship')) return 'rocket_falcon9';
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
  const vehicle2   = nextLaunch?.vehicle || currentLaunch()?.vehicle || '';
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
  const vehicle  = currentLaunch()?.vehicle || '';
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
  const vehicle  = currentLaunch()?.vehicle || '';
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

  const BW = 58, BH = 58, GAP = 6;
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

  if (cd === 'LAUNCHED') {
    ctx.fillStyle='#ff4444'; ctx.shadowColor='#ff2200'; ctx.shadowBlur=8;
    ctx.font='bold 20px Courier New'; ctx.textAlign='center';
    ctx.fillText('🚀  LAUNCHED', BX+TOTAL_W/2, BY+BH/2+14);
    ctx.shadowBlur=0; return;
  }
  if (!cd) {
    ctx.fillStyle='#ffd93d'; ctx.font='bold 9px Courier New'; ctx.textAlign='center';
    ctx.fillText('LAUNCH TIME TBD', BX+TOTAL_W/2, BY+BH/2+10); return;
  }

  LABELS.forEach((lbl, i) => {
    const bx = BX + i*(BW+GAP);
    const by = BY + 8;

    // Plastic body
    ctx.fillStyle='#c8d4e0'; ctx.fillRect(bx, by, BW, BH);
    // Bevels
    ctx.fillStyle='#e2ecf4'; ctx.fillRect(bx, by, BW, 2); ctx.fillRect(bx, by, 2, BH);
    ctx.fillStyle='#8a9db0'; ctx.fillRect(bx, by+BH-2, BW, 2); ctx.fillRect(bx+BW-2, by, 2, BH);
    ctx.strokeStyle='#6080a0'; ctx.lineWidth=1; ctx.strokeRect(bx+0.5, by+0.5, BW-1, BH-1);

    // LCD screen
    const px=6, py=5, sw=BW-12, sh=BH-py*2-14;
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
    ctx.shadowColor='#00ff88'; ctx.shadowBlur=7;
    ctx.fillStyle='#00e87a';
    ctx.font='bold 20px Courier New';
    ctx.textAlign='center';
    ctx.textBaseline='middle';
    ctx.fillText(String(vals[i]).padStart(2,'0'), sx + sw/2, sy + sh/2);
    ctx.textBaseline='alphabetic';
    ctx.shadowBlur=0;

    // Label
    ctx.fillStyle='#4a7aaa'; ctx.font='bold 6px Courier New'; ctx.textAlign='center';
    ctx.fillText(lbl, bx+BW/2, by+BH-3);
  });
}


// ─────────────────────────────────────────────────────────────────────────────
//  INFO SIGN  (right edge, matches Phase 1)
// ─────────────────────────────────────────────────────────────────────────────
function drawInfoSign() {
  const launch = currentLaunch();
  if (!launch) return;

  const SW = 170, SX = W - SW - 6, SY = 148;
  const IX = SX + 14, IW = SW - 28;

  const statusColors = {
    'Go':'#00e87a','Go for Launch':'#00e87a',
    'TBD':'#ffd93d','To Be Determined':'#ffd93d','To Be Confirmed':'#ffd93d',
  };
  const statusCol = statusColors[launch.status] || '#4a9ede';

  const shorten = s => (s||'Unknown')
    .replace('Space Launch Complex','SLC').replace('Launch Complex','LC')
    .replace('Space Force Station','SFS').replace('Air Force Base','AFB')
    .replace('Kennedy Space Center','KSC').replace('Cape Canaveral','CCAFS')
    .replace('Vandenberg Space Force Base','VSFB');

  const formatT0 = t0 => {
    if (!t0) return { date:'TBD', time:'' };
    try {
      const d = new Date(t0);
      return {
        date: d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}),
        time: d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:'UTC'}) + ' UTC',
      };
    } catch(e) { return { date:t0, time:'' }; }
  };

  const wrapText = (text, maxPx, font) => {
    ctx.font = font;
    const words = (text||'Unknown').split(' ');
    const lines = []; let cur = '';
    for (const w of words) {
      const t = cur ? cur+' '+w : w;
      if (ctx.measureText(t).width <= maxPx) cur = t;
      else { if(cur) lines.push(cur); cur = w; }
    }
    if(cur) lines.push(cur);
    return lines;
  };

  const lt = formatT0(launch.t0 || launch.win_open);
  const F_VAL  = '11px monospace';
  const F_LBL  = 'bold 8px monospace';
  const F_NAME = 'bold 12px monospace';
  const LH = 13;

  const nameLines = wrapText(launch.name||'Unknown', IW, F_NAME).slice(0,2);
  const padLines  = wrapText(shorten(launch.pad||launch.location||'Unknown'), IW, F_VAL).slice(0,2);
  const vehLines  = wrapText(launch.vehicle||'Unknown', IW, F_VAL).slice(0,2);
  const provLines = wrapText(launch.provider||'Unknown', IW, F_VAL).slice(0,2);

  // Dynamic height — capped so sign never overlaps the grass (ground starts y=365)
  const MAX_SIGN_BOTTOM = 362;
  const rawPH = 22 + 10
    + nameLines.length * 15 + 10
    + 1 + 10
    + 9 + 14 + (lt.time ? 13 : 0) + 10
    + 1 + 10
    + 9 + padLines.length  * LH + 6
    + 9 + vehLines.length  * LH + 6
    + 9 + provLines.length * LH + 6
    + 1 + 10
    + 22 + 8;
  const PH = Math.min(rawPH, MAX_SIGN_BOTTOM - SY);

  // Background
  ctx.save();
  ctx.fillStyle = 'rgba(5,5,10,0.96)';
  ctx.beginPath(); roundRectPath(SX, SY, SW, PH, 5); ctx.fill();
  ctx.strokeStyle = statusCol; ctx.lineWidth = 2; ctx.stroke();

  // Header
  ctx.fillStyle = statusCol;
  ctx.beginPath(); roundRectPath(SX, SY, SW, 22, [5,5,0,0]); ctx.fill();
  ctx.fillStyle = 'rgba(0,0,0,0.8)';
  ctx.font = 'bold 11px monospace'; ctx.textAlign = 'center';
  ctx.fillText('NEXT LAUNCH', SX+SW/2, SY+15);

  let oy = SY + 32;

  // Mission name
  ctx.fillStyle = '#ffffff'; ctx.font = F_NAME; ctx.textAlign = 'center';
  nameLines.forEach(ln => { ctx.fillText(ln, SX+SW/2, oy); oy += 15; });
  oy += 8;

  const divider = () => {
    ctx.fillStyle='rgba(255,255,255,0.1)'; ctx.fillRect(IX, oy, IW, 1); oy += 10;
  };
  const rowLbl = txt => {
    ctx.font=F_LBL; ctx.textAlign='left'; ctx.fillStyle='rgba(255,255,255,0.4)';
    ctx.fillText(txt, IX, oy); oy += 11;
  };
  const rowVal = (lines, col) => {
    ctx.font=F_VAL; ctx.textAlign='left'; ctx.fillStyle=col||'#fff';
    lines.forEach(ln => { ctx.fillText(ln, IX, oy); oy += LH; });
    oy += 4;
  };

  divider();

  // Launch time
  rowLbl('LAUNCH TIME');
  ctx.font='bold 12px monospace'; ctx.textAlign='left'; ctx.fillStyle='#ffd93d';
  ctx.fillText(lt.date, IX, oy); oy += 14;
  if (lt.time) { ctx.font=F_VAL; ctx.fillStyle='#ffd93d'; ctx.fillText(lt.time, IX, oy); oy += LH; }
  oy += 6;

  divider();

  rowLbl('LAUNCH PAD');  rowVal(padLines,  '#ff9944');
  rowLbl('VEHICLE');     rowVal(vehLines,  '#4a9ede');
  rowLbl('PROVIDER');    rowVal(provLines, '#dddddd');

  divider();

  // Status badge
  ctx.fillStyle=statusCol+'28';
  ctx.beginPath(); roundRectPath(IX, oy, IW, 22, 3); ctx.fill();
  ctx.strokeStyle=statusCol; ctx.lineWidth=1.5; ctx.stroke();
  ctx.fillStyle=statusCol; ctx.font='bold 11px monospace'; ctx.textAlign='center';
  ctx.fillText((launch.status||'TBD').toUpperCase(), SX+SW/2, oy+15);

  ctx.restore();
}

// ─────────────────────────────────────────────────────────────────────────────
//  ATTRIBUTION
// ─────────────────────────────────────────────────────────────────────────────
function drawAttribution() {
  ctx.fillStyle='#666666'; ctx.font='7px Courier New'; ctx.textAlign='center';
  ctx.fillText('Data: RocketLaunch.Live  |  Weather: Open-Meteo', 400, 580);
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
  if (!cd || cd === 'LAUNCHED') return;

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
      if (!state.testMode) {
        console.log(`[${ts()}] Launch complete — fetching next mission`);
        fetch('/api/launches/invalidate', { method: 'POST' })
          .then(() => fetchLaunches(true));
      } else {
        console.log(`[${ts()}] Test launch complete — awaiting reset`);
      }
    }
  }

  const flameX = NOZZLE_X;
  const flameY = NOZZLE_Y + (state.rocketY - PAD_Y_BASE) + 8;
  if (state.flameIntensity > 0) {
    spawnFlameParticles(flameX, flameY, state.flameIntensity);
  }
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
    const prev = currentLaunch()?.id;

    state.launches = data.launches || [];

    if (afterLaunch) {
      // Move to next different launch, reset all animation state
      const newLaunch = state.launches.find(l => l.id !== prev) || state.launches[0];
      state.currentIdx = newLaunch ? state.launches.indexOf(newLaunch) : 0;
      state.launchTriggered = false;
      state.isLaunching     = false;
      state.rocketOffscreen = false;
      state.launchComplete  = false;
      state.rocketY         = PAD_Y_BASE;
      state.flameParticles  = [];
      showNotification('NEXT MISSION');
    } else {
      state.currentIdx = 0;
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

  // ── Draw (back to front) ──
  ctx.clearRect(0, 0, W, H);

  drawBackground();
  drawClouds();
  // drawVAB();  // VAB removed for now
  drawTE();
  drawHIF();
  // drawFences();
  drawRocket();         // ← Draw rocket FIRST (behind)
  drawLaunchTower();    // ← Draw tower AFTER (in front)
  drawLaunchPad();
  drawPond();
  drawBirds();
  drawCars();
  drawSpotlights();
  drawSmoke();
  drawFlameParticles();
  drawInfoSign();
  drawCountdown();
  drawAttribution();
  if (state.notification) drawNotification();
}

// ─────────────────────────────────────────────────────────────────────────────
//  POLLING
// ─────────────────────────────────────────────────────────────────────────────
function startPolling() {
  // Refresh launches every 5 minutes
  setInterval(() => {
    if (!state.isLaunching) {
      fetchLaunches().then(() => showNotification('DATA UPDATED'));
    }
  }, 5 * 60 * 1000);

  // Refresh weather every 15 minutes
  setInterval(fetchWeather, 15 * 60 * 1000);
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
    if (state.rocketOffscreen) {
      clearInterval(checkReset);
      launch.t0             = originalT0;
      state.launchTriggered = originalTriggered;
      state.isLaunching     = false;
      state.rocketOffscreen = false;
      state.launchComplete  = false;
      state.rocketY         = PAD_Y_BASE;
      state.flameParticles  = [];
      state.flameIntensity  = 0;
      state.testMode        = false;
      console.log(`[${ts()}] TEST MODE complete — restored original countdown`);
    }
  }, 200);
});

// ─────────────────────────────────────────────────────────────────────────────
//  BOOT
// ─────────────────────────────────────────────────────────────────────────────
(async function boot() {
  await loadAssets();
  spawnBirds();
  spawnCars();
  await Promise.all([fetchLaunches(), fetchWeather()]);
  startPolling();
  requestAnimationFrame(render);
  console.log(`[${ts()}] Launch Countdown Phase 2 ready`);
})();