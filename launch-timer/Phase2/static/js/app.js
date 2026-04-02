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
  mlp:             'ground-MLP.png',
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
  rocket_soyuz5:    'rocket-Soyuz5.png',
  rocket_ariane6:   'rocket-Ariane6.png',
  rocket_sls:       'rocket-SLS.png',
  rocket_kinetica:  'rocket-Kinetica2.png',
  rocket_gslv:      'rocket-GSLV.png',
  rocket_firefly:   'rocket-firefly.png',
  rocket_longmarch12:  'rocket-longmarch12.png',
  rocket_longmarch2d:  'rocket-longmarch2d.png',
  rocket_vegaC:        'rocket-vegaC.png',
  rocket_jielong:      'rocket-Jielong.png',
  rocket_falconheavy:  'rocket-FalconHeavy.png',
  rocket_minotaur:     'rocket-MinotaurIV.png',
  rocket_neutron:      'rocket-Neutron.png',
  rocket_rfaone:       'rocket-RFAone.png',
  rocket_spectrum:     'rocket-Spectrum.png',
  rocket_tianlong:     'rocket-tianlong3.png',
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
  buriedLaunchIds: [],

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
function _getSkyPhase() {
  // Use server-provided sunrise/sunset if available, else fall back to clock
  const now = Date.now();
  const wx = state.weather;
  let srMs = null, ssMs = null;
  if (wx.sunrise) try { srMs = new Date(wx.sunrise).getTime(); } catch(e) {}
  if (wx.sunset)  try { ssMs = new Date(wx.sunset).getTime();  } catch(e) {}
  if (srMs && ssMs) {
    const fade = 45 * 60 * 1000; // 45 min fade window
    if (now < srMs - fade)               return 'night';
    if (now < srMs)                      return 'sunrise';
    if (now < ssMs - fade)               return 'day';
    if (now < ssMs)                      return 'sunset';
    return 'night';
  }
  // Fallback: hour-based
  const h = getHour();
  if (h >= 10 && h < 16) return 'day';
  if (h >= 16 && h < 18) return 'sunset';
  if (h >= 6  && h < 10) return 'sunrise';
  return 'night';
}

function getSkyColors() {
  const cond = state.weather.condition;
  const isRainy = ['rain','thunderstorm','light_rain'].includes(cond);
  if (isRainy) return { sky:'#3a4a5a', ocean:'#0d1a2e', cloud:'#505050' };
  if (cond === 'cloudy') return { sky:'#7a9ab8', ocean:'#1a5b6e', cloud:'#b0b0b0' };
  if (cond === 'fog')    return { sky:'#8a9aaa', ocean:'#1a5b6e', cloud:'#c0c8d0' };
  const phase = _getSkyPhase();
  if (phase === 'day')     return { sky:'#87ceeb', ocean:'#1a8b9e', cloud:'#ffffff' };
  if (phase === 'sunset')  return { sky:'#ff9933', ocean:'#1a5b6e', cloud:'#ffd9b3' };
  if (phase === 'sunrise') return { sky:'#ff9966', ocean:'#2a5b6e', cloud:'#ffe5cc' };
  return { sky:'#0a0a1e', ocean:'#0d1a2e', cloud:'#d0d0d0' };
}

function isNight() { return _getSkyPhase() === 'night'; }

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
//  VAB
// ─────────────────────────────────────────────────────────────────────────────
function drawVAB() {
  if (!IMG.vab) return;
  const h = 427;
  const w = Math.round(IMG.vab.width * (h / IMG.vab.height));
  ctx.drawImage(IMG.vab, -64, 61, w, h);
}

