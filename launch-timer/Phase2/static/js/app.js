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
  vab:             'ground-VAB.png',
  launchTower:     'ground-LaunchPad.png',
  launchPad:       'ground-LaunchPad.png',
  floodlight:      'ground-floodlight.png',
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
  rocket_kinetica:     'rocket-Kinetica.png',
  rocket_falcon1st:    'rocket-Falcon1st.png',
  rocket_placeholder:  'rocket-placeholder.png',
  moon:                'moon.png',
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
  settings:    { temp_unit: 'f', time_format: 'local' },
  // Countdown / launch
  launchTriggered: false,     // ← THE FIX: set true at T-0, reset on new mission
  isLaunching:     false,
  launchFrame:     0,
  rocketY:         340,       // current rocket base Y during launch
  rocketOffscreen: false,
  launchComplete:  false,

  // Rocket flame particles
  flameParticles:  [],
  trenchParticles: [],
  ventParticles:   [],
  flameIntensity:  0,

  // Smoke (pre-launch vent on pad)
  smokeFrame: 0,

  // Clouds — y kept between 30–130 (tower top is ~160)
  clouds: [
    { x:  80, y:  35, size: 1.4 },
    { x: 240, y: 125, size: 0.6 },
    { x: 380, y:  65, size: 1.0 },
    { x: 520, y: 115, size: 0.5 },
    { x: 640, y:  45, size: 1.3 },
    { x: 760, y:  90, size: 0.7 },
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
  dataAge: 0,          // seconds since server last fetched from LL2 (from age_seconds in /api/data)
  postLaunchCooldown:   false,
  cooldownEndsAt:       0,
  launchedMissionName:  '',
  nextMissionName:      '',
  nextMissionT0:        null,
  buriedLaunchIds: [],

  // RTLS booster return animation
  rtlsActive:    false,
  rtlsFrame:     0,
  rtlsBoosterY:  -200,   // starts offscreen above

  // Notification banner
  notification: null,

  now: Date.now(),
};

// ─────────────────────────────────────────────────────────────────────────────
//  OFFSCREEN CACHE — static layers rendered once, blitted each frame
// ─────────────────────────────────────────────────────────────────────────────
function makeOffscreen(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

// Grass + road — completely static, render once
let _grassCache = null;
function getGrassCache() {
  if (_grassCache) return _grassCache;
  _grassCache = makeOffscreen(W, H);
  const g = _grassCache.getContext('2d');
  // Grass base first
  g.fillStyle = '#5a8c3a'; g.fillRect(0, 365, W, BAR_Y - 365);
  // Road on top of grass
  g.fillStyle = '#3a3a3a'; g.fillRect(0, ROAD_Y, W, 18);
  g.fillStyle = '#5a5a5a'; g.fillRect(0, ROAD_Y, W, 2);
  g.fillStyle = '#5a5a5a'; g.fillRect(0, ROAD_Y+16, W, 2);
  g.fillStyle = '#6a6a3a';
  for (let x = 0; x < W; x += 20) g.fillRect(x, ROAD_Y+8, 10, 2);
  // Grass details
  const rng = mulberry32(123);
  const colors = ['#4a7c2a','#6a9c4a','#5a8c3a','#3a6c1a'];
  for (let i = 0; i < 400; i++) {
    const gx = rng() * W;
    const gy = 368 + rng() * (BAR_Y - 368 - 20);
    g.fillStyle = colors[Math.floor(rng() * 4)];
    const style = Math.floor(rng() * 4);
    if (style === 0)      { g.fillRect(gx, gy-3, 1, 3); }
    else if (style === 1) { g.fillRect(gx, gy, 2, 3); }
    else if (style === 2) { g.fillRect(gx, gy, 1, 1); }
    else                  { g.fillRect(gx, gy-3, 1, 3); }
  }
  return _grassCache;
}

// Stars — static per night session, invalidated on sky phase change
let _starsCache = null;
let _starsSkyPhase = null;
function getStarsCache() {
  const phase = _getSkyPhase();
  if (_starsCache && _starsSkyPhase === phase) return _starsCache;
  _starsSkyPhase = phase;
  if (phase !== 'night') { _starsCache = null; return null; }
  _starsCache = makeOffscreen(W, H);
  const g = _starsCache.getContext('2d');
  g.fillStyle = '#ffffff';
  const rng = mulberry32(42);
  for (let i = 0; i < 60; i++) {
    const sx = rng() * W;
    const sy = rng() * 340;
    const sz = rng() > 0.7 ? 2 : 1;
    g.fillRect(sx, sy, sz, sz);
  }
  return _starsCache;
}

// Spotlight beams — static geometry, invalidated only on isNight() change
let _spotlightCache = null;
let _spotlightNight = null;
function getSpotlightCache() {
  const night = isNight();
  if (_spotlightCache && _spotlightNight === night) return _spotlightCache;
  _spotlightNight = night;
  _spotlightCache = makeOffscreen(W, H);
  const g = _spotlightCache.getContext('2d');

  const groundY = PAD_Y_BASE + 22;
  const targetX = NOZZLE_X + 10;
  const targetY = NOZZLE_Y - 40;
  const lx      = targetX - 110;
  const rx      = targetX + 110;
  const fh = 40;
  const fw = IMG.floodlight ? Math.round(IMG.floodlight.width * (fh / IMG.floodlight.height)) : 12;
  const lCX = lx + fw / 2;
  const rCX = rx + fw / 2;
  const headY = groundY - fh / 2;

  if (night) {
    g.globalAlpha = 0.28;
    const g1 = g.createLinearGradient(lCX, headY, targetX, targetY);
    g1.addColorStop(0, '#ffffcc'); g1.addColorStop(1, 'rgba(255,255,180,0)');
    g.fillStyle = g1;
    g.beginPath(); g.moveTo(lCX-4, headY); g.lineTo(targetX-18, targetY); g.lineTo(targetX+18, targetY); g.lineTo(lCX+4, headY); g.fill();
    const g2 = g.createLinearGradient(rCX, headY, targetX, targetY);
    g2.addColorStop(0, '#ffffcc'); g2.addColorStop(1, 'rgba(255,255,180,0)');
    g.fillStyle = g2;
    g.beginPath(); g.moveTo(rCX-4, headY); g.lineTo(targetX-18, targetY); g.lineTo(targetX+18, targetY); g.lineTo(rCX+4, headY); g.fill();
    g.globalAlpha = 1;
  }

  // Floodlight images
  if (IMG.floodlight) {
    g.drawImage(IMG.floodlight, lx, groundY - fh, fw, fh);
    g.save();
    g.translate(rx + fw, groundY - fh);
    g.scale(-1, 1);
    g.drawImage(IMG.floodlight, 0, 0, fw, fh);
    g.restore();
  }
  return _spotlightCache;
}

// Pad 2 flood light beams — static geometry, invalidated on night change
let _pad2BeamCache = null;
let _pad2BeamNight = null;
function getPad2BeamCache(sl2lx, sl2rx, sl2groundY, sl2targetX, sl2targetY) {
  const night = isNight();
  if (_pad2BeamCache && _pad2BeamNight === night) return _pad2BeamCache;
  _pad2BeamNight = night;
  _pad2BeamCache = makeOffscreen(W, H);
  if (!night) return _pad2BeamCache;
  const g = _pad2BeamCache.getContext('2d');
  const fh2 = 18;
  const fw2 = IMG.floodlight ? Math.round(IMG.floodlight.width * (fh2 / IMG.floodlight.height)) : 8;
  const sl2beamLX = sl2lx + fw2 / 2 - 9;
  const sl2beamRX = sl2rx + fw2 / 2 - 9;
  const sl2headY  = sl2groundY - fh2 / 2;
  g.globalAlpha = 0.28;
  const sg1 = g.createLinearGradient(sl2beamLX, sl2headY, sl2targetX, sl2targetY);
  sg1.addColorStop(0, '#ffffcc'); sg1.addColorStop(1, 'rgba(255,255,180,0)');
  g.fillStyle = sg1;
  g.beginPath(); g.moveTo(sl2beamLX-3, sl2headY); g.lineTo(sl2targetX-8, sl2targetY); g.lineTo(sl2targetX+8, sl2targetY); g.lineTo(sl2beamLX+3, sl2headY); g.fill();
  const sg2 = g.createLinearGradient(sl2beamRX, sl2headY, sl2targetX, sl2targetY);
  sg2.addColorStop(0, '#ffffcc'); sg2.addColorStop(1, 'rgba(255,255,180,0)');
  g.fillStyle = sg2;
  g.beginPath(); g.moveTo(sl2beamRX-3, sl2headY); g.lineTo(sl2targetX-8, sl2targetY); g.lineTo(sl2targetX+8, sl2targetY); g.lineTo(sl2beamRX+3, sl2headY); g.fill();
  g.globalAlpha = 1;
  return _pad2BeamCache;
}

// Aviation light glow — cached per combined blink state of both towers
let _aviCache = null;
let _aviCacheKey = null;

function _drawAviLight(g, x, y, blink, size=1) {
  if (blink) {
    const gl = g.createRadialGradient(x, y, 0, x, y, 8*size);
    gl.addColorStop(0, 'rgba(255,255,255,0.9)'); gl.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gl; g.beginPath(); g.arc(x, y, 8*size, 0, Math.PI*2); g.fill();
    g.fillStyle = '#ffffff';
    g.beginPath(); g.arc(x, y, 3*size, 0, Math.PI*2); g.fill();
  } else {
    g.fillStyle = 'rgba(180,180,180,0.3)';
    g.beginPath(); g.arc(x, y, 2*size, 0, Math.PI*2); g.fill();
  }
}

function getAviCache(blink1, blink2) {
  const key = `${blink1}|${blink2}`;
  if (_aviCache && _aviCacheKey === key) return _aviCache;
  _aviCacheKey = key;
  _aviCache = makeOffscreen(W, H);
  const g = _aviCache.getContext('2d');
  // Main tower lights (size=1)
  _drawAviLight(g, 562, 200, blink1, 1);
  _drawAviLight(g, 562, 270, blink1, 1);
  // Pad 2 tower lights — smaller to match distant scale
  _drawAviLight(g, 307, 320, blink2, 0.45);
  _drawAviLight(g, 307, 290, blink2, 0.45);  // ← adjust 0.45 to resize
  return _aviCache;
}

// Cloud shape cache — keyed by color+size, max 16 entries
const MAX_CLOUD_CACHE = 16;
let _cloudCaches = {};
let _cloudCacheKeys = [];
function getCloudCache(col, size=1) {
  const key = col + size;
  if (_cloudCaches[key]) return _cloudCaches[key];
  if (_cloudCacheKeys.length >= MAX_CLOUD_CACHE) {
    const evict = _cloudCacheKeys.shift();
    delete _cloudCaches[evict];
  }
  const bw = Math.round(96 * size), bh = Math.round(44 * size);
  const cc = makeOffscreen(bw, bh);
  const g = cc.getContext('2d');

  const puffs = [
    [14, 34, 14,  9],
    [34, 30, 18, 12],
    [58, 34, 14,  9],
    [20, 24, 13, 11],
    [46, 24, 13, 11],
    [34, 16, 14, 12],
    [24, 20, 10,  9],
    [48, 20, 10,  9],
  ];

  // Shadow pass
  g.globalAlpha = 0.18;
  g.fillStyle = 'rgba(0,0,0,1)';
  puffs.forEach(([x,y,rx,ry]) => {
    g.beginPath(); g.ellipse(x*size+2, y*size+2, rx*size, ry*size, 0, 0, Math.PI*2); g.fill();
  });

  // Main cloud
  g.globalAlpha = 1;
  g.fillStyle = col;
  puffs.forEach(([x,y,rx,ry]) => {
    g.beginPath(); g.ellipse(x*size, y*size, rx*size, ry*size, 0, 0, Math.PI*2); g.fill();
  });

  // Highlight sheen
  g.globalAlpha = 0.22;
  g.fillStyle = 'rgba(255,255,255,1)';
  [[28,14,10,7],[40,10,8,6]].forEach(([x,y,rx,ry]) => {
    g.beginPath(); g.ellipse(x*size, y*size, rx*size, ry*size, 0, 0, Math.PI*2); g.fill();
  });
  g.globalAlpha = 1;

  _cloudCaches[key] = cc;
  _cloudCacheKeys.push(key);
  return cc;
}

// ─────────────────────────────────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function ts() {
  return new Date().toLocaleTimeString('en-US', { hour12: false });
}

