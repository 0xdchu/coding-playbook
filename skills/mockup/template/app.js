/* Router, theme, device and the demo state machine. */
(function () {
  const KEY = 'mockup.seed.v1';
  const SEED = window.SEED;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const clone = (o) => JSON.parse(JSON.stringify(o));

  let state = load();
  let current = 'gallery';

  function load() {
    const base = clone(SEED);
    try { const raw = localStorage.getItem(KEY); return raw ? Object.assign(base, JSON.parse(raw)) : base; }
    catch { return base; }
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch {} }

  const view = $('#view');
  const back = $('#back');
  const title = $('#title');
  const themeBtn = $('#theme');
  const themeIc = $('#theme-ic use');
  const themeLabel = $('#theme-label');
  const device = $('#device');

  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    themeIc.setAttribute('href', state.theme === 'light' ? '#i-moon' : '#i-sun');
    themeLabel.textContent = state.theme === 'light' ? 'Dark' : 'Light';
    $$('[data-theme-set]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.themeSet === state.theme)));
  }
  function applyDevice() {
    $$('[data-device]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.device === state.device)));
  }
  function route() {
    const raw = location.hash.replace(/^#\/?/, '');
    const name = raw || 'gallery';
    render(name !== 'gallery' && window.Mockups.screens(state).some(s => s.id === name) ? name : 'gallery');
  }
  function render(name) {
    current = name;
    const isGallery = name === 'gallery';
    view.className = isGallery ? '' : (state.device === 'mobile' ? 'device-mobile' : '');
    view.innerHTML = window.Mockups.render(name, state);
    back.hidden = isGallery;
    title.hidden = isGallery;
    const meta = window.Mockups.screens(state).find(s => s.id === name);
    title.textContent = meta ? meta.title : '';
    document.title = meta ? `${meta.title} · ${state.product}` : `${state.product} mockups`;
    applyDevice();
    applyTheme();
    if (!isGallery) window.scrollTo({ top: 0 });
  }
  function toast(msg) {
    const el = document.createElement('div');
    el.className = 'toast';
    el.innerHTML = `<svg class="ic"><use href="#i-check"/></svg><span>${msg}</span>`;
    $('#toasts').appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }
  function busy(el, on, text) {
    if (!el) return;
    if (on) { el.dataset.orig = el.innerHTML; el.disabled = true; el.innerHTML = `<span class="spinner"></span> ${text || 'Working…'}`; }
    else { el.disabled = false; if (el.dataset.orig) { el.innerHTML = el.dataset.orig; delete el.dataset.orig; } }
  }

  document.addEventListener('click', async (e) => {
    const go = e.target.closest('[data-go]');
    if (go) { location.hash = '#/' + go.dataset.go; return; }
    const themeEl = e.target.closest('[data-theme-set]');
    if (themeEl) { state.theme = themeEl.dataset.themeSet; save(); render(current); return; }
    const mobile = e.target.closest('[data-mobile]');
    if (mobile) { state.device = 'mobile'; save(); return; }
    const plan = e.target.closest('[data-approve]');
    if (plan) {
      busy(plan, true, 'Approving…'); await sleep(650);
      const it = state.items.find(i => i.id === plan.dataset.approve);
      if (it) it.status = 'approved';
      save(); render(current); toast('Approved.'); return;
    }
    const act = e.target.closest('[data-action]');
    if (!act) return;
    if (act.dataset.action === 'send-code') {
      busy(act, true, 'Sending…'); await sleep(700);
      act.disabled = true; act.innerHTML = `<svg class="ic"><use href="#i-check"/></svg> Code sent`;
      const otp = $('[data-otp]'); if (otp) otp.hidden = false; toast('Code sent (demo).'); return;
    }
    if (act.dataset.action === 'generate') {
      state.generating = true; save(); render(current);
      await sleep(1100);
      state.generating = false; state.generated = true; save(); render(current); toast('Steps ready.'); return;
    }
    if (act.dataset.action === 'reset') {
      busy(act, true, 'Resetting…'); await sleep(500);
      localStorage.removeItem(KEY); state = clone(SEED); applyTheme(); location.hash = '#/gallery'; render('gallery'); return;
    }
  });

  back.addEventListener('click', () => { location.hash = '#/gallery'; });
  themeBtn.addEventListener('click', () => { state.theme = state.theme === 'light' ? 'dark' : 'light'; save(); applyTheme(); });
  device.addEventListener('click', (e) => {
    const b = e.target.closest('[data-device]');
    if (!b) return;
    state.device = b.dataset.device; save(); applyDevice(); render(current);
  });
  window.addEventListener('hashchange', route);
  applyTheme(); applyDevice(); route();
})();