// ─────────────────────────────────────────────────────────────────────────────
//  LAUNCH TOWER + PAD
// ─────────────────────────────────────────────────────────────────────────────
function drawLaunchTower() {
  if (IMG.launchTower) {
    const h = 289;
    const w = Math.round(IMG.launchTower.width * (h / IMG.launchTower.height));
    ctx.drawImage(IMG.launchTower, 456, 141.1, w, h);
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
//  UMBILICAL ARMS
// ─────────────────────────────────────────────────────────────────────────────
function drawUmbilicals() {
  if (state.rocketOffscreen || state.launchComplete || state.postLaunchCooldown) return;
  if (state.isLaunching && state.rocketY < PAD_Y_BASE - 10) return;

  const vehicle  = (currentLaunch() ? currentLaunch().vehicle : null) || '';
  const assetKey = getRocketAssetKey(vehicle);
  const cfg      = (ROCKET_CONFIG[assetKey] || ROCKET_CONFIG.rocket_generic).pad;
  const launchOffset = state.isLaunching ? state.rocketY - PAD_Y_BASE : 0;

  // Tower face where arm is bolted, rocket right side where cables attach
  // Anchor to NOZZLE_X (pad centre) rather than cfg.x (image left edge)
  const rocketRightX = NOZZLE_X + 8;   // right side of rocket body ≈ 523
  const towerFaceX   = NOZZLE_X + 28;  // left structural face of tower ≈ 543

  // Each arm: { frac=height along rocket, cableColors=array of line colors }
  const arms = [
    { frac: 0.18, cableColors: ['#dddddd','#ffffff','#cccccc'] },
    { frac: 0.44, cableColors: ['#cc2222','#ff4444','#cc2222'] },
    { frac: 0.67, cableColors: ['#dddddd','#ffffff','#cccccc'] },
  ];

  arms.forEach(({ frac, cableColors }) => {
    const pivotY = Math.round(cfg.y + launchOffset + cfg.h * frac);

    // ── Rigid swing arm: grey beam from tower face out to rocket ──
    ctx.strokeStyle = '#777777';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(towerFaceX, pivotY);
    ctx.lineTo(rocketRightX + 5, pivotY);
    ctx.stroke();

    // Small mounting bracket box at tower
    ctx.fillStyle = '#555555';
    ctx.fillRect(towerFaceX, pivotY - 4, 4, 8);

    // ── Cable bundle: 3 lines drooping from arm tip to rocket ──
    const cableStartX = rocketRightX + 5;
    const cableEndX   = rocketRightX;
    // cables droop downward from where arm ends to the rocket skin
    const droopY = pivotY + 5;

    cableColors.forEach((col, j) => {
      const offY = (j - 1) * 1.5;  // slight vertical spread
      ctx.strokeStyle = col;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cableStartX, pivotY + offY);
      ctx.quadraticCurveTo(
        cableStartX - 4, droopY + offY,
        cableEndX,       pivotY + offY + 2
      );
      ctx.stroke();
    });

    // Connector plate at rocket skin
    ctx.fillStyle = cableColors[1];
    ctx.fillRect(rocketRightX - 2, pivotY - 3, 4, 7);
  });
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
  // Spotlight poles sit left and right of the pad, aim at the rocket centre
  const groundY = PAD_Y_BASE + 7;
  const poleH   = 30;
  const targetX = NOZZLE_X + 10;   // rocket centre
  const targetY = NOZZLE_Y - 40;
  const lx      = targetX - 60;   // left pole
  const rx      = targetX + 80;    // right pole

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

  // ── Blinking aviation lights on right side of tower ───────────────────────
  // Pulse on for 0.5s every 3s
  const blink = (Date.now() % 3000) < 500;
  const towerRightX = 562;  // right edge of launch tower
  const light1Y = 185;      // upper light
  const light2Y = 250;      // lower light
  if (blink) {
    ctx.save();
    ctx.fillStyle = '#ffffff';
    // Glow
    const gl1 = ctx.createRadialGradient(towerRightX, light1Y, 0, towerRightX, light1Y, 8);
    gl1.addColorStop(0, 'rgba(255,255,255,0.9)'); gl1.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gl1;
    ctx.beginPath(); ctx.arc(towerRightX, light1Y, 8, 0, Math.PI*2); ctx.fill();
    const gl2 = ctx.createRadialGradient(towerRightX, light2Y, 0, towerRightX, light2Y, 8);
    gl2.addColorStop(0, 'rgba(255,255,255,0.9)'); gl2.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gl2;
    ctx.beginPath(); ctx.arc(towerRightX, light2Y, 8, 0, Math.PI*2); ctx.fill();
    // Core dot
    ctx.fillStyle = '#ffffff';
    ctx.beginPath(); ctx.arc(towerRightX, light1Y, 3, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(towerRightX, light2Y, 3, 0, Math.PI*2); ctx.fill();
    ctx.restore();
  } else {
    // Dim off-state
    ctx.fillStyle = 'rgba(180,180,180,0.3)';
    ctx.beginPath(); ctx.arc(towerRightX, light1Y, 2, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(towerRightX, light2Y, 2, 0, Math.PI*2); ctx.fill();
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
  if (v.includes('soyuz-5') || v.includes('soyuz5')) return 'rocket_soyuz5';
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
  if (v.includes('long march 12') || v.includes('longmarch-12') || v.includes('lm-12')) return 'rocket_longmarch12';
  if (v.includes('long march 2d') || v.includes('longmarch-2d') || v.includes('cz-2d')) return 'rocket_longmarch2d';
  if (v.includes('long march') || v.includes('longmarch') || v.includes('chang zheng')) return 'rocket_longmarch';
  if (v.includes('vega'))                                                               return 'rocket_vegaC';
  if (v.includes('jielong') || v.includes('smart dragon'))                              return 'rocket_jielong';
  if (v.includes('falcon heavy'))                                                        return 'rocket_falconheavy';
  if (v.includes('minotaur'))                                                            return 'rocket_minotaur';
  if (v.includes('neutron'))                                                             return 'rocket_neutron';
  if (v.includes('rfa') || v.includes('rfa one'))                                       return 'rocket_rfaone';
  if (v.includes('spectrum'))                                                            return 'rocket_spectrum';
  if (v.includes('tianlong') || v.includes('sky dragon'))                               return 'rocket_tianlong';
  return 'rocket_generic';
}

const ROCKET_CONFIG = {
  rocket_falcon9:     { pad: { x: 440, y: 204, h: 155 }, te: { x: 128, y: 203, h: 155 } },
  rocket_atlas:       { pad: { x: 469, y: 209, h: 162 }, te: { x: 167, y: 200, h: 162 } },
  rocket_vulcan:      { pad: { x: 464, y: 170, h: 181 }, te: { x: 159, y: 164, h: 181 } },
  rocket_electron:    { pad: { x: 483, y: 251, h: 116 }, te: { x: 180, y: 239, h: 116 } },
  rocket_ng:          { pad: { x: 457, y: 170, h: 200 }, te: { x: 154, y: 161, h: 200 } },
  rocket_kairos:      { pad: { x: 511, y: 234, h: 127 }, te: { x: 207, y: 224, h: 127 } },
  rocket_longmarch:   { pad: { x: 471, y: 205, h: 156 }, te: { x: 167, y: 195, h: 156 } },
  rocket_generic:     { pad: { x: 440, y: 204, h: 155 }, te: { x: 128, y: 203, h: 155 } },
  rocket_firefly:     { pad: { x: 470, y: 210, h: 164 }, te: { x: 167, y: 203, h: 164 } },
  rocket_starship:    { pad: { x: 445, y: 157, h: 228 }, te: { x: 143, y: 148, h: 228 } },
  rocket_soyuz:       { pad: { x: 480, y: 219, h: 131 }, te: { x: 177, y: 209, h: 131 } },
  rocket_soyuz5:      { pad: { x: 480, y: 219, h: 131 }, te: { x: 177, y: 209, h: 131 } },
  rocket_ariane6:     { pad: { x: 472, y: 204, h: 146 }, te: { x: 173, y: 194, h: 146 } },
  rocket_sls:         { pad: { x: 513, y: 177, h: 169 }, te: { x: 208, y: 170, h: 169 } },
  rocket_kinetica:    { pad: { x: 440, y: 204, h: 155 }, te: { x: 128, y: 203, h: 155 } },
  rocket_gslv:        { pad: { x: 479, y: 215, h: 132 }, te: { x: 177, y: 206, h: 132 } },
  rocket_longmarch12: { pad: { x: 470, y: 214, h: 155 }, te: { x: 170, y: 203, h: 155 } },
  rocket_longmarch2d: { pad: { x: 474, y: 212, h: 147 }, te: { x: 173, y: 202, h: 147 } },
  rocket_vegaC:       { pad: { x: 459, y: 186, h: 187 }, te: { x: 155, y: 176, h: 187 } },
  rocket_jielong:     { pad: { x: 474, y: 220, h: 146 }, te: { x: 172, y: 209, h: 146 } },
  rocket_falconheavy: { pad: { x: 479, y: 220, h: 116 }, te: { x: 179, y: 220, h: 116 } },
  rocket_minotaur:    { pad: { x: 485, y: 235, h: 115 }, te: { x: 182, y: 225, h: 115 } },
  rocket_neutron:     { pad: { x: 484, y: 232, h: 118 }, te: { x: 181, y: 220, h: 118 } },
  rocket_rfaone:      { pad: { x: 484, y: 239, h: 124 }, te: { x: 180, y: 228, h: 124 } },
  rocket_spectrum:    { pad: { x: 476, y: 219, h: 142 }, te: { x: 172, y: 209, h: 142 } },
  rocket_tianlong:    { pad: { x: 478, y: 222, h: 136 }, te: { x: 174, y: 211, h: 136 } },
};
const PAD_Y_BASE = 359
const NOZZLE_X   = 515;
const NOZZLE_Y   = 280;

function drawMLPRocket() {
  // Draw the next rocket on the MLP — must be called BEFORE drawMLP() so MLP overlays it
  const nextLaunch = state.launches[state.currentIdx + 1] || null;
  const vehicle2   = (nextLaunch ? nextLaunch.vehicle : null) || (currentLaunch() ? currentLaunch().vehicle : null) || '';
  const assetKey2  = getRocketAssetKey(vehicle2);
  const rocketImg  = IMG[assetKey2];
  if (!rocketImg) return;
  const cfg  = (ROCKET_CONFIG[assetKey2] || ROCKET_CONFIG.rocket_generic).te;
  const rw2  = Math.round(rocketImg.width * (cfg.h / rocketImg.height));
  ctx.drawImage(rocketImg, cfg.x, cfg.y, rw2, cfg.h);
}

function drawMLP() {
  if (!IMG.mlp) return;
  const h = 78;
  const w = Math.round(IMG.mlp.width * (h / IMG.mlp.height));
  ctx.save();
  ctx.translate(233, 348);
  ctx.rotate(0.0021);
  ctx.drawImage(IMG.mlp, -w / 2, -39, w, h);
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
  const ventY    = cfg.y + cfg.h * 0.5;  // mid-rocket
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


function updateInfoBar() {

  // If the HTML info-bar isn't present in this page (e.g. canvas-only embed),
  // bail out to avoid "Cannot set properties of null" errors.
  if (!document.getElementById('ib-name')) return;

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

  // Name — use mission name after " | " if present, otherwise full name
  const fullName = launch.name || '—';
  const pipeIdx  = fullName.indexOf(' | ');
  const missionName = pipeIdx >= 0 ? fullName.slice(pipeIdx + 3) : fullName;
  const nameEl = document.getElementById('ib-name');
  nameEl.textContent = missionName;
  nameEl.style.fontSize = missionName.length > 24 ? '10px' : missionName.length > 16 ? '12px' : '14px';

  // Badge
  const badge = document.getElementById('ib-badge');
  const sl = (launch.status||'').toLowerCase();
  if (sl.includes('go')) { badge.textContent='GO'; badge.className='go'; }
  else if (sl.includes('hold')) { badge.textContent='HOLD'; badge.className='hold'; }
  else { badge.textContent=(launch.status||'TBD').toUpperCase(); badge.className=''; }

  // Probability badge
  const probBadge = document.getElementById('ib-prob-badge');
  if (probBadge) {
    const prob = launch.probability;
    if (prob !== null && prob !== undefined && prob >= 0) {
      probBadge.textContent = prob + '%';
      probBadge.style.display = 'block';
    } else {
      probBadge.style.display = 'none';
    }
  }

  // Sub line — vehicle · provider · pad
  const shorten = s => (s||'').replace('Space Launch Complex','SLC').replace('Launch Complex','LC')
    .replace('Space Force Station','SFS').replace('Kennedy Space Center','KSC')
    .replace('Cape Canaveral','CC').replace('Vandenberg Space Force Base','VSFB')
    .replace(' Space Force Base','');
  const shortenProvider = s => (s||'')
    .replace('Space Exploration Technologies Corp.','SpaceX')
    .replace('Rocket Lab USA','Rocket Lab')
    .replace('United Launch Alliance','ULA')
    .replace('Blue Origin, LLC','Blue Origin');
  document.getElementById('ib-sub').textContent =
    (launch.vehicle||'') + ' · ' + shortenProvider(launch.provider||'') + ' · ' + shorten(launch.pad||'');

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

  // Tap hint — update both the hidden compat element and the visible ib-left panel
  const _missionUrl = `/mission?id=${launch.id}&name=${encodeURIComponent(launch.name||'')}`;
  document.getElementById('ib-tap').onclick = () => { window.location = _missionUrl; };
  const ibLeft = document.getElementById('ib-left');
  if (ibLeft) ibLeft.onclick = () => { window.location = _missionUrl; };

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
    const winClose = launch.win_close || null;
    const windowEl = document.getElementById('ib-window');
    const isInstant = !winClose ||
      Math.abs(new Date(winClose).getTime() - new Date(winOpen).getTime()) < 60000;

    if (isInstant) {
      if (windowEl) windowEl.style.visibility = 'visible';
      document.getElementById('ib-win-open').textContent = '—:—';
      document.getElementById('ib-win-close').textContent = '—:—';
      document.getElementById('ib-win-label').textContent = 'LAUNCH TIME';
    } else {
      if (windowEl) windowEl.style.visibility = 'visible';
      if (winOpen) {
        document.getElementById('ib-win-open').textContent =
          new Date(winOpen).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz,hour12:false});
      }
      document.getElementById('ib-win-close').textContent =
        new Date(winClose).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz,hour12:false});
      const dotEl = document.getElementById('ib-win-dot');
      if (dotEl) {
        const openMs  = new Date(winOpen).getTime();
        const t0Ms    = new Date(t0).getTime();
        const closeMs = new Date(winClose).getTime();
        const pct = Math.min(100, Math.max(0, (t0Ms - openMs) / (closeMs - openMs) * 100));
        dotEl.style.left = pct + '%';
      }
    }
  }

  // Weather
  const wx = state.weather;
  if (wx) {
    const useCelsius = state.settings?.temp_unit === 'c';
    document.getElementById('ib-temp').textContent   = useCelsius ? Math.round(wx.temp_c)+'°C' : Math.round(wx.temp_f)+'°F';
    document.getElementById('ib-wind').textContent   = Math.round(wx.wind_speed);
    document.getElementById('ib-cloud').textContent  = (wx.cloud_cover||0)+'%';
    
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
      if (!state.buriedLaunchIds.includes(launch.id)) state.buriedLaunchIds.push(launch.id);
      fetchLaunches(true);
      return;
    }

    console.log(`[${ts()}] Missed launch detected — starting cooldown`);
    state.launchTriggered     = true;
    state.launchComplete      = true;
    state.rocketOffscreen     = true;
    if (!state.buriedLaunchIds.includes(launch.id)) state.buriedLaunchIds.push(launch.id);
    state.launchedMissionName = launch.name || '';
    state._lastLaunchT0       = launch.t0 || null;
    state._lastLaunchVehicle  = launch.vehicle || '';

    // Fetch latest launches to determine the next mission
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
  // Capture launched mission data NOW so drawMilestoneTimeline fallback works
  // during the animation and immediately after postLaunchCooldown starts
  const _launching = currentLaunch();
  if (_launching) {
    state._lastLaunchT0      = _launching.t0 || null;
    state._lastLaunchVehicle = _launching.vehicle || '';
  }
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
      if (_launched && !state.buriedLaunchIds.includes(_launched.id)) state.buriedLaunchIds.push(_launched.id);
      state.launchedMissionName = _launched ? (_launched.name || '') : '';
      state._lastLaunchT0       = _launched ? (_launched.t0 || null) : null;
      state._lastLaunchVehicle  = _launched ? (_launched.vehicle || '') : '';
      state.postLaunchCooldown  = true;
      state.cooldownEndsAt      = Date.now() + 10 * 60 * 1000;
      saveState(); // persist immediately so navigation away doesn't lose cooldown
      // Invalidate cache then fetch fresh data from the single source
      const _afterLaunchFetch = () => fetch('/api/data').then(r => r.json()).then(data => {
        const all    = data.launches || [];
        const prevId = _launched ? _launched.id : null;
        const next   = all.find(l => l.id !== prevId) || all[1] || all[0];
        state.nextMissionName = next ? (next.name || '') : '';
        state.nextMissionT0   = next ? (next.t0 || null) : null;
      }).catch(() => {});
      if (!state.testMode) {
        fetch('/api/launches/invalidate', { method: 'POST' })
          .then(_afterLaunchFetch).catch(() => {});
      } else {
        _afterLaunchFetch();
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

// Single data fetch — all pages use /api/data as the one source of truth.
// Add ?testlaunch=N to the URL to use /api/test-launch?secs=N instead.
const _testSecs = new URLSearchParams(location.search).get('testlaunch');
const _dataUrl  = _testSecs ? `/api/test-launch?secs=${_testSecs}` : '/api/data';

async function fetchData(afterLaunch=false) {
  try {
    const res  = await fetch(_dataUrl);
    const data = await res.json();

    const newLaunches = data.launches || [];
    if (newLaunches.length === 0 && state.launches.length > 0) return;

    state.launches    = newLaunches;
    state.weather     = data.weather  || state.weather;
    state.settings    = data.settings || state.settings;
    state.lastFetchAt = Date.now();

    if (afterLaunch) {
      const newLaunch = state.launches.find(l => !state.buriedLaunchIds.includes(l.id)) || state.launches[0];
      state.currentIdx      = newLaunch ? state.launches.indexOf(newLaunch) : 0;
      state.launchTriggered = false;
      state.isLaunching     = false;
      state.rocketOffscreen = false;
      state.launchComplete  = false;
      state.rocketY         = PAD_Y_BASE;
      state.flameParticles  = [];
      showNotification('NEXT MISSION');
    } else {
      const firstValid = state.launches.findIndex(l => !state.buriedLaunchIds.includes(l.id));
      state.currentIdx = firstValid >= 0 ? firstValid : 0;
    }

    // Update probability badge directly from launch data (no separate /api/ll2 call)
    const launch = currentLaunch();
    if (launch?.probability != null) {
      const prob      = launch.probability;
      const pc        = prob >= 80 ? '#00e87a' : prob >= 50 ? '#ffd93d' : '#ff4422';
      const probBadge = document.getElementById('ib-prob-badge');
      if (probBadge) {
        probBadge.textContent  = prob + '%';
        probBadge.style.display      = 'block';
        probBadge.style.color        = pc;
        probBadge.style.borderColor  = pc;
      }
    }
  } catch(e) {
    console.error('fetchData error:', e);
  }
}

// Thin wrapper so existing call-sites (fetchLaunches(true) etc.) still work.
async function fetchLaunches(afterLaunch=false) { return fetchData(afterLaunch); }

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
  const bw = 88, bh = 22;
  const bx = W - bw - 6, by = 5;

  // Background
  ctx.fillStyle = '#080c12';
  ctx.fillRect(bx, by, bw, bh);

  // 2px green border
  ctx.strokeStyle = '#00e87a';
  ctx.lineWidth = 2;
  ctx.strokeRect(bx + 1, by + 1, bw - 2, bh - 2);

  // Text
  ctx.fillStyle = '#00e87a';
  ctx.font = '7px "Press Start 2P"';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('> SETTINGS', bx + bw / 2, by + bh / 2);
  ctx.textBaseline = 'alphabetic';
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
  const launch = currentLaunch() || (state.postLaunchCooldown ? { t0: state._lastLaunchT0, vehicle: state._lastLaunchVehicle } : null);
  if (!launch || !launch.t0) return;
  const cd = computeCountdown(launch.t0);
  const elapsed = (Date.now() - new Date(launch.t0).getTime()) / 1000;
  // Show timeline from T-30min until end of milestones sequence (~75 min post launch)
  if (cd && cd !== 'LAUNCHED' && cd.total_seconds > 1800) return;
  if (elapsed > 4500) return;
  const milestones = getMilestones(launch.vehicle || '');
  // currentIdx = index of the next upcoming milestone (first one not yet reached)
  let currentIdx = milestones.findIndex(m => elapsed < m.t);
  if (currentIdx === -1) currentIdx = milestones.length - 1; // all done

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

    const isDone    = elapsed >= m.t;
    const isCurrent = i === currentIdx && !isDone;
    const dist      = i - currentIdx;
    const opacity   = opacities[String(dist)] ?? 0.15;
    const scale     = scales[String(dist)] ?? 0.6;

    // Connecting line
    const ni = i + 1;
    if (visible.includes(ni) && ni < milestones.length) {
      const ny = centerY + ni*spacing - _tlSmooth;
      if (ny < 368) {
        const lineTop = y + 7;
        const lineBot = Math.min(ny - 7, 365);
        const lineLen = lineBot - lineTop;
        if (isDone) {
          // Fill based on progress toward next milestone
          const nextM = milestones[ni];
          const progress = Math.min(1, Math.max(0, (elapsed - m.t) / (nextM.t - m.t)));
          const fillY = lineTop + lineLen * progress;
          // Black outline behind green line
          ctx.strokeStyle = `rgba(0,0,0,0.7)`;
          ctx.lineWidth = 4;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, fillY); ctx.stroke();
          // Green filled portion
          ctx.strokeStyle = `rgba(0,232,122,${opacity*0.8})`;
          ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, fillY); ctx.stroke();
          // Gray remaining portion
          if (fillY < lineBot) {
            ctx.strokeStyle = `rgba(0,0,0,0.5)`;
            ctx.lineWidth = 3;
            ctx.beginPath(); ctx.moveTo(dotX, fillY); ctx.lineTo(dotX, lineBot); ctx.stroke();
            ctx.strokeStyle = `rgba(255,255,255,${opacity*0.25})`;
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(dotX, fillY); ctx.lineTo(dotX, lineBot); ctx.stroke();
          }
        } else {
          ctx.strokeStyle = `rgba(0,0,0,0.5)`;
          ctx.lineWidth = 3;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, lineBot); ctx.stroke();
          ctx.strokeStyle = `rgba(255,255,255,${opacity*0.25})`;
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, lineBot); ctx.stroke();
        }
      }
    }

    // Dot — black halo behind for contrast
    const r = Math.max(2, Math.round(5*scale));
    ctx.fillStyle = 'rgba(0,0,0,0.75)';
    ctx.beginPath(); ctx.arc(dotX, y, r+2, 0, Math.PI*2); ctx.fill();
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
      ctx.strokeStyle=`rgba(255,255,255,${opacity*0.7})`;
      ctx.lineWidth=1.5;
      ctx.beginPath();ctx.arc(dotX,y,r,0,Math.PI*2);ctx.stroke();
    }

    // Labels — shadow for readability against bright backgrounds
    const ls=Math.max(5,Math.round(9*scale));
    const ts=Math.max(4,Math.round(6*scale));
    ctx.textAlign='right';
    ctx.shadowColor = 'rgba(0,0,0,0.95)';
    ctx.shadowBlur = 4;
    ctx.font=`bold ${ls}px Courier New`;
    ctx.fillStyle=isCurrent?`rgba(255,211,61,${opacity})`:isDone?`rgba(0,232,122,${opacity})`:`rgba(255,255,255,${opacity})`;
    ctx.fillText(m.label, dotX-12, y+3);
    ctx.font=`${ts}px Courier New`;
    ctx.fillStyle=`rgba(255,255,255,${opacity*0.7})`;
    ctx.fillText(tStr(m.t), dotX-12, y+ls+4);
    ctx.shadowBlur = 0;
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
  try {

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
  drawVAB();
  // drawFences();
  drawMLPRocket();      // ← Next rocket behind MLP
  drawMLP();            // ← MLP over its rocket
  drawRocket();         // ← Active pad rocket (behind tower)
  drawUmbilicals();     // ← Umbilical arms (between rocket and tower)
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
  } catch(e) { console.error('[render]', e); }
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

