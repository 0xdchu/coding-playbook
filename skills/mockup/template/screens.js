/* Screen renderers. Keep screens free of element ids so thumbnails can render them many times. */
(function (g) {
  const I = (n) => `<svg class="ic"><use href="#i-${n}"/></svg>`;
  const S = (state) => state.screens;
  const pending = (state) => state.items.filter(i => i.status === 'pending').length;

  function nav(active, state) {
    const items = S(state).filter(s => s.id !== 'login');
    return `<aside class="sidebar">
      <div class="side-brand">${state.product}<small>Demo workspace</small></div>
      ${items.map(s => `<button class="nav-item${s.id === active ? ' active' : ''}" data-go="${s.id}">
        ${I(s.id === 'board' ? 'list' : 'gear')}<span>${s.title}</span></button>`).join('')}
      <div class="side-note">Agent is on while your machine is open</div>
    </aside>`;
  }
  function mobileNav(active, state) {
    const items = S(state).filter(s => s.id !== 'login');
    return `<nav class="mobile-nav">${items.map(s =>
      `<a href="#/${s.id}" class="${s.id === active ? 'active' : ''}">${I(s.id === 'board' ? 'list' : 'gear')}<span>${s.title}</span></a>`).join('')}</nav>`;
  }
  function shell(active, body, state) {
    return `<div class="screen"><div class="app">${nav(active, state)}<div class="main">${body}</div></div>${mobileNav(active, state)}</div>`;
  }

  function gallery(state) {
    const groups = [...new Set(S(state).map(s => s.group))];
    let html = `<div class="gallery wrap">
      <div class="gallery-head"><div>
        <span class="kicker">${state.product} · prototype</span>
        <h1>Product mockups</h1>
        <p class="lead">Every screen of the flow, one card each. Open a page on web or mobile, in light or dark. Buttons react on hover, actions show loading then complete.</p>
        <div class="meta"><span class="badge line">${S(state).length} screens</span><span class="badge line">Web + Mobile</span><span class="badge line">Light + Dark</span></div>
      </div><div class="row"><a class="btn btn-primary" href="#/${S(state)[1].id}">Open ${S(state)[1].title} ${I('arrow')}</a></div></div>`;
    groups.forEach(group => {
      html += `<div class="gallery-group"><h2>${group}</h2><span>${S(state).filter(s => s.group === group).length}</span></div><div class="grid">`;
      S(state).filter(s => s.group === group).forEach(s => {
        html += `<article class="card"><div class="thumb"><div class="thumb-canvas">${RENDER[s.id](state)}</div></div>
          <div class="mock-meta"><div class="mock-title"><h3>${s.title}</h3><small>${s.desc.split(' ').length} words</small></div>
          <p class="sub">${s.desc}</p><div class="mock-links"><a href="#/${s.id}">Open</a><a class="muted" href="#/${s.id}" data-mobile>Mobile</a></div></div></article>`;
      });
      html += `</div>`;
    });
    return html + `</div>`;
  }

  function login(state) {
    return `<div class="screen"><div class="hero"><div class="hero-copy">
      <span class="kicker">${state.product}</span>
      <h1>A workspace that keeps your work in one place.</h1>
      <p>Sign in with a code. No password to remember.</p>
      <div class="field"><label>Email</label><input class="input" value="you@example.com"></div>
      <button class="btn btn-primary btn-block" type="button" data-action="send-code">Send code</button>
      <div data-otp hidden><p class="sub" style="margin:8px 0">Code sent. Demo code is 2048.</p>
        <div class="otp" style="margin-bottom:10px"><input value="2"><input value="0"><input value="4"><input value="8"></div>
        <a class="btn btn-primary btn-block" href="#/board">Enter ${I('arrow')}</a></div>
      <p class="hint">Demo only. No email is sent.</p>
    </div><div class="hero-art">[ product image ]</div></div></div>`;
  }

  function item(state, it) {
    const done = it.status === 'approved';
    return `<div class="item${done ? ' done' : ''}">
      ${I(done ? 'check' : 'spark')}
      <div><b>${it.title}</b><p>${it.detail}</p></div>
      <div class="actions">${done ? `<span class="badge ok">Approved</span>` : `<button class="btn btn-sm btn-primary" data-approve="${it.id}">Approve</button>`}</div>
    </div>`;
  }

  function board(state) {
    const ready = state.items;
    return shell('board', `
      <div class="page-head"><div><h1>Board</h1><p>One brief goes in. Each step is a card you approve before it ships.</p></div>
      <a class="btn btn-sm" href="#/board">${I('check')} ${pending(state)} waiting</a></div>
      <div class="panel"><div class="field"><label>Brief</label><textarea class="textarea">A short brief: the goal, the audience and the one thing to say.</textarea></div>
        <div class="row" style="justify-content:space-between;margin-top:10px"><span class="hint">Nothing ships until you approve.</span>
        <button class="btn btn-primary" type="button" data-action="generate">${I('spark')} Generate steps</button></div></div>
      ${state.generating ? `<div class="stack" style="margin-top:14px">${[0,1,2].map(() => `<div class="panel"><div class="skeleton" style="width:40%"></div><div class="skeleton"></div><div class="skeleton" style="width:70%"></div></div>`).join('')}</div>` : ''}
      <div class="grid-2" style="margin-top:14px">
        <div class="stat"><b>${pending(state)}</b><span>Waiting for approval</span></div>
        <div class="stat"><b>${state.items.length - pending(state)}</b><span>Approved</span></div>
      </div>
      <div class="stack" style="margin-top:14px">${ready.map(it => item(state, it)).join('')}</div>
    `, state);
  }

  function settings(state) {
    return shell('settings', `
      <div class="page-head"><div><h1>Settings</h1><p>Theme, language and the demo state.</p></div></div>
      <div class="grid-2">
        <div class="panel"><h2>Theme</h2><p class="sub">Dark or light is the user's choice.</p>
          <div class="seg" style="margin-top:10px"><button type="button" data-theme-set="light" aria-pressed="${state.theme === 'light'}">${I('sun')} Light</button>
          <button type="button" data-theme-set="dark" aria-pressed="${state.theme === 'dark'}">${I('moon')} Dark</button></div></div>
        <div class="panel"><h2>Demo data</h2><p class="sub">Seed lives in localStorage. Reset to the first state.</p>
          <button class="btn" style="margin-top:10px" type="button" data-action="reset">${I('refresh')} Reset demo</button></div>
      </div>
    `, state);
  }

  const RENDER = { login, board, settings };
  g.Mockups = { screens: S, render: (name, state) => (name === 'gallery' ? gallery(state) : RENDER[name] ? RENDER[name](state) : `<div class="wrap">Unknown screen ${name}</div>`) };
})(typeof window !== 'undefined' ? window : globalThis);