function getHour() {
  const fmt = state.settings?.time_format;
  if (fmt === 'utc') return new Date().getUTCHours();
  if (fmt === 'site') {
    const tz = state.settings?.site === 'vandenberg' ? 'America/Los_Angeles' : 'America/New_York';
    const h = parseInt(new Date().toLocaleString('en-US',{hour:'numeric',hour12:false,timeZone:tz}),10);
    return h === 24 ? 0 : h;
  }
  // 'local' — use the device's actual local hour, not a hardcoded timezone
  const h = new Date().getHours();
  return h;
}

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
  const now = Date.now();
  const wx = state.weather;
  const fmt = state.settings?.time_format;

  // Only use launch-site sunrise/sunset when user is in site or UTC mode.
  // In local mode the site times are wrong for the user's location — use device clock.
  let srMs = null, ssMs = null;
  if (fmt !== 'local') {
    if (wx.sunrise) try { srMs = new Date(wx.sunrise).getTime(); } catch(e) {}
    if (wx.sunset)  try { ssMs = new Date(wx.sunset).getTime();  } catch(e) {}
  }

  if (srMs && ssMs) {
    const fade = 45 * 60 * 1000; // 45 min fade window
    if (now < srMs - fade)               return 'night';
    if (now < srMs)                      return 'sunrise';
    if (now < ssMs - fade)               return 'day';
    if (now < ssMs)                      return 'sunset';
    return 'night';
  }

  // Hour-based fallback (also used for local mode)
  const h = getHour();
  if (h >= 10 && h < 18) return 'day';
  if (h >= 18 && h < 20) return 'sunset';
  if (h >= 6  && h < 10) return 'sunrise';
  return 'night';
}

