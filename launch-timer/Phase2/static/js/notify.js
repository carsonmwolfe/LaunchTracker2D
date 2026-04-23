(function () {
  // Inject overlay styles once
  const style = document.createElement('style');
  style.textContent = `
    #pi-notify-overlay {
      display: none;
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(0,0,0,0.72);
      align-items: center; justify-content: center;
    }
    #pi-notify-overlay.show { display: flex; }
    #pi-notify-box {
      background: #0a0f1a;
      border: 2px solid #00e87a;
      padding: 40px 56px;
      text-align: center;
      font-family: 'Courier New', monospace;
      box-shadow: 0 0 60px rgba(0,232,122,0.25);
      animation: pi-notify-in 0.25s ease;
    }
    @keyframes pi-notify-in {
      from { transform: scale(0.88); opacity: 0; }
      to   { transform: scale(1);    opacity: 1; }
    }
    #pi-notify-icon { font-size: 48px; margin-bottom: 16px; }
    #pi-notify-title {
      font-size: 22px; font-weight: bold; letter-spacing: 3px;
      color: #00e87a; margin-bottom: 12px;
    }
    #pi-notify-msg {
      font-size: 13px; color: rgba(255,255,255,0.6);
      letter-spacing: 1px;
    }
    #pi-notify-bar {
      margin-top: 28px; height: 3px; background: rgba(0,232,122,0.15);
      overflow: hidden;
    }
    #pi-notify-bar-inner {
      height: 100%; background: #00e87a;
      animation: pi-notify-drain 15s linear forwards;
    }
    @keyframes pi-notify-drain {
      from { width: 100%; }
      to   { width: 0%; }
    }
  `;
  document.head.appendChild(style);

  const overlay = document.createElement('div');
  overlay.id = 'pi-notify-overlay';
  overlay.innerHTML = `
    <div id="pi-notify-box">
      <div id="pi-notify-icon">✓</div>
      <div id="pi-notify-title"></div>
      <div id="pi-notify-msg"></div>
      <div id="pi-notify-bar"><div id="pi-notify-bar-inner"></div></div>
    </div>
  `;
  document.body.appendChild(overlay);

  let hideTimer = null;

  // Dedup key stored in sessionStorage so it survives page reloads during updates
  function _getShownKey() { try { return sessionStorage.getItem('pi-notify-key'); } catch(e) { return null; } }
  function _setShownKey(k) { try { sessionStorage.setItem('pi-notify-key', k); } catch(e) {} }
  function _clearShownKey(k) { try { if (sessionStorage.getItem('pi-notify-key') === k) sessionStorage.removeItem('pi-notify-key'); } catch(e) {} }

  function showNotify(title, msg, icon) {
    document.getElementById('pi-notify-icon').textContent = icon || '✓';
    document.getElementById('pi-notify-title').textContent = title;
    document.getElementById('pi-notify-msg').textContent = msg;
    // Reset bar animation
    const bar = document.getElementById('pi-notify-bar-inner');
    bar.style.animation = 'none';
    bar.offsetHeight; // reflow
    bar.style.animation = '';
    overlay.classList.add('show');
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(() => overlay.classList.remove('show'), 15000);
  }

  async function pollNotify() {
    try {
      const r = await fetch('/api/notify');
      const msgs = await r.json();
      if (msgs && msgs.length > 0) {
        const n = msgs[0];
        const key = n.title + '|' + n.msg;
        if (key !== _getShownKey()) {
          _setShownKey(key);
          // Clear after 30s so a genuinely new identical notification can show
          setTimeout(() => _clearShownKey(key), 30000);
          const icon = n.title.includes('REBOOT') ? '↻' : '↑';
          showNotify(n.title, n.msg, icon);
        }
      }
    } catch (e) {}
    setTimeout(pollNotify, 1000);
  }

  pollNotify();

  // ── Auto-dim ─────────────────────────────────────────────────────────────────
  // Applies to every page. Reads auto_dim setting from /api/settings every 5 min.
  let _autoDimEnabled = true;
  async function _loadDimSetting() {
    try {
      const r = await fetch('/api/settings');
      const s = await r.json();
      _autoDimEnabled = s.auto_dim !== false;
    } catch(e) {}
  }
  function _applyDim() {
    const h = new Date().getHours();
    const dimOn = _autoDimEnabled && (h >= 22 || h < 6);
    document.body.style.filter = dimOn ? 'brightness(0.45)' : '';
  }
  _loadDimSetting().then(_applyDim);
  setInterval(() => { _loadDimSetting().then(_applyDim); }, 5 * 60 * 1000);
  setInterval(_applyDim, 60000);
  // expose so app.js can trigger re-apply after settings save
  window._applyAutoDim = _applyDim;
  window._setAutoDim = (v) => { _autoDimEnabled = v; _applyDim(); };

  // ── Inactivity redirect ───────────────────────────────────────────────────────
  // After 1 hour of no interaction on any non-home page, return to main screen.
  if (window.location.pathname !== '/') {
    const INACTIVITY_MS = 60 * 60 * 1000; // 1 hour
    let _inactivityTimer = setTimeout(() => { window.location = '/'; }, INACTIVITY_MS);
    function _resetInactivity() {
      clearTimeout(_inactivityTimer);
      _inactivityTimer = setTimeout(() => { window.location = '/'; }, INACTIVITY_MS);
    }
    ['mousemove','mousedown','keydown','touchstart','scroll'].forEach(ev =>
      document.addEventListener(ev, _resetInactivity, { passive: true })
    );
  }
})();