function startPolling() {
  // Refresh all data every 5 minutes from the single /api/data source
  setInterval(() => {
    if (!state.isLaunching && !state.postLaunchCooldown) {
      fetchData().then(() => showNotification('DATA UPDATED'));
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


  // Settings button tap zone — matches drawGearIcon: bx = W-94, by = 5, bw = 88, bh = 22
  if (x > W - 100 && x < W - 6 && y > 5 && y < 27) {
    window.location = '/settings';
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
//  STATE PERSISTENCE — survive page navigation
// ─────────────────────────────────────────────────────────────────────────────
function saveState() {
  try {
    localStorage.setItem('lt_state', JSON.stringify({
      postLaunchCooldown:  state.postLaunchCooldown,
      cooldownEndsAt:      state.cooldownEndsAt,
      buriedLaunchIds:     state.buriedLaunchIds,
      launchedMissionName: state.launchedMissionName,
      nextMissionName:     state.nextMissionName,
      nextMissionT0:       state.nextMissionT0,
      _lastLaunchT0:       state._lastLaunchT0,
      _lastLaunchVehicle:  state._lastLaunchVehicle,
      _savedAt:            Date.now(),
    }));
  } catch(e) {}
}

function restoreState() {
  try {
    const saved = JSON.parse(localStorage.getItem('lt_state') || 'null');
    // Discard saves older than 24 hours to prevent permanent stale state
    if (saved && Date.now() - (saved._savedAt || 0) > 86400000) {
      localStorage.removeItem('lt_state'); return;
    }
    if (!saved) return;
    // Only restore cooldown if it hasn't expired
    if (saved.postLaunchCooldown && Date.now() < saved.cooldownEndsAt) {
      state.postLaunchCooldown  = true;
      state.cooldownEndsAt      = saved.cooldownEndsAt;
      state.launchedMissionName = saved.launchedMissionName || '';
      state.nextMissionName     = saved.nextMissionName || '';
      state.nextMissionT0       = saved.nextMissionT0 || null;
      state._lastLaunchT0       = saved._lastLaunchT0 || null;
      state._lastLaunchVehicle  = saved._lastLaunchVehicle || '';
      state.rocketOffscreen     = true;
      state.launchComplete      = true;
      state.launchTriggered     = true;
    }
    if (Array.isArray(saved.buriedLaunchIds)) state.buriedLaunchIds = saved.buriedLaunchIds;
  } catch(e) {}
}

//  BOOT
// ─────────────────────────────────────────────────────────────────────────────
(async function boot() {
  await loadAssets();
  spawnBirds();
  spawnCars();
  restoreState();
  await fetchData();
  initWeatherParticles();
  startPolling();
  // Persist state every 5 seconds
  setInterval(saveState, 5000);
  requestAnimationFrame(render);
  console.log(`[${ts()}] Launch Countdown Phase 2 ready`);
})();