function getSkyColors() {
  const cond = state.weather.condition;
  const phase = _getSkyPhase();
  const night = phase === 'night';
  const isRainy = ['rain','thunderstorm','light_rain'].includes(cond);
  // All overcast/weather conditions still respect night
  if (isRainy) return night
    ? { sky:'#0d1520', ocean:'#070d18', cloud:'#252830' }
    : { sky:'#3a4a5a', ocean:'#0d1a2e', cloud:'#505050' };
  if (cond === 'cloudy') return night
    ? { sky:'#0d1a2a', ocean:'#080e1a', cloud:'#1a2030' }
    : { sky:'#7a9ab8', ocean:'#1a5b6e', cloud:'#b0b0b0' };
  if (cond === 'fog') return night
    ? { sky:'#0d1520', ocean:'#080e18', cloud:'#1e2530' }
    : { sky:'#8a9aaa', ocean:'#1a5b6e', cloud:'#c0c8d0' };
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

  // Stars — cached offscreen canvas
  if (isNight() && !['cloudy','rain','thunderstorm','fog'].includes(state.weather.condition)) {
    const sc = getStarsCache();
    if (sc) ctx.drawImage(sc, 0, 0);
  }

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
function drawMoon() {
  if (!IMG.moon) return;
  if (!isNight()) return;
  if (['cloudy','rain','thunderstorm','fog'].includes(state.weather.condition)) return;

  const wx = state.weather;
  const now = Date.now();

  // Get sunset/sunrise ms
  let srMs = null, ssMs = null;
  if (wx.sunrise) try { srMs = new Date(wx.sunrise).getTime(); } catch(e) {}
  if (wx.sunset)  try { ssMs = new Date(wx.sunset).getTime();  } catch(e) {}

  let t;
  if (srMs && ssMs) {
    // Night spans sunset → (next) sunrise
    const nightLen = (srMs + 86400000) - ssMs;
    const intoNight = now - ssMs;
    t = Math.max(0, Math.min(1, intoNight / nightLen));
  } else {
    // Fallback: assume night runs 20:00–06:00 (10 hrs), derive t from local hour
    const d = new Date(now);
    const h = d.getHours() + d.getMinutes() / 60;
    const nightStart = 20, nightEnd = 30; // 30 = 6:00 next day
    const hWrapped = h < nightStart ? h + 24 : h;
    t = Math.max(0, Math.min(1, (hWrapped - nightStart) / (nightEnd - nightStart)));
  }

  // Arc: rises right, sets left, peaks at midnight
  const moonSize = 28;
  const mx = W * 0.85 - t * (W * 0.72);
  const my = 280 - Math.sin(t * Math.PI) * 230;

  // Only draw if above the grass line
  if (my + moonSize > 360) return;

  // Soft glow halo
  const glow = ctx.createRadialGradient(mx, my, moonSize * 0.6, mx, my, moonSize * 1);
  glow.addColorStop(0, 'rgba(220,220,180,0.15)');
  glow.addColorStop(1, 'rgba(220,220,180,0)');
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(mx, my, moonSize * 1.25, 0, Math.PI*2); ctx.fill();

  // Moon sprite — clip to circle, preserve PNG aspect ratio
  ctx.save();
  ctx.beginPath(); ctx.arc(mx, my, moonSize, 0, Math.PI * 2); ctx.clip();
  const mAspect = IMG.moon.width / IMG.moon.height;
  const mDw = mAspect >= 1 ? moonSize * 2 : moonSize * 2 * mAspect;
  const mDh = mAspect >= 1 ? moonSize * 2 / mAspect : moonSize * 2;
  ctx.drawImage(IMG.moon, mx - mDw / 2, my - mDh / 2, mDw, mDh);
  ctx.restore();
}

function drawVAB() {
  if (!IMG.vab) return;
  // Slightly smaller + subtle haze to read as distant background
  const h = 200;
  const w = Math.round(IMG.vab.width * (h / IMG.vab.height));
  const x = -15;
  const groundY = 422;
  const y = groundY - h;
  // Alpha varies by condition to push VAB into the background
  const _cond = state.weather.condition;
  let _vabAlpha;
  if (['rain','light_rain','thunderstorm'].includes(_cond)) {
    _vabAlpha = 0.55; // fade heavily into stormy sky
  } else if (_cond === 'cloudy') {
    _vabAlpha = 0.70;
  } else if (_cond === 'fog') {
    _vabAlpha = 0.45;
  } else if (isNight()) {
    _vabAlpha = 0.72;
  } else {
    _vabAlpha = 0.88; // clear day — original
  }
  ctx.save();
  ctx.globalAlpha = _vabAlpha;
  ctx.drawImage(IMG.vab, x, y, w, h);
  ctx.restore();
}

// ─────────────────────────────────────────────────────────────────────────────
//  LAUNCH TOWER + PAD
// ─────────────────────────────────────────────────────────────────────────────
function drawLaunchTower() {
  if (IMG.launchTower) {
    const h = 250;
    const w = Math.round(IMG.launchTower.width * (h / IMG.launchTower.height));
    ctx.drawImage(IMG.launchTower, 465, 160, w, h);
  }
}

function drawLaunchPad() {
  // Skip - the pad is already included in the tower image
  // Only draw if we have a separate pad asset AND no tower
  if (IMG.launchPad && !IMG.launchTower) {
    ctx.drawImage(IMG.launchPad, 550, 325, 140, 70);
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
    { frac: 0.44, cableColors: ['#aaaaaa','#cccccc','#aaaaaa'] },
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
  // Spotlight beams + floodlight images — cached offscreen
  ctx.drawImage(getSpotlightCache(), 0, 0);

  // Aviation lights — offset pad 2 by 1500ms so they don't sync
  const blink1 = (Date.now() % 3000) < 500;
  const blink2 = ((Date.now() + 1500) % 3000) < 500;
  ctx.drawImage(getAviCache(blink1, blink2), 0, 0);
}

// ─────────────────────────────────────────────────────────────────────────────
//  CLOUDS
// ─────────────────────────────────────────────────────────────────────────────
function drawClouds() {
  const col = getSkyColors().cloud;
  state.clouds.forEach(c => {
    const size = c.size || 1;
    const cc = getCloudCache(col, size);
    ctx.drawImage(cc, c.x - 10, c.y);
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
  if (v.includes('gslv') || v.includes('geosynchronous')) return 'rocket_gslv';
  if (v.includes('falcon heavy'))  return 'rocket_falconheavy';
  if (v.includes('falcon'))        return 'rocket_falcon9';
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
  if (v.includes('minotaur'))                                                            return 'rocket_minotaur';
  if (v.includes('neutron'))                                                             return 'rocket_neutron';
  if (v.includes('rfa') || v.includes('rfa one'))                                       return 'rocket_rfaone';
  if (v.includes('spectrum'))                                                            return 'rocket_spectrum';
  if (v.includes('kinetica'))                                                            return 'rocket_kinetica';
  if (v.includes('tianlong') || v.includes('sky dragon'))                               return 'rocket_tianlong';
  return 'rocket_placeholder';
}

// y is tuned per-rocket: nozzle must visually land at PAD_Y_BASE (359).
// PNGs with transparent padding below the nozzle need y > PAD_Y_BASE-h so the
// transparent region sinks below the ground line.
const ROCKET_CONFIG = {
  rocket_falcon9:     { pad: { x: 439, y: 211, h: 155, fx: -33, fy: -12 }, te: { x: 250, y: 291, h: 71 } },
  rocket_atlas:       { pad: { x: 462, y: 196, h: 183, fy: -26 },          te: { x: 261, y: 292, h: 79 } },
  rocket_vulcan:      { pad: { x: 472, y: 200, h: 153 },                    te: { x: 265, y: 291, h: 67 } },
  rocket_electron:    { pad: { x: 485, y: 252, h: 116, fy: -18 },          te: { x: 268, y: 309, h: 60 } },
  rocket_ng:          { pad: { x: 452, y: 159, h: 216, fx: 2, fy: -20 },   te: { x: 252, y: 261, h: 109 } },
  rocket_kairos:      { pad: { x: 480, y: 238, h: 127, fy: -10 },          te: { x: 267, y: 304, h: 60 } },
  rocket_longmarch:   { pad: { x: 471, y: 207, h: 156, fy: -10 },          te: { x: 263, y: 290, h: 74 } },
  rocket_generic:     { pad: { x: 440, y: 204, h: 155 },                    te: { x: 128, y: 204, h: 155 } },
  rocket_firefly:     { pad: { x: 469, y: 215, h: 164, fy: -25 },          te: { x: 258, y: 284, h: 91 } },
  rocket_starship:    { pad: { x: 429, y: 122, h: 280, fy: -40 },          te: { x: 242, y: 247, h: 138 } },
  rocket_soyuz:       { pad: { x: 480, y: 223, h: 131 },                    te: { x: 268, y: 297, h: 62 } },
  rocket_soyuz5:      { pad: { x: 480, y: 228, h: 131, fy: -3 },           te: { x: 266, y: 296, h: 66 } },
  rocket_ariane6:     { pad: { x: 477, y: 220, h: 133 },                    te: { x: 265, y: 292, h: 67 } },
  rocket_sls:         { pad: { x: 509, y: 161, h: 194 },                    te: { x: 280, y: 272, h: 87 } },
  rocket_gslv:        { pad: { x: 479, y: 221, h: 132 },                    te: { x: 268, y: 297, h: 62 } },
  rocket_longmarch12: { pad: { x: 470, y: 218, h: 155, fy: -17 },          te: { x: 261, y: 294, h: 76 } },
  rocket_longmarch2d: { pad: { x: 476, y: 218, h: 147, fy: -12 },          te: { x: 263, y: 290, h: 73 } },
  rocket_vegaC:       { pad: { x: 459, y: 190, h: 187, fy: -22 },          te: { x: 258, y: 284, h: 89 } },
  rocket_jielong:     { pad: { x: 460, y: 191, h: 189, fx: 1, fy: -26 },   te: { x: 257, y: 281, h: 88 } },
  rocket_falconheavy: { pad: { x: 477, y: 213, h: 143, fx: -2 },           te: { x: 265, y: 296, h: 65 } },
  rocket_minotaur:    { pad: { x: 485, y: 244, h: 115, fy: -9 },           te: { x: 268, y: 304, h: 60 } },
  rocket_neutron:     { pad: { x: 483, y: 235, h: 119 },                    te: { x: 267, y: 302, h: 60 } },
  rocket_rfaone:      { pad: { x: 478, y: 244, h: 127, fy: -17 },          te: { x: 266, y: 305, h: 60 } },
  rocket_spectrum:    { pad: { x: 476, y: 225, h: 142, fy: -13 },          te: { x: 264, y: 296, h: 69 } },
  rocket_tianlong:    { pad: { x: 475, y: 226, h: 136, fy: -9 },           te: { x: 265, y: 298, h: 65 } },
  rocket_kinetica:    { pad: { x: 506, y: 240, h: 109 },                    te: { x: 277, y: 299, h: 60 } },
  rocket_placeholder: { pad: { x: 485, y: 252, h: 115 },                    te: { x: 267, y: 309, h: 60 } },
};
const PAD_Y_BASE = 359
const NOZZLE_X   = 515;
const NOZZLE_Y   = 280;

function drawBackgroundPad() {
  if (!IMG.launchTower) return;

  const sc      = 0.40;   // scale vs main pad
  const groundY = 385;
  const padX    = 300;    // centre X

  const th = Math.round(289 * sc);
  const tw = Math.round(IMG.launchTower.width * (th / IMG.launchTower.height));
  const tx = padX - tw / 2;
  const ty = groundY - th;

  // Next rocket sitting on this pad — only show if there IS a next queued launch
  const nextLaunch = state.launches[state.currentIdx + 1] || null;
  const vehicle2   = nextLaunch ? (nextLaunch.vehicle || '') : '';
  const assetKey2  = vehicle2 ? getRocketAssetKey(vehicle2) : null;
  const rocketImg  = assetKey2 ? IMG[assetKey2] : null;
  let rocketMidY = ty + Math.round(th * 0.55);
  if (rocketImg && vehicle2) {
    const rCfg = ROCKET_CONFIG[assetKey2] || ROCKET_CONFIG.rocket_generic;
    const te   = rCfg.te || rCfg.pad;  // use te (hand-tuned for pad 2) directly
    const rh   = te.h;
    const rw   = Math.round(rocketImg.width * (rh / rocketImg.height));
    rocketMidY = te.y + Math.round(rh * 0.5);

    // Draw rocket FIRST so tower structure renders in front of it
    ctx.globalAlpha = 0.82;
    ctx.drawImage(rocketImg, te.x, te.y, rw, rh);
    ctx.globalAlpha = 1;
  }

  // Tower drawn AFTER rocket so it occludes the rocket correctly
  ctx.save();
  ctx.globalAlpha = 0.82;
  ctx.drawImage(IMG.launchTower, tx, ty, tw, th);
  ctx.globalAlpha = 1;


  // ── Vent smoke (same logic as main pad) ──
  const ventX2 = 285;
  const ventY2 = rocketMidY;
  const f2 = state.smokeFrame;
  for (let i = 0; i < 12; i++) {
    const dist    = (f2 * 0.5 + i * 6) % 100;
    const smx     = ventX2 - dist * sc;
    const smy     = ventY2 + dist * 0.08 + (i % 3 - 1) * 2;
    const opacity = 1 - dist / 100;
    if (opacity > 0.08) {
      const sz   = dist < 20 ? 4 + i % 3 : 4 + i % 3 + Math.floor(dist / 6);
      const gray = dist < 20 ? 245 : 220;
      ctx.globalAlpha = opacity * 0.7;
      ctx.fillStyle = `rgb(${gray},${gray},${gray})`;
      ctx.beginPath();
      ctx.ellipse(smx, smy, sz * sc / 2, sz * sc / 2, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.globalAlpha = 1;



  // ── Flood lights ──
  const sl2groundY = groundY - 11;
  const sl2targetX = padX - 10;
  const sl2targetY = rocketMidY - 16;
  const sl2lx      = sl2targetX - 30;
  const sl2rx      = sl2targetX + 60;

  // Beams — cached offscreen
  ctx.drawImage(getPad2BeamCache(sl2lx, sl2rx, sl2groundY, sl2targetX, sl2targetY), 0, 0);

  if (IMG.floodlight) {
    const fh2 = 18;
    const fw2 = Math.round(IMG.floodlight.width * (fh2 / IMG.floodlight.height));
    ctx.drawImage(IMG.floodlight, sl2lx - fw2/2, sl2groundY - fh2, fw2, fh2);
    ctx.save();
    ctx.translate(sl2rx - fw2/2 + fw2, sl2groundY - fh2);
    ctx.scale(-1, 1);
    ctx.drawImage(IMG.floodlight, 0, 0, fw2, fh2);
    ctx.restore();
  }

  // Haze overlay — day only (at night the rect edge is visible), skip on Pi (minor visual)
  // (removed — was causing visible box at night and cheap to omit)

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

// ─────────────────────────────────────────────────────────────────────────────
//  RTLS BOOSTER RETURN  (Return-to-Launch-Site landing animation)
//  Draws the first stage coming back down inverted, then landing ~80px left of pad
// ─────────────────────────────────────────────────────────────────────────────
function updateRTLS() {
  if (!state.rtlsActive) return;
  state.rtlsFrame++;
  // Delay ~3s before booster re-appears (60 frames @ 20fps)
  if (state.rtlsFrame < 60) return;
  const frame = state.rtlsFrame - 60;
  // Phase 1: descend from top (decelerate into landing)
  const LAND_Y = 380;  // bottom of booster sits on visual grass line
  const totalFrames = 140;
  const t = Math.min(frame / totalFrames, 1);
  const easedT = 1 - Math.pow(1 - t, 3); // ease-out cubic — fast at top, slow at bottom
  state.rtlsBoosterY = -220 + (LAND_Y + 220) * easedT;
  state.rtlsBoosterY = Math.min(state.rtlsBoosterY, 380); // never go below ground
  if (t >= 1) {
    // Landed — keep for 90 minutes then clear
    if (frame > totalFrames + (90 * 60 * 20)) {
      state.rtlsActive = false;
    }
  }
}

function spawnRTLSFlame(flameX, flameY, intensity, distToGround) {
  // Airborne jet — same core/outer particles as launch but pointing DOWN (vy positive)
  const slots = MAX_FLAME_PARTICLES - state.flameParticles.length;
  const n = Math.min(Math.floor(20 * intensity), slots);
  for (let i = 0; i < n; i++) {
    const r = Math.random();
    if (r < 0.55) {
      state.flameParticles.push({
        type: 'core',
        x: Math.round((flameX + (Math.random()-0.5) * 6) / 2) * 2,
        y: flameY,
        vx: (Math.random()-0.5) * 0.4,
        vy: 3.5 + Math.random() * 2.5,   // downward
        age: 0, life: 8 + Math.floor(Math.random() * 6), sz: 4,
      });
    } else {
      state.flameParticles.push({
        type: 'outer',
        x: Math.round((flameX + (Math.random()-0.5) * 12) / 2) * 2,
        y: flameY + Math.random() * 4,
        vx: (Math.random()-0.5) * 1.2,
        vy: 1.8 + Math.random() * 1.8,
        age: 0, life: 10 + Math.floor(Math.random() * 8), sz: 6,
      });
    }
  }
  // Trench plumes when very close to ground (last 30px)
  if (distToGround < 30) {
    const trenchIntensity = (30 - distToGround) / 30;
    const trenchSlots = 900 - state.trenchParticles.length;
    const tn = Math.min(Math.ceil(20 * trenchIntensity), trenchSlots);
    for (let i = 0; i < tn; i++) {
      const side = Math.random() < 0.5 ? -1 : 1;
      const lowRiser = Math.random() < 0.65;
      state.trenchParticles.push({
        type: 'trench_smoke',
        x: flameX + side * (28 + Math.random() * 30),
        y: PAD_Y_BASE - Math.random() * 6,
        vx: side * (1.5 + Math.random() * 5),
        vy: lowRiser ? -(0.2 + Math.random() * 1.0) : -(1.2 + Math.random() * 2.5),
        age: 0, life: 10 + Math.floor(Math.random() * 40),
        sz: 8 + Math.floor(Math.random() * 3) * 2,
        dark: Math.random() < 0.18, side,
      });
    }
  }
}

function drawRTLS() {
  if (!state.rtlsActive) return;
  if (state.rtlsFrame < 60) return;
  const frame  = state.rtlsFrame - 60;
  const LAND_X = NOZZLE_X + 220;   // right of the primary pad, stays on screen
  const y      = state.rtlsBoosterY;
  const landed = (frame / 140) >= 1;

  const img = IMG.rocket_falcon1st;
  const h        = 90;  // booster height (stage 1 only)

  // Draw booster — upright (nose up, nozzle down), bottom edge at y
  if (img) {
    const w = Math.round(img.width * (h / img.height));
    ctx.globalAlpha = 0.88;
    ctx.drawImage(img, LAND_X - w / 2, y - h, w, h);
    ctx.globalAlpha = 1;
  } else {
    ctx.fillStyle = '#e0e0e0';
    ctx.fillRect(LAND_X - 6, y - h, 12, h);
  }

  // Landing burn — use the same particle system as launch, pointing downward
  if (!landed) {
    const distToGround = PAD_Y_BASE - y;
    // Throttle up from 120px above ground (entry burn style)
    const intensity = Math.min(1, Math.max(0, (120 - distToGround) / 100));
    if (intensity > 0) {
      spawnRTLSFlame(LAND_X, y, intensity, distToGround);
    }
  }

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
  if (!assetKey) return; // no rocket asset — no venting
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
// Types:
//   'core'  — tight white/yellow jet, fast downward, narrow spread
//   'plume' — wide orange/red cloud, slower, drifts sideways
//   'smoke' — dark grey, billows sideways on ground when rocket hasn't lifted

const MAX_FLAME_PARTICLES = 280;

const FLAME_PALETTE = [
  '#ffffff', // 0 — white core
  '#ffffaa', // 1 — pale yellow
  '#ffee44', // 2 — bright yellow
  '#ffcc00', // 3 — yellow-orange
  '#ff8800', // 4 — orange
  '#ff4400', // 5 — red-orange
  '#cc2200', // 6 — dark red
  '#661100', // 7 — near-black tip
];

function spawnFlameParticles(flameX, flameY, intensity) {
  if (state.flameParticles.length >= MAX_FLAME_PARTICLES) return;
  const slots = MAX_FLAME_PARTICLES - state.flameParticles.length;
  const n = Math.min(Math.floor(30 * intensity), slots);
  const liftDist = PAD_Y_BASE - state.rocketY; // 0 on pad, grows as rocket rises
  const lifted = liftDist > 6;

  // Flame trench intensity — full at T-0, fades out gradually over 200px of altitude
  const trenchIntensity = Math.max(0, 1 - liftDist / 200);

  if (lifted) {
    // ── Rocket is airborne — downward jet only, no trench ──
    for (let i = 0; i < n; i++) {
      const r = Math.random();
      if (r < 0.55) {
        const px = Math.round((flameX + (Math.random()-0.5) * 6) / 2) * 2;
        state.flameParticles.push({
          type: 'core',
          x: px, y: flameY,
          vx: (Math.random()-0.5) * 0.4,
          vy: 3.5 + Math.random() * 2.5,
          age: 0, life: 8 + Math.floor(Math.random() * 6),
          sz: 4,
        });
      } else {
        const px = Math.round((flameX + (Math.random()-0.5) * 14) / 2) * 2;
        state.flameParticles.push({
          type: 'outer',
          x: px, y: flameY + Math.random() * 4,
          vx: (Math.random()-0.5) * 1.2,
          vy: 1.8 + Math.random() * 1.8,
          age: 0, life: 12 + Math.floor(Math.random() * 8),
          sz: 6,
        });
      }
    }
  }

  // ── Flame trench — continuous sideways plumes ──
  // Steady-state: cap=220, avgLife=16 → need spawn≥220/16≈14/frame. Use 22.
  // Steady-state: cap=900, avgLife=35 → need spawn≥900/35≈26/frame. Use 35.
  // Wide life range (10-60) staggers deaths so no wave-die-respawn spurting.
  const MAX_TRENCH = 900;
  if (trenchIntensity > 0) {
    const trenchY = PAD_Y_BASE;
    const slots = MAX_TRENCH - state.trenchParticles.length;
    const tn = Math.min(Math.ceil(35 * trenchIntensity), slots);
    for (let i = 0; i < tn; i++) {
      const side = Math.random() < 0.5 ? -1 : 1;
      const isDark = Math.random() < 0.18;
      // Decouple vx and vy completely so particles don't all trace the same diagonal line.
      // 65% hug the ground (low vy), 35% rise higher — builds volume below then above.
      const lowRiser = Math.random() < 0.65;
      state.trenchParticles.push({
        type: 'trench_smoke',
        x: flameX + side * (side < 0 ? (28 + Math.random() * 22) : (62 + Math.random() * 28)),
        y: trenchY - Math.random() * 8,
        vx: side * (1.5 + Math.random() * 5.5),         // horizontal independent of vertical
        vy: lowRiser ? -(0.2 + Math.random() * 1.2)     // mostly horizontal, stays low
                     : -(1.5 + Math.random() * 2.8),    // rises moderately, not sky-high
        age: 0, life: 10 + Math.floor(Math.random() * 50),
        sz: 10 + Math.floor(Math.random() * 3) * 2,
        dark: isDark,
        side,
      });
    }
  }
}

// Called BEFORE pad/tower — trench smoke appears behind structures
function drawTrenchParticles() {
  state.trenchParticles = state.trenchParticles.filter(p => p.age < p.life);

  // snap helper — align to 2px pixel grid for crisp retro look
  const snap = v => Math.round(v / 2) * 2;

  state.trenchParticles.forEach(p => {
    const t = p.age / p.life;
    p.vx *= 0.97; p.vy *= 0.97;
    // Turbulence — breaks straight-line trajectories into billowing shapes
    p.vx += (Math.random() - 0.5) * 0.4;
    p.vy += (Math.random() - 0.5) * 0.3;
    p.x += p.vx; p.y += p.vy;
    // Blocks grow slightly as cloud billows outward
    const bsz = p.sz + Math.floor(t * 6);
    const gray = p.dark
      ? Math.floor(170 + t * 30)   // light grey: 170→200
      : Math.floor(220 + t * 30);  // almost white: 220→250
    ctx.globalAlpha = t < 0.15 ? t / 0.15 * 0.85   // fade in fast
                    : (1 - t) * 0.85;               // fade out slowly
    ctx.fillStyle = `rgb(${gray},${gray},${gray})`;
    ctx.fillRect(snap(p.x) - bsz / 2, snap(p.y) - bsz / 2, bsz, bsz);
    p.age++;
  });
  ctx.globalAlpha = 1;
}

// Called AFTER pad/tower — jet and pad smoke appear in front
function drawFlameParticles() {
  state.flameParticles = state.flameParticles.filter(p => p.age < p.life);

  state.flameParticles.filter(p => p.type === 'smoke').forEach(p => {
    const t = p.age / p.life;
    const sz = Math.round((p.sz * (1 + t * 1.4)) / 2) * 2;
    const gray = Math.floor(160 + t * 70);
    ctx.globalAlpha = (1 - t) * 0.55;
    ctx.fillStyle = `rgb(${gray},${gray},${gray})`;
    ctx.fillRect(Math.round(p.x - sz/2), Math.round(p.y - sz/4), sz, Math.round(sz * 0.55));
    p.age++; p.x += p.vx; p.y += p.vy; p.vx *= 0.96;
  });
  ctx.globalAlpha = 1;

  state.flameParticles.filter(p => p.type === 'outer').forEach(p => {
    const t = p.age / p.life;
    const ci = Math.min(3 + Math.floor(t * 5), FLAME_PALETTE.length - 1);
    const halfW = Math.max(2, Math.round((p.sz * (1.2 - t * 0.5)) / 2));
    const blockH = Math.max(2, Math.round(p.sz * (1 - t * 0.3)));
    ctx.globalAlpha = (1 - t * 0.7);
    ctx.fillStyle = FLAME_PALETTE[ci];
    ctx.fillRect(Math.round(p.x) - halfW, Math.round(p.y), halfW * 2, blockH);
    p.age++; p.x += p.vx; p.y += p.vy;
  });

  state.flameParticles.filter(p => p.type === 'core').forEach(p => {
    const t = p.age / p.life;
    const ci = Math.min(Math.floor(t * 5), FLAME_PALETTE.length - 1);
    const halfW = Math.max(2, Math.round(p.sz * (1 - t * 0.35)));
    const blockH = Math.max(2, p.sz);
    ctx.globalAlpha = t < 0.15 ? 1 : (1 - t * 0.5);
    ctx.fillStyle = FLAME_PALETTE[ci];
    ctx.fillRect(Math.round(p.x) - halfW, Math.round(p.y), halfW * 2, blockH);
    p.age++; p.x += p.vx; p.y += p.vy;
  });
  ctx.globalAlpha = 1;
}

// ─────────────────────────────────────────────────────────────────────────────
//  COUNTDOWN UI
// ─────────────────────────────────────────────────────────────────────────────
function drawCountdown() {
  const launch = currentLaunch();
  if (!launch) return;
  const cd = computeCountdown(launch.t0);
  const vals = (cd && cd !== 'LAUNCHED') ? [cd.days, cd.hours, cd.minutes, cd.seconds] : [0,0,0,0];
  const LABELS = ['DAY','HOUR','MIN','SEC'];

  const BW = 80, BH = 80, GAP = 7;
  const TOTAL_W = 4*BW + 3*GAP;
  const BX = Math.round((W - TOTAL_W) / 2);
  const BY = 8;

  // Dark bar background
  ctx.fillStyle = 'rgba(20,20,28,0.88)';
  ctx.beginPath(); roundRectPath(BX-16, BY-6, TOTAL_W+32, BH+30, 5); ctx.fill();

  const _onHold = (launch.status || '').toLowerCase().includes('hold');

  if (_onHold && cd === 'LAUNCHED') {
    // Launch is on hold — slow breathing yellow ON HOLD banner
    const _holdBreath = 0.65 + 0.35 * Math.sin(Date.now() / 800);
    const _boxCX = BX - 16 + (TOTAL_W + 32) / 2;  // true center of box
    const _boxH  = BH + 30;

    ctx.shadowColor = `rgba(255,211,61,${_holdBreath * 0.6})`; ctx.shadowBlur = 10;
    ctx.strokeStyle = `rgba(255,211,61,${_holdBreath * 0.75})`; ctx.lineWidth = 2;
    ctx.beginPath(); roundRectPath(BX-16, BY-6, TOTAL_W+32, _boxH, 5); ctx.stroke();
    ctx.shadowBlur = 0;

    // Box center = BY-6 + (BH+30)/2 = BY+49. Lay out 3 lines centered on that.
    ctx.fillStyle = `rgba(255,211,61,${_holdBreath * 0.5})`;
    ctx.font = 'bold 6px "Press Start 2P"'; ctx.textAlign = 'center';
    ctx.fillText('— COUNTDOWN —', _boxCX, BY + 30);

    ctx.shadowColor = `rgba(255,180,0,${_holdBreath * 0.8})`; ctx.shadowBlur = 14;
    ctx.fillStyle = `rgba(255,211,61,${_holdBreath})`;
    ctx.font = '20px "Press Start 2P"'; ctx.textAlign = 'center';
    ctx.fillText('ON HOLD', _boxCX, BY + 54);
    ctx.shadowBlur = 0;

    // Elapsed time since original NET — "HELD AT T+MM:SS"
    const _holdElapsed = Math.floor((Date.now() - new Date(launch.t0).getTime()) / 1000);
    const _hm = Math.floor(_holdElapsed / 60), _hs = _holdElapsed % 60;
    const _holdStr = `HELD AT T+${String(_hm).padStart(2,'0')}:${String(_hs).padStart(2,'0')}`;
    ctx.fillStyle = `rgba(255,200,130,${_holdBreath * 0.75})`;
    ctx.font = '6px "Press Start 2P"'; ctx.textAlign = 'center';
    ctx.fillText(_holdStr, _boxCX, BY + 70);
    return;
  }

  if (cd === 'LAUNCHED' || state.postLaunchCooldown) {
    const _hasCooldown = !!state.postLaunchCooldown;
    const _boxH = _hasCooldown ? BH + 45 : BH + 30;
    const _cx   = BX - 16 + (TOTAL_W + 32) / 2;

    // Extend background for cooldown content
    if (_hasCooldown) {
      ctx.fillStyle = 'rgba(20,20,28,0.88)';
      ctx.beginPath(); roundRectPath(BX-16, BY-6, TOTAL_W+32, _boxH, 5); ctx.fill();
    }

    // Glowing red border
    ctx.shadowColor = '#ff3300'; ctx.shadowBlur = 12;
    ctx.strokeStyle = 'rgba(255,68,34,0.7)'; ctx.lineWidth = 2;
    ctx.beginPath(); roundRectPath(BX-16, BY-6, TOTAL_W+32, _boxH, 5); ctx.stroke();
    ctx.shadowBlur = 0;

    // "LIFTOFF" header label
    ctx.fillStyle = 'rgba(255,100,50,0.5)';
    ctx.font = 'bold 9px "Press Start 2P"'; ctx.textAlign = 'center';
    ctx.fillText('— LIFTOFF —', _cx, BY + 10);

    // Big IN FLIGHT text
    ctx.shadowColor = '#ff2200'; ctx.shadowBlur = 18;
    ctx.fillStyle = '#ff4422';
    ctx.font = '20px "Press Start 2P"'; ctx.textAlign = 'center';
    ctx.fillText('IN FLIGHT', _cx, BY + 38);
    ctx.shadowBlur = 0;

    // Mission name — clipped to one line below LAUNCHED
    const _lFull  = state.launchedMissionName || '';
    const _lPipe  = _lFull.indexOf(' | ');
    const _lShort = (_lPipe >= 0 ? _lFull.slice(_lPipe + 3) : _lFull).toUpperCase();
    if (_lShort) {
      ctx.fillStyle = 'rgba(255,200,150,0.85)';
      ctx.font = '9px "Press Start 2P"'; ctx.textAlign = 'center';
      ctx.save();
      ctx.beginPath(); ctx.rect(BX-16, BY+44, TOTAL_W+32, 16); ctx.clip();
      ctx.fillText(_lShort, _cx, BY + 57);
      ctx.restore();
    }

    if (_hasCooldown) {
      const remSec = Math.max(0, Math.floor((state.cooldownEndsAt - Date.now()) / 1000));
      const remM = Math.floor(remSec / 60), remS = remSec % 60;

      // Divider
      ctx.strokeStyle = 'rgba(255,68,34,0.3)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(BX, BY+68); ctx.lineTo(BX+TOTAL_W, BY+68); ctx.stroke();

      // Stand-up countdown
      ctx.shadowColor = '#ffd93d'; ctx.shadowBlur = 6;
      ctx.fillStyle = '#ffd93d';
      ctx.font = '10px "Press Start 2P"'; ctx.textAlign = 'center';
      ctx.fillText('PAD TURNAROUND IN  ' + remM + ':' + String(remS).padStart(2,'0'), _cx, BY + 82);
      ctx.shadowBlur = 0;
    }
    return;
  }

  // Pre-compute delay info so border + tab share the same values
  const _slipMs0 = (launch.original_t0 && launch.original_t0 !== launch.t0)
    ? Math.abs(new Date(launch.t0) - new Date(launch.original_t0)) : 0;
  const _isDelayed = _slipMs0 >= 5 * 60000;
  const _dlw = 4; // border lineWidth — shared by border + tab
  const _dbp = _isDelayed ? 0.75 + 0.25 * Math.sin(Date.now() / 1400) : 1; // shared pulse
  let _delayedStr = '';
  if (_isDelayed) {
    const _sd = Math.floor(_slipMs0 / 86400000);
    const _sh = Math.floor((_slipMs0 % 86400000) / 3600000);
    const _sm = Math.floor((_slipMs0 % 3600000) / 60000);
    _delayedStr = _sd > 0 ? `+${_sd} ${_sd===1?'DAY':'DAYS'}` : _sh > 0 ? `+${_sh} ${_sh===1?'HOUR':'HOURS'}` : `+${_sm} MIN`;
  }

  // Border — when delayed: 3-sided red outline (no bottom — tab provides it); otherwise subtle white
  if (_isDelayed) {
    const _bx = BX - 16, _by = BY - 6, _bw = TOTAL_W + 32, _bh = BH + 30, _r = 5;
    ctx.shadowColor = `rgba(200,30,0,${_dbp * 0.4})`; ctx.shadowBlur = 10;
    ctx.strokeStyle = `rgba(210,40,0,${_dbp})`; ctx.lineWidth = _dlw;
    ctx.beginPath();
    ctx.moveTo(_bx, _by + _bh);
    ctx.lineTo(_bx, _by + _r);
    ctx.arcTo(_bx, _by, _bx + _r, _by, _r);
    ctx.lineTo(_bx + _bw - _r, _by);
    ctx.arcTo(_bx + _bw, _by, _bx + _bw, _by + _r, _r);
    ctx.lineTo(_bx + _bw, _by + _bh);
    ctx.stroke();
    ctx.shadowBlur = 0;
  } else {
    ctx.strokeStyle = 'rgba(255,255,255,0.07)'; ctx.lineWidth = 1;
    ctx.beginPath(); roundRectPath(BX-16, BY-6, TOTAL_W+32, BH+30, 5); ctx.stroke();
  }
  ctx.fillStyle='rgba(255,255,255,0.25)';
  ctx.font='bold 7px Courier New'; ctx.textAlign='center';
  ctx.fillText('T  —  M I N U S', BX+TOTAL_W/2, BY+2);
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
    ctx.font='24px "Press Start 2P"';
    ctx.textAlign='center';
    ctx.textBaseline='middle';
    ctx.fillText(String(vals[i]).padStart(2,'0'), sx + sw/2, sy + sh/2);
    ctx.textBaseline='alphabetic';
    ctx.shadowBlur=0;

    // Label
    ctx.fillStyle='#1a2a3a'; ctx.font='bold 11px "Press Start 2P"'; ctx.textAlign='center';
    ctx.fillText(lbl, bx+BW/2, by+BH-3);
  });

  // DELAYED tab — flush with outer edge of border (offset by lineWidth/2)
  if (_isDelayed) {
    const _tabX = BX - 16 - _dlw / 2;
    const _tabW = TOTAL_W + 32 + _dlw;
    const _tabY = BY - 6 + BH + 30;
    const _tabH = 18;
    ctx.fillStyle = `rgba(180,28,0,${_dbp})`;
    ctx.beginPath();
    ctx.moveTo(_tabX, _tabY);
    ctx.lineTo(_tabX + _tabW, _tabY);
    ctx.lineTo(_tabX + _tabW, _tabY + _tabH - 4);
    ctx.arcTo(_tabX + _tabW, _tabY + _tabH, _tabX + _tabW - 4, _tabY + _tabH, 4);
    ctx.lineTo(_tabX + 4, _tabY + _tabH);
    ctx.arcTo(_tabX, _tabY + _tabH, _tabX, _tabY + _tabH - 4, 4);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = `rgba(255,255,255,${_dbp})`;
    ctx.font = '8px "Press Start 2P"';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`DELAYED  ${_delayedStr}`, _tabX + _tabW / 2, _tabY + _tabH / 2);
    ctx.textBaseline = 'alphabetic';
  }

  // Simultaneous launch banner — shown when the next launch has the same NET (within 5 min)
  if (state.launches.length > 1) {
    const primary = state.launches[state.currentIdx];
    const next    = state.launches.find((l, i) => i !== state.currentIdx && l.t0 && !state.buriedLaunchIds.includes(l.id));
    if (primary && next && primary.t0 && next.t0) {
      const diff = Math.abs(new Date(primary.t0) - new Date(next.t0)) / 60000;
      if (diff <= 5) {
        const _simY  = BY + BH + 26;
        const _simW  = TOTAL_W + 32;
        const _simCX = BX - 16 + _simW / 2;
        ctx.fillStyle = 'rgba(20,20,28,0.85)';
        ctx.beginPath(); roundRectPath(BX-16, _simY, _simW, 20, 3); ctx.fill();
        ctx.strokeStyle = 'rgba(74,158,222,0.4)'; ctx.lineWidth = 1;
        ctx.beginPath(); roundRectPath(BX-16, _simY, _simW, 20, 3); ctx.stroke();

        ctx.fillStyle = 'rgba(74,158,222,0.6)';
        ctx.font = 'bold 5px "Press Start 2P"'; ctx.textAlign = 'center';
        ctx.fillText('SIMULTANEOUS LAUNCH', _simCX, _simY + 7);

        const _sName = (next.name || '').split(' | ').pop().toUpperCase();
        const _sLoc  = (next.location || next.pad || '').toUpperCase().slice(0, 30);
        const _sTxt  = (_sName.length > 24 ? _sName.slice(0, 22) + '…' : _sName) + '  ·  ' + _sLoc;
        ctx.fillStyle = 'rgba(255,255,255,0.7)';
        ctx.font = '5px "Press Start 2P"'; ctx.textAlign = 'center';
        ctx.fillText(_sTxt, _simCX, _simY + 16);
      }
    }
  }
}


function updateInfoBar() {

  // If the HTML info-bar isn't present in this page (e.g. canvas-only embed),
  // bail out to avoid "Cannot set properties of null" errors.
  if (!document.getElementById('ib-name')) return;

  // Post-launch cooldown state
  if (state.postLaunchCooldown) {
    const _lnFull = state.launchedMissionName || '—';
    const _lnPipe = _lnFull.indexOf(' | ');
    document.getElementById('ib-name').textContent = _lnPipe >= 0 ? _lnFull.slice(_lnPipe + 3) : _lnFull;
    document.getElementById('ib-badge').textContent = '✓';
    document.getElementById('ib-badge').className = 'go';
    document.getElementById('ib-sub').textContent = 'IN FLIGHT';
    document.getElementById('ib-location').textContent = '';
    document.getElementById('ib-cd').textContent = '—';
    document.getElementById('ib-tap').onclick = null;
    return;
  }

  const launch = currentLaunch();
  if (!launch || typeof launch !== 'object') {
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
  // Truncate to fit: Press Start 2P at 10px ≈ 7px/char, name area ~280px wide ≈ 40 chars max
  const nameDisplay = missionName.length > 38 ? missionName.slice(0, 36) + '…' : missionName;
  nameEl.textContent = nameDisplay;
  nameEl.style.fontSize = nameDisplay.length > 24 ? '10px' : nameDisplay.length > 16 ? '12px' : '14px';

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
  const shorten = s => (s||'').replace(/\s*\(.*?\)/g,'').replace('Space Launch Complex','SLC').replace('Launch Complex','LC')
    .replace('Space Force Station','SFS').replace('Kennedy Space Center','KSC')
    .replace('Cape Canaveral','CC').replace('Vandenberg Space Force Base','VSFB')
    .replace(' Space Force Base','').trim();
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
  document.getElementById('ib-tap').onclick = () => { window.showPage ? window.showPage(_missionUrl) : (window.location = _missionUrl); };
  const ibLeft = document.getElementById('ib-left');
  if (ibLeft) ibLeft.onclick = () => { window.showPage ? window.showPage(_missionUrl) : (window.location = _missionUrl); };

  // Date + countdown (hidden elements kept for compat)
  const _fmt = state.settings?.time_format;
  const _siteTz = state.settings?.site === 'vandenberg' ? 'America/Los_Angeles' : 'America/New_York';
  const _localTz = state.settings?.timezone || 'America/New_York';
  const tz  = _fmt === 'utc' ? 'UTC' : _fmt === 'site' ? _siteTz : _localTz;
  const tzLabel = _fmt === 'utc' ? 'UTC' : _fmt === 'site' ? 'SITE' : 'LOCAL';
  const t0 = launch.t0 || launch.win_open;
  if (t0) {
    const d = new Date(t0);
    document.getElementById('ib-date').textContent =
      d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:tz}) + ' · ' +
      d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz,hour12:false}) +
      ' ' + tzLabel;
    // T-0 display in new detail row
    const t0Label = d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:tz,hour12:false})
      + ' · ' + d.toLocaleDateString('en-US',{day:'numeric',month:'short',timeZone:tz}).toUpperCase();
    document.getElementById('ib-t0').textContent = t0Label;
    const _winT0El = document.getElementById('ib-win-t0');
    if (_winT0El) _winT0El.textContent = t0Label;
    const cd = computeCountdown(t0);
    if (cd && cd !== 'LAUNCHED') {
      const {days,hours,minutes,seconds} = cd;
      const hh=String(hours).padStart(2,'0'), mm=String(minutes).padStart(2,'0'), ss=String(seconds).padStart(2,'0');
      document.getElementById('ib-cd').textContent = days>0 ? `T− ${days}d ${hh}:${mm}:${ss}` : `T− ${hh}:${mm}:${ss}`;
      // T-10 alert: flash info bar red when under 10 minutes
      // T-1hr alert: pulse info bar amber when under 1 hour
      const infoBar = document.getElementById('info-bar');
      if (infoBar) {
        if (cd.total_seconds <= 600 && cd.total_seconds > 0) {
          infoBar.classList.add('t10-alert');
          infoBar.classList.remove('t1hr-alert');
        } else if (cd.total_seconds <= 3600 && cd.total_seconds > 0) {
          infoBar.classList.add('t1hr-alert');
          infoBar.classList.remove('t10-alert');
        } else {
          infoBar.classList.remove('t10-alert');
          infoBar.classList.remove('t1hr-alert');
        }
      }
    } else if (cd === 'LAUNCHED') {
      const _ibLaunch = currentLaunch();
      const _ibHold = _ibLaunch && (_ibLaunch.status || '').toLowerCase().includes('hold');
      document.getElementById('ib-cd').textContent = _ibHold ? 'ON HOLD' : 'LAUNCHED';
      document.getElementById('ib-cd').style.color = '#ff4422';
      const infoBar = document.getElementById('info-bar');
      if (infoBar) { infoBar.classList.remove('t10-alert'); infoBar.classList.remove('t1hr-alert'); }
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
      const dotEl  = document.getElementById('ib-win-dot');
      const fillEl = document.getElementById('ib-win-fill');
      if (dotEl) {
        const openMs  = new Date(winOpen).getTime();
        const t0Ms    = new Date(t0).getTime();
        const closeMs = new Date(winClose).getTime();
        const _span = closeMs - openMs;
        const pct = _span > 0 ? Math.min(100, Math.max(0, (t0Ms - openMs) / _span * 100)) : 50;
        dotEl.style.left = pct + '%';
        if (fillEl) fillEl.style.width = pct + '%';
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
    // Version + data age — show LOS warning when stale >1h
  const serverStaleIB = state.dataAge > 3600;
  const clientStaleIB = Date.now() - state.lastFetchAt > 60 * 60 * 1000;
  const verEl = document.getElementById('ib-ver');
  if (serverStaleIB || clientStaleIB) {
    const staleMin = serverStaleIB
      ? Math.floor(state.dataAge / 60)
      : Math.floor((Date.now() - state.lastFetchAt) / 60000);
    const sh = Math.floor(staleMin / 60), sm = staleMin % 60;
    const staleStr = sh > 0 ? `${sh}h ${String(sm).padStart(2,'0')}m` : `${sm}m`;
    verEl.textContent = `⚠ NO SIGNAL · ${staleStr} ago`;
    verEl.style.color = '#ff4422';
  } else {
    const minAgo = Math.floor((Date.now() - state.lastFetchAt) / 60000);
    verEl.textContent = `${state.version || 'v2.0.0'} · data ${minAgo}m ago`;
    verEl.style.color = '';
  }
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
  const W_N = 160, H_N = 36;
  const nx = 800 - (W_N + 8) + (W_N + 8) * (n.offset / 200); // slides in from right
  const ny = 8;
  ctx.globalAlpha = Math.min(1, n.alpha);
  // Background
  ctx.fillStyle = 'rgba(8,12,22,0.96)';
  ctx.fillRect(Math.round(nx), ny, W_N, H_N);
  // Green left accent bar
  ctx.fillStyle = '#00e87a';
  ctx.fillRect(Math.round(nx), ny, 2, H_N);
  // Border
  ctx.strokeStyle = 'rgba(0,232,122,0.30)';
  ctx.lineWidth = 1;
  ctx.strokeRect(Math.round(nx) + 0.5, ny + 0.5, W_N - 1, H_N - 1);
  // Dot
  ctx.fillStyle = '#00e87a';
  ctx.fillRect(Math.round(nx) + 10, ny + 10, 4, 4);
  // Title
  ctx.fillStyle = '#00e87a';
  ctx.font = 'bold 9px Courier New';
  ctx.textAlign = 'left';
  ctx.fillText(n.text, Math.round(nx) + 22, ny + 15);
  // Timestamp
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.font = '8px Courier New';
  ctx.fillText(ts(), Math.round(nx) + 22, ny + 27);
  ctx.globalAlpha = 1;
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

  // If the launch is on hold, never trigger the LAUNCHED banner (skip in test mode)
  if (!state.testMode && (launch.status || '').toLowerCase().includes('hold')) return;

  const cd = computeCountdown(launch.t0);

  if (cd === 'LAUNCHED') {
    const launchTime = new Date(launch.t0).getTime();
    const minsAgo = (Date.now() - launchTime) / 60000;

    // Only act if we've had at least one successful data fetch and the page has been
    // open for >5s — prevents false triggers on stale cache at startup
    const pageAge = (Date.now() - state.lastFetchAt) / 1000;
    if (pageAge > 30 * 60) return; // data is too old to trust — wait for refresh

    if (minsAgo > 30) {
      // Old launch — just bury it silently, no cooldown banner
      console.log(`[${ts()}] Stale launch (${Math.floor(minsAgo)}m ago) — burying and skipping`);
      if (!state.buriedLaunchIds.includes(launch.id)) state.buriedLaunchIds.push(launch.id);
      // Advance to next without triggering postLaunchCooldown
      const nextIdx = state.launches.findIndex(l => !state.buriedLaunchIds.includes(l.id));
      state.currentIdx = nextIdx >= 0 ? nextIdx : 0;
      state.launchTriggered = false;
      return;
    }

    // Within 30 min of T-0 — genuinely just launched. But don't trigger missed-launch
    // if data is very fresh (< 10s old) — could be a fetch-race causing a false positive
    if (state.lastFetchAt && (Date.now() - state.lastFetchAt) < 10000) return;

    console.log(`[${ts()}] Missed launch detected (${Math.floor(minsAgo)}m ago) — starting cooldown`);
    state.launchTriggered     = true;
    state.launchComplete      = true;
    state.rocketOffscreen     = true;
    if (!state.buriedLaunchIds.includes(launch.id)) state.buriedLaunchIds.push(launch.id);
    state.launchedMissionName = launch.name || '';
    state._lastLaunchT0       = launch.t0 || null;
    state._lastLaunchVehicle  = launch.vehicle || '';
    state.postLaunchCooldown  = true;
    state.cooldownEndsAt      = Date.now() + 3 * 60 * 1000; // 3 min cooldown for missed launches (not 10)

    fetch('/api/launches').then(r => r.json()).then(data => {
      const all = data.launches || [];
      const next = all.find(l => l.id !== launch.id && l.t0 && new Date(l.t0) > new Date()) || null;
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
  state.flameParticles  = [];
  state.trenchParticles = [];
  state.ventParticles   = [];
  state.flameIntensity  = 0;
  state.rocketOffscreen = false;
}

function updateLaunch() {
  if (!state.isLaunching) return;

  state.launchFrame++;

  // Phase 1: ignition build-up (40 frames = 2s at 20fps)
  if (state.launchFrame < 40) {
    state.flameIntensity = state.launchFrame / 40;
  } else {
    // Phase 2: liftoff
    const vel = Math.min(0.08 * (state.launchFrame - 40) * 0.5, 4);
    state.rocketY -= vel;

    if (state.rocketY < -200) {
      state.isLaunching    = false;
      state.rocketOffscreen = true;
      state.launchComplete  = true;
      state.flameParticles  = [];
      const _launched           = currentLaunch();
      // Trigger RTLS booster return if landing type is RTLS
      if (_launched && (_launched.landing_type || '').toUpperCase() === 'RTLS') {
        state.rtlsActive   = true;
        state.rtlsFrame    = 0;
        state.rtlsBoosterY = -220;
      }
      if (_launched && !state.buriedLaunchIds.includes(_launched.id)) state.buriedLaunchIds.push(_launched.id);
      state.launchedMissionName = _launched ? (_launched.name || '') : '';
      state._lastLaunchT0       = _launched ? (_launched.t0 || null) : null;
      state._lastLaunchVehicle  = _launched ? (_launched.vehicle || '') : '';
      state.postLaunchCooldown  = true;
      if (state.testMode) {
        state.cooldownEndsAt = Date.now() + 10 * 1000; // 10s for test only
      } else {
        state.cooldownEndsAt = Date.now() + 10 * 60 * 1000;
        markStateDirty();
      }
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

  // Flame origin = centre-X of current rocket image, just below the nozzle
  const _fVehicle  = (currentLaunch() ? currentLaunch().vehicle : null) || '';
  const _fKey      = getRocketAssetKey(_fVehicle);
  const _fCfg      = (ROCKET_CONFIG[_fKey] || ROCKET_CONFIG.rocket_generic).pad;
  const _fImg      = IMG[_fKey];
  const _fRw       = _fImg ? Math.round(_fImg.width * (_fCfg.h / _fImg.height)) : 50;
  const flameX     = _fCfg.x + _fRw / 2 + (_fCfg.fx || 0);
  // Flame Y = bottom of rocket image + liftoff offset + fy (matches positioner exactly)
  const flameY     = _fCfg.y + _fCfg.h + (state.rocketY - PAD_Y_BASE) + (_fCfg.fy || 0);
  if (state.flameIntensity > 0) {
    spawnFlameParticles(flameX, flameY, state.flameIntensity);
  }
}

function drawNoSignal() {
  // Trigger when server hasn't reached LL2 in 1h OR client hasn't heard from server in 1h
  const serverStale = state.dataAge > 3600;
  const clientStale = Date.now() - state.lastFetchAt > 60 * 60 * 1000;
  if (!serverStale && !clientStale) return;

  // Compute total stale duration in minutes for display
  const staleMs  = clientStale
    ? Date.now() - state.lastFetchAt
    : state.dataAge * 1000;
  const totalMin = Math.floor(staleMs / 60000);
  const hh = Math.floor(totalMin / 60);
  const mm = totalMin % 60;
  const ageStr = hh > 0 ? `${hh}H ${String(mm).padStart(2,'0')}M` : `${mm}M`;

  // Blink at ~1Hz
  const blink = Math.floor(Date.now() / 600) % 2 === 0;

  // Panel — right side below gear icon
  const PW = 120, PH = 38;
  const PX = W - PW - 6, PY = 32;

  // Dark background
  ctx.fillStyle = 'rgba(8,10,16,0.93)';
  ctx.fillRect(PX, PY, PW, PH);

  // Red border (blinks between solid and dim)
  ctx.strokeStyle = blink ? '#ff2200' : 'rgba(255,34,0,0.35)';
  ctx.lineWidth = 2;
  ctx.strokeRect(PX + 1, PY + 1, PW - 2, PH - 2);

  // "NO SIGNAL" title
  ctx.fillStyle = blink ? '#ff4422' : 'rgba(255,68,34,0.5)';
  ctx.font = '7px "Press Start 2P"';
  ctx.textAlign = 'center';
  ctx.fillText('NO SIGNAL', PX + PW / 2, PY + 14);

  // Stale age
  ctx.fillStyle = 'rgba(255,200,180,0.55)';
  ctx.font = '6px "Press Start 2P"';
  ctx.fillText('DATA: ' + ageStr + ' AGO', PX + PW / 2, PY + 28);

  ctx.textAlign = 'left';
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

    const hadData = state.launches.length > 0;
    state.launches    = newLaunches;
    state.weather     = data.weather  || state.weather;
    state.settings    = data.settings || state.settings;
    state.version     = data.version  || state.version || '';
    state.dataAge     = data.age_seconds || 0;
    state.lastFetchAt = Date.now();
    if (hadData) showNotification('DATA UPDATED');

    // Prune buriedLaunchIds: remove any ID that no longer appears in the
    // fresh launch list (it already launched or was removed by the API).
    // This prevents stale test-launch IDs from permanently skipping real missions.
    const freshIds = new Set(newLaunches.map(l => l.id));
    state.buriedLaunchIds = state.buriedLaunchIds.filter(id => freshIds.has(id));

    // Auto-bury any launch whose T-0 is more than 5 min in the past.
    // Prevents LL2 data inconsistency (past launches reappearing in the feed)
    // from re-triggering the IN FLIGHT banner after a launch was already handled.
    newLaunches.forEach(l => {
      if (l.t0 && !state.buriedLaunchIds.includes(l.id)) {
        if ((Date.now() - new Date(l.t0).getTime()) / 60000 > 5) {
          state.buriedLaunchIds.push(l.id);
        }
      }
    });

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
      if (firstValid < 0) state.buriedLaunchIds = []; // all buried — reset so we don't show nothing
      state.currentIdx = firstValid >= 0 ? firstValid : 0;
      // If the current launch has a future T-0, reset trigger so countdown runs normally.
      // This prevents a stale launchTriggered=true from blocking the next mission's animation.
      const cur = state.launches[state.currentIdx];
      if (cur && cur.t0 && new Date(cur.t0) > new Date() && !state.isLaunching && !state.postLaunchCooldown) {
        state.launchTriggered = false;
      }
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
    if (c.x > 900) {
      c.x = -120;
      c.y = 30 + Math.random() * 100;  // 30–130, stays above tower top (~160)
    }
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

// Fog puff — single cached offscreen, scrolled across screen
let _fogPuff = null;
function getFogPuff() {
  if (_fogPuff) return _fogPuff;
  _fogPuff = makeOffscreen(400, 160);
  const g = _fogPuff.getContext('2d');
  const grad = g.createRadialGradient(200, 80, 0, 200, 80, 200);
  grad.addColorStop(0, 'rgba(200,210,220,0.18)');
  grad.addColorStop(1, 'rgba(200,210,220,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 400, 160);
  return _fogPuff;
}

function drawFog() {
  fogOffset = (fogOffset + 0.3) % W;
  const puff = getFogPuff();
  for (let i = 0; i < 3; i++) {
    const x = ((fogOffset + i * 280) % (W + 200)) - 300;
    ctx.drawImage(puff, x, 260);
  }
}

function getMilestones(vehicle) {
  const v = (vehicle||'').toLowerCase();
  if (v.includes('falcon')) return [{label:'PROP LOAD',t:-2280},{label:'ENGINE CHILL',t:-420},{label:'STRONGBACK',t:-270},{label:'STARTUP',t:-60},{label:'IGNITION',t:-3},{label:'LIFTOFF',t:0},{label:'MAX-Q',t:72},{label:'MECO',t:145},{label:'STAGE SEP',t:149},{label:'FAIRING SEP',t:178},{label:'ENTRY BURN',t:361},{label:'LANDING',t:500},{label:'SECO-1',t:532},{label:'DEPLOY',t:3691}];
  if (v.includes('electron')) return [{label:'TERMINAL COUNT',t:-3600},{label:'LOX FLIGHT LVL',t:-2700},{label:'RANGE VERIFY',t:-2100},{label:'FLIGHT SW',t:-1800},{label:'WX CHECK',t:-1200},{label:'GO POLL',t:-720},{label:'CD RESUMES',t:-600},{label:'PRESS ARMED',t:-300},{label:'AUTO SEQ',t:-120},{label:'TANK PRESS',t:-18},{label:'IGNITION',t:-2},{label:'LIFTOFF',t:0},{label:'PITCH PROG',t:15},{label:'TRANSONIC',t:55},{label:'SUPERSONIC',t:60},{label:'MAX-Q',t:72},{label:'MECO',t:149},{label:'STAGE SEP',t:153},{label:'2ND IGNITION',t:156},{label:'FAIRING SEP',t:188},{label:'BATT SWAP',t:410},{label:'SECO',t:565},{label:'KICK STAGE SEP',t:570},{label:'KICK BURN',t:1800},{label:'CURIE CUTOFF',t:2010},{label:'DEPLOY',t:2040}];
  if (v.includes('starship')) return [{label:'PROP LOAD',t:-3600},{label:'IGNITION',t:-3},{label:'LIFTOFF',t:0},{label:'MAX-Q',t:58},{label:'MECO',t:169},{label:'STAGE SEP',t:175},{label:'BOOSTER CATCH',t:420},{label:'SECO',t:540},{label:'DEPLOY',t:3600}];
  if (v.includes('new glenn') || v.includes(' ng')) return [{label:'TERMINAL COUNT',t:-240},{label:'IGNITION',t:-6},{label:'LIFTOFF',t:0},{label:'MAX-Q',t:96},{label:'MECO',t:185},{label:'STAGE SEP',t:189},{label:'FAIRING SEP',t:222},{label:'REENTRY BURN',t:426},{label:'BOOSTER LANDING',t:563},{label:'SECO-1',t:781},{label:'SECO-2',t:4249},{label:'DEPLOY',t:4544}];
  return [{label:'IGNITION',t:-3},{label:'LIFTOFF',t:0},{label:'MAX-Q',t:75},{label:'MECO',t:160},{label:'STAGE SEP',t:163},{label:'FAIRING SEP',t:200},{label:'SECO',t:520},{label:'DEPLOY',t:3600}];
}

let _tlSmooth = 0;

function drawMilestoneTimeline() {
  const launch = currentLaunch() || (state.postLaunchCooldown ? { t0: state._lastLaunchT0, vehicle: state._lastLaunchVehicle } : null);
  if (!launch || !launch.t0) return;
  const cd = computeCountdown(launch.t0);
  const isHold = (launch.status || '').toLowerCase().includes('hold');
  const elapsed = (Date.now() - new Date(launch.t0).getTime()) / 1000;
  // Show timeline from T-30min until end of milestones sequence (~75 min post launch)
  if (!isHold && cd && cd !== 'LAUNCHED' && cd.total_seconds > 1800) return;
  if (elapsed > 4500) return;
  const milestones = getMilestones(launch.vehicle || '');
  // On hold: lock display to the LIFTOFF milestone (t=0)
  let currentIdx = isHold
    ? milestones.findIndex(m => m.t === 0) ?? 0
    : milestones.findIndex(m => elapsed < m.t);
  if (currentIdx === -1) currentIdx = milestones.length - 1; // all done

  _tlSmooth += (currentIdx * 48 - _tlSmooth) * 0.08;

  const dotX = W - 38;
  const centerY = 210;
  const spacing = 48;
  const opacities = {'-2':0.5,'-1':0.8,'0':1.0,'1':0.8,'2':0.5};
  const scales    = {'-2':0.6, '-1':0.75,'0':1.0,'1':0.75,'2':0.6};
  const visible   = [currentIdx-2, currentIdx-1, currentIdx, currentIdx+1, currentIdx+2];

  function tStr(t){const a=Math.abs(t),m=Math.floor(a/60),s=a%60;return(t<0?'T-':'T+')+m+':'+String(s).padStart(2,'0');}

  visible.forEach(i => {
    if (i < 0 || i >= milestones.length) return;
    const m   = milestones[i];
    const y   = centerY + (i * spacing) - _tlSmooth;
    if (y < 15 || y > 365) return;

    const isDone    = !isHold && elapsed >= m.t;
    const isCurrent = i === currentIdx;
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
        if (!isHold && isDone) {
          // Fill based on progress toward next milestone
          const nextM = milestones[ni];
          const progress = Math.min(1, Math.max(0, (elapsed - m.t) / (nextM.t - m.t)));
          const fillY = lineTop + lineLen * progress;
          // Black outline behind green line
          ctx.strokeStyle = `rgba(0,0,0,0.7)`;
          ctx.lineWidth = 4;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, fillY); ctx.stroke();
          // Green filled portion
          ctx.strokeStyle = `rgba(0,232,122,${Math.min(1, opacity*1.3)})`;
          ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, fillY); ctx.stroke();
          // Gray remaining portion
          if (fillY < lineBot) {
            ctx.strokeStyle = `rgba(0,0,0,0.5)`;
            ctx.lineWidth = 3;
            ctx.beginPath(); ctx.moveTo(dotX, fillY); ctx.lineTo(dotX, lineBot); ctx.stroke();
            ctx.strokeStyle = `rgba(255,255,255,${opacity*0.5})`;
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(dotX, fillY); ctx.lineTo(dotX, lineBot); ctx.stroke();
          }
        } else {
          ctx.strokeStyle = `rgba(0,0,0,0.5)`;
          ctx.lineWidth = 3;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, lineBot); ctx.stroke();
          ctx.strokeStyle = `rgba(255,255,255,${opacity*0.5})`;
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(dotX, lineTop); ctx.lineTo(dotX, lineBot); ctx.stroke();
        }
      }
    }

    // Dot — black halo behind for contrast
    const r = Math.max(3, Math.round(6*scale));
    ctx.fillStyle = 'rgba(0,0,0,0.75)';
    ctx.beginPath(); ctx.arc(dotX, y, r+2, 0, Math.PI*2); ctx.fill();
    if (isHold) {
      // Hold state: current (LIFTOFF) pulses amber, rest are dim amber
      if (isCurrent) {
        const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 800);
        ctx.fillStyle = `rgba(255,211,61,${0.12 * pulse})`;
        ctx.beginPath(); ctx.arc(dotX, y, r+5, 0, Math.PI*2); ctx.fill();
        ctx.fillStyle = `rgba(255,211,61,${0.7 + 0.3 * pulse})`;
        ctx.beginPath(); ctx.arc(dotX, y, r, 0, Math.PI*2); ctx.fill();
      } else {
        ctx.strokeStyle = `rgba(255,211,61,${opacity * 0.5})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(dotX, y, r, 0, Math.PI*2); ctx.stroke();
      }
    } else if (isDone) {
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

    // Labels — dark pill background for contrast, bigger font for current
    const ls = isCurrent ? 11 : Math.max(9, Math.round(10*scale));
    const ts = isCurrent ? 7  : Math.max(7, Math.round(8*scale));
    const labelColor = isHold ? `rgba(255,211,61,${opacity * (isCurrent ? 1.0 : 0.5)})` : isCurrent ? `rgba(255,211,61,1.0)` : isDone ? `rgba(0,232,122,${opacity})` : `rgba(255,255,255,${opacity})`;
    const timeColor  = isHold ? `rgba(255,211,61,${opacity * 0.4})` : isCurrent ? `rgba(255,211,61,0.9)` : `rgba(0,232,122,${Math.min(1,opacity*1.1)})`;
    ctx.textAlign = 'right';

    // Dark pill behind label for readability
    if (isCurrent) {
      ctx.font = `bold ${ls}px "Press Start 2P"`;
      const lw = ctx.measureText(m.label).width;
      ctx.fillStyle = 'rgba(0,0,0,0.75)';
      roundRectPath(dotX - 14 - lw - 4, y - ls, lw + 8, ls + 4, 2);
      ctx.fill();
    }

    ctx.shadowColor = 'rgba(0,0,0,0.95)';
    ctx.shadowBlur = isCurrent ? 8 : 4;
    ctx.font = isCurrent ? `bold ${ls}px "Press Start 2P"` : `bold ${ls}px Courier New`;
    ctx.fillStyle = labelColor;
    ctx.fillText(m.label, dotX-12, y+3);
    ctx.font = isCurrent ? `${ts}px "Press Start 2P"` : `${ts}px Courier New`;
    ctx.fillStyle = timeColor;
    ctx.fillText(tStr(m.t), dotX-12, y+ls+5);
    ctx.shadowBlur = 0;
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  MAIN RENDER LOOP
// ─────────────────────────────────────────────────────────────────────────────
let lastFrame = 0;
const TARGET_FPS = 20;
const FRAME_MS   = 1000 / TARGET_FPS;

function render(now) {
  requestAnimationFrame(render);
  if (now - lastFrame < FRAME_MS) return;
  lastFrame = now;
  try {

  // ── Updates ──
  updateClouds();
  updateBirds();
  updateRTLS();
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
  drawMoon();
  drawClouds();

  // Weather effects — only draw rain streaks if measurable precip detected
  const cond = state.weather.condition;
  const hasRain = (state.weather.precip || 0) > 0;
  if (cond === 'rain' || cond === 'light_rain') { if (hasRain) drawRain(false); }
  if (cond === 'thunderstorm') { const clouds = state.weather.cloud_cover || 0; if (hasRain) drawRain(true); if (clouds > 20) drawLightning(); }
  if (cond === 'fog') drawFog();
  drawVAB();
  // drawFences();
  drawTrenchParticles(); // ← Trench smoke/fire (behind grass, road, pad)
  drawFlameParticles();  // ← Rocket jet (behind grass, road, pad)
  ctx.drawImage(getGrassCache(), 0, 0);  // grass/road covers base of exhaust
  drawBackgroundPad();  // ← Next rocket on distant pad
  drawUmbilicals();     // ← Umbilical arms (behind rocket)
  drawRocket();         // ← Active pad rocket (in front of umbilicals)
  drawRTLS();           // ← RTLS booster return (after grass, sits on ground)
  drawLaunchTower();    // ← Draw tower AFTER (in front)
  drawLaunchPad();

  //drawPond();
  drawBirds();
  drawCars();
  drawSpotlights();
  drawSmoke();
  updateInfoBar();
  drawCountdown();
  drawMilestoneTimeline();
  drawGearIcon();
  drawNoSignal();
  if (state.notification) drawNotification();
  } catch(e) {
    console.error('[render]', e);
    // Show error on screen so Pi kiosk user knows something is wrong
    ctx.fillStyle = 'rgba(0,0,0,0.7)';
    ctx.fillRect(0, H - 30, W, 30);
    ctx.fillStyle = '#ff4422';
    ctx.font = '7px "Press Start 2P"';
    ctx.textAlign = 'left';
    ctx.fillText('RENDER ERR: ' + String(e.message || e).slice(0, 80), 8, H - 10);
  }
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

  // Poll server for push notifications (update complete, reboots, etc.)
  let _lastNotifyMsg = null;
  setInterval(async () => {
    try {
      const r = await fetch('/api/notify', { cache: 'no-store' });
      if (!r.ok) return;
      const msgs = await r.json();
      if (!msgs.length) return;
      const m = msgs[0];
      const key = m.title + '|' + m.msg;
      if (key === _lastNotifyMsg) return; // don't re-show same message
      _lastNotifyMsg = key;
      const text = m.msg ? `${m.title}: ${m.msg}` : m.title;
      showNotification(text);
    } catch(e) {}
  }, 5000);

  // Update HTML info bar every second
  setInterval(updateInfoBar, 1000);
}

// ─────────────────────────────────────────────────────────────────────────────
//  TEST LAUNCH  (click rocket on pad to trigger)
// ─────────────────────────────────────────────────────────────────────────────
function triggerTestLaunch(rtls = false) {
  if (state.isLaunching || state.testMode) return;
  const launch = currentLaunch();
  if (!launch) return;
  console.log(`[${ts()}] TEST MODE — overriding t0 to T-3s${rtls ? ' (RTLS)' : ''}`);
  const originalT0          = launch.t0;
  const originalTriggered   = state.launchTriggered;
  const originalLandingType = launch.landing_type;
  state.testMode            = true;
  launch.t0                 = new Date(Date.now() + 3000).toISOString();
  state.launchTriggered     = false;
  if (rtls) launch.landing_type = 'RTLS';

  const checkReset = setInterval(() => {
    if (!state.rocketOffscreen) return;
    clearInterval(checkReset);

    const launchedName = launch.name || '';
    state.launchedMissionName = launchedName;
    state.nextMissionName     = launchedName;
    state.nextMissionT0       = originalT0;
    state.postLaunchCooldown  = true;
    state.cooldownEndsAt      = Date.now() + 10 * 1000;

    const originalIdx = state.launches.indexOf(launch);
    const cooldownEnd = setInterval(() => {
      if (Date.now() < state.cooldownEndsAt) return;
      clearInterval(cooldownEnd);
      launch.t0                 = originalT0;
      launch.landing_type       = originalLandingType;
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
      // Unbury so the queue doesn't advance permanently
      if (launch.id) state.buriedLaunchIds = state.buriedLaunchIds.filter(id => id !== launch.id);
      state.currentIdx = originalIdx >= 0 ? originalIdx : 0;
      console.log(`[${ts()}] TEST MODE complete — restored`);
    }, 500);

    console.log(`[${ts()}] TEST MODE rocket offscreen — cooldown demo started`);
  }, 200);
}

document.getElementById('btn-test').addEventListener('click', triggerTestLaunch);
window.triggerTestRTLS = () => triggerTestLaunch(true);

// Direct RTLS-only test — skips full launch sequence, just plays the booster return
window.testRTLS = () => {
  console.log(`[${ts()}] RTLS direct test`);
  state.rtlsActive    = true;
  state.rtlsFrame     = 80;   // skip 60-frame pre-delay so booster + banner appear immediately
  state.rtlsBoosterY  = -220;
  state._lastLaunchVehicle = (currentLaunch() || {}).vehicle || 'Falcon 9';
};

// Force reset stuck post-launch state
window.ltReset = () => {
  state.postLaunchCooldown = false;
  state.launchComplete     = false;
  state.rocketOffscreen    = false;
  state.launchTriggered    = false;
  state.isLaunching        = false;
  state.testMode           = false;
  state.rocketY            = PAD_Y_BASE;
  state.flameParticles     = [];
  state.flameIntensity     = 0;
  state.buriedLaunchIds    = [];
  state.launchedMissionName = '';
  state.rtlsActive         = false;
  fetchData().then(() => console.log('[ltReset] done'));
};

// Debug helper — print key state
window.ltState = () => console.log(JSON.stringify({
  testMode: state.testMode, isLaunching: state.isLaunching,
  launchTriggered: state.launchTriggered, rocketOffscreen: state.rocketOffscreen,
  rtlsActive: state.rtlsActive, rtlsFrame: state.rtlsFrame,
  currentLaunch: currentLaunch() ? { id: currentLaunch().id, status: currentLaunch().status, landing_type: currentLaunch().landing_type, t0: currentLaunch().t0 } : null
}, null, 2));

canvas.addEventListener('click', function(e) {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;

  // Settings button tap zone — expanded hit area around gear icon (visual: W-94 to W-6, y 5-27)
  if (x > W - 116 && x < W && y > 0 && y < 40) {
    window.location = '/settings';
  }

  // Mission name tap zone (bottom info bar)
  if (x > 0 && x < 400 && y > BAR_Y && y < BAR_Y + 35) {
    const launch = currentLaunch();
    if (launch) {
      window.location = `/mission?id=${launch.id}&name=${encodeURIComponent(launch.name)}`;
    }
  }

  // Rocket click → test launch
  if (!state.isLaunching && !state.testMode && !state.postLaunchCooldown && !state.rocketOffscreen) {
    const vehicle  = (currentLaunch() ? currentLaunch().vehicle : null) || '';
    const assetKey = getRocketAssetKey(vehicle);
    const cfg      = (ROCKET_CONFIG[assetKey] || ROCKET_CONFIG.rocket_generic).pad;
    const img      = IMG[assetKey];
    const rw       = img ? Math.round(img.width * (cfg.h / img.height)) : 50;
    if (x >= cfg.x - 4 && x <= cfg.x + rw + 4 && y >= cfg.y && y <= cfg.y + cfg.h) {
      triggerTestLaunch();
    }
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  STATE PERSISTENCE — survive page navigation
// ─────────────────────────────────────────────────────────────────────────────
let _stateDirty = false;
function markStateDirty() { _stateDirty = true; }

function saveState() {
  if (!_stateDirty) return;
  _stateDirty = false;
  try {
    localStorage.setItem('lt_state', JSON.stringify({
      currentIdx:          state.currentIdx,
      postLaunchCooldown:  state.postLaunchCooldown,
      cooldownEndsAt:      state.cooldownEndsAt,
      buriedLaunchIds:     state.buriedLaunchIds,
      launchedMissionName: state.launchedMissionName,
      nextMissionName:     state.nextMissionName,
      nextMissionT0:       state.nextMissionT0,
      _lastLaunchT0:       state._lastLaunchT0,
      _lastLaunchVehicle:  state._lastLaunchVehicle,
      isLaunching:         state.isLaunching,
      launchFrame:         state.launchFrame,
      rocketY:             state.rocketY,
      flameIntensity:      state.flameIntensity,
      launchTriggered:     state.launchTriggered,
      _savedAt:            Date.now(),
    }));
  } catch(e) {}
}

function restoreState() {
  try {
    const raw = localStorage.getItem('lt_state');
    if (!raw) return;
    const saved = JSON.parse(raw);
    // Discard if not a valid object or older than 24 hours
    if (!saved || typeof saved !== 'object') { localStorage.removeItem('lt_state'); return; }
    if (Date.now() - (saved._savedAt || 0) > 86400000) { localStorage.removeItem('lt_state'); return; }
    // Only restore cooldown if it hasn't expired
    // Restore current launch index
    if (saved.currentIdx != null) state.currentIdx = saved.currentIdx;
    // Restore mid-flight state
    if (saved.isLaunching) {
      state.isLaunching    = true;
      state.launchFrame    = saved.launchFrame || 0;
      state.rocketY        = saved.rocketY || PAD_Y_BASE;
      state.flameIntensity = saved.flameIntensity || 0;
      state.launchTriggered = true;
    }
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
    // Do NOT restore buriedLaunchIds — they are pruned against fresh API data
    // on the first fetchData() call, so stale test-launch IDs can't persist across reboots.
  } catch(e) {}
}

//  BOOT
// ─────────────────────────────────────────────────────────────────────────────
(async function boot() {
  // Wait for Press Start 2P to load before first render so canvas text isn't wrong font
  try { await document.fonts.load('10px "Press Start 2P"'); } catch(e) {}
  await loadAssets();
  spawnBirds();
  spawnCars();
  restoreState();
  await fetchData();
  initWeatherParticles();
  startPolling();
  // Persist state every 5 seconds
  setInterval(saveState, 5000);
  // Auto-dim handled globally by notify.js (applies to document.body on all pages)
  // Server watchdog — redirect to boot page if server goes down
  let _wdFails = 0;
  setInterval(async () => {
    try {
      const r = await fetch('/api/data?_wd=1', { cache: 'no-store' });
      if (r.ok) { _wdFails = 0; return; }
    } catch(e) {}
    _wdFails++;
    if (_wdFails >= 3) {
      window.location = 'file:///home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/static/boot.html';
    }
  }, 10000);
  // Version watchdog — reload page when server updates (new git commit)
  let _appVersion = null;
  setInterval(async () => {
    try {
      const r = await fetch('/api/version', { cache: 'no-store' });
      if (!r.ok) return;
      const { version } = await r.json();
      if (_appVersion === null) { _appVersion = version; return; }
      if (version !== _appVersion) window.location.reload(true);
    } catch(e) {}
  }, 30000);
  requestAnimationFrame(render);
  console.log(`[${ts()}] Launch Countdown Phase 2 ready`);
})();