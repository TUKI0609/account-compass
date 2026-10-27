/* 홈 카드 모음.
   CSV는 홈에서 한 번만 읽고, 카드는 그 결과를 나눠 본다.
   새 카드는 registerModule 한 번으로 등록한다 (status:'soon' 이면 아직 열리지 않음).

   XA.registerModule({
     id: 'my-card',          // 고유 id
     order: 6,               // 홈에 보이는 번호
     category: 'fun',        // analyze | fun | soon
     status: 'ready',        // 'ready' 또는 'soon'
     icon: '✨',
     titleKey: 'hub.card.my.t',
     descKey: 'hub.card.my.d',
     needsKey: 'hub.needs.my',
     requires: ['text'],     // 없으면 막는 칸. 본문이 필요하면 'text'
     ready: function (A) {}, // 선택. {state, key, params} 를 돌려줌
     render: function (el, A) {} // status가 ready일 때 카드 안을 그림 (나침반 제외)
   });
*/
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const modules = [];
  const CATS = [
    { id: 'analyze', titleKey: 'hub.cat.analyze' },
    { id: 'fun', titleKey: 'hub.cat.fun' },
    { id: 'soon', titleKey: 'hub.cat.soon' },
  ];
  XA.hubCategories = CATS;

  function esc(s) {
    return XA.esc ? XA.esc(s) : String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  const t = (k, p) => (XA.t ? XA.t(k, p) : k);

  XA.registerModule = function (mod) {
    if (!mod || !mod.id) return false;
    if (modules.some((m) => m.id === mod.id)) return false;
    modules.push(mod);
    modules.sort((a, b) => (a.order || 99) - (b.order || 99) || String(a.id).localeCompare(String(b.id)));
    return true;
  };
  XA.unregisterModule = function (id) {
    const i = modules.findIndex((m) => m.id === id);
    if (i < 0) return false;
    modules.splice(i, 1);
    return true;
  };
  XA.modules = modules;
  XA.moduleById = (id) => modules.find((m) => m.id === id);

  function defaultReady(mod, A) {
    if (!A) return { state: 'empty', key: 'hub.state.empty' };
    const req = mod.requires || [];
    if (A.mode === 'overview' && req.indexOf('text') >= 0) return { state: 'blocked', key: 'hub.why.overview' };
    if (A.mode !== 'overview' && A.map) {
      const miss = req.filter((k) => A.map[k] == null);
      if (miss.length) {
        const cols = miss.map((k) => t('col.' + k)).join(', ');
        return { state: 'blocked', key: 'hub.why.missing', params: { cols: cols } };
      }
    }
    return { state: 'ready', key: 'hub.state.ready' };
  }

  XA.cardStatus = function (mod, A) {
    if (!mod) return { state: 'blocked', key: 'hub.why.noFile' };
    if (mod.status === 'soon') return { state: 'soon', key: 'hub.state.soon' };
    if (typeof mod.ready === 'function') return mod.ready(A);
    return defaultReady(mod, A);
  };

  function pad(n) { return String(n).padStart(2, '0'); }

  XA.mountHome = function () {
    const board = document.getElementById('hub-board');
    if (!board) return;
    const A = XA.last && XA.last.mode ? XA.last : (XA.last || null);
    const status = document.getElementById('home-status');
    if (status) {
      if (!A) { status.innerHTML = ''; status.hidden = true; }
      else {
        status.hidden = false;
        const name = XA._fileLabel || 'CSV';
        status.innerHTML = `<p>${esc(t(XA._isSample ? 'hub.fileOkSample' : 'hub.fileOk', { name: name }))}</p>`;
      }
    }
    const ask = document.getElementById('hub-ask');
    const askText = document.getElementById('hub-ask-text');
    const strip = document.getElementById('drop');
    if (ask && askText) {
      if (A || !XA._askId) {
        if (A) XA._askId = null;
        ask.hidden = true;
        if (strip) strip.classList.remove('need');
      } else {
        const asked = XA.moduleById(XA._askId);
        ask.hidden = false;
        askText.textContent = t('hub.ask', { name: asked ? t(asked.titleKey) : '' });
        if (strip) strip.classList.add('need');
      }
    }
    const blocks = CATS.map((cat) => {
      const list = modules.filter((m) => m.category === cat.id);
      if (!list.length) return '';
      const cards = list.map((mod) => {
        const st = XA.cardStatus(mod, A);
        const soon = mod.status === 'soon';
        const blocked = st.state === 'blocked';
        const cls = 'hub-card' + (soon ? ' soon' : '') + (blocked ? ' blocked' : '') + (st.state === 'ready' ? ' is-ready' : '');
        const num = pad(mod.order || 0);
        const why = (blocked || soon) ? `<span class="why">${esc(t(st.key, st.params))}</span>` : (st.state === 'empty' ? `<span class="needs quiet">${esc(t('hub.state.empty'))}</span>` : `<span class="ready-flag">${esc(t('hub.state.ready'))}</span>`);
        const tag = `<span class="tag">${esc(t(cat.titleKey))}</span>`;
        const needs = `<span class="needs">${esc(t('hub.needsLabel'))} ${esc(t(mod.needsKey))}</span>`;
        const label = num + ' ' + t(mod.titleKey);
        const head = `<span class="hd"><span class="num">${num}</span><span class="ic" aria-hidden="true">${mod.icon || '·'}</span><span class="tt">${esc(t(mod.titleKey))}</span></span>`;
        const body = `${head}<span class="dd">${esc(t(mod.descKey))}</span><span class="meta">${tag}${needs}${why}</span>`;
        if (soon) {
          return `<button type="button" class="${cls}" data-mod="${esc(mod.id)}" disabled aria-disabled="true">${body}</button>`;
        }
        return `<button type="button" class="${cls}" data-mod="${esc(mod.id)}" aria-label="${esc(label)}">${body}</button>`;
      }).join('');
      return `<section class="hub-cat" data-cat="${esc(cat.id)}"><h2>${esc(t(cat.titleKey))}</h2><div class="hub-grid">${cards}</div></section>`;
    }).join('');
    board.innerHTML = blocks;
    board.querySelectorAll('.hub-card:not(:disabled)').forEach((btn) => {
      btn.addEventListener('click', () => {
        const mod = XA.moduleById(btn.dataset.mod);
        const st = XA.cardStatus(mod, XA.last || null);
        if (!XA.last || st.state === 'empty') {
          XA.promptForCsv(mod);
          return;
        }
        XA.openCard(btn.dataset.mod);
      });
    });
  };

  XA.promptForCsv = function (mod) {
    if (!mod) return;
    XA._askId = mod.id;
    const ask = document.getElementById('hub-ask');
    const askText = document.getElementById('hub-ask-text');
    const strip = document.getElementById('drop');
    if (ask && askText) {
      ask.hidden = false;
      askText.textContent = t('hub.ask', { name: t(mod.titleKey) });
    }
    if (strip) {
      strip.classList.add('need');
      strip.scrollIntoView({ block: 'nearest' });
    }
    const pick = document.getElementById('csv-pick');
    if (pick) pick.focus();
  };

  XA.syncCompassEmpty = function () {
    const empty = document.getElementById('compass-empty');
    if (!empty) return;
    empty.hidden = !!(XA.last && (XA.last.posts || XA.last.days));
  };

  XA.openCard = function (id) {
    const mod = XA.moduleById(id);
    if (!mod || mod.status === 'soon') return false;
    const home = document.getElementById('home');
    const view = document.getElementById('card-view');
    const compass = document.getElementById('card-compass');
    const dyn = document.getElementById('card-dynamic');
    if (!home || !view || !compass || !dyn) return false;
    home.hidden = true;
    view.hidden = false;
    XA._openCard = id;
    if (id === 'compass') {
      compass.hidden = false;
      dyn.hidden = true;
      dyn.innerHTML = '';
      XA.syncCompassEmpty();
    } else {
      compass.hidden = true;
      dyn.hidden = false;
      dyn.innerHTML = '';
      dyn.dataset.card = id;
      if (typeof mod.render === 'function') mod.render(dyn, XA.last || null);
    }
    const back = document.getElementById('back-home');
    if (back) back.focus();
    window.scrollTo({ top: 0 });
    return true;
  };

  XA.closeCard = function () {
    const home = document.getElementById('home');
    const view = document.getElementById('card-view');
    if (home) home.hidden = false;
    if (view) view.hidden = true;
    XA._openCard = null;
    window.scrollTo({ top: 0 });
  };

  XA.syncHub = function () {
    XA.mountHome();
    if (XA._openCard === 'compass') XA.syncCompassEmpty();
    if (XA._openCard && XA._openCard !== 'compass') {
      const mod = XA.moduleById(XA._openCard);
      const dyn = document.getElementById('card-dynamic');
      if (mod && dyn && typeof mod.render === 'function') mod.render(dyn, XA.last || null);
    }
  };

  function bindCompassNav() {
    const nav = document.getElementById('compass-nav');
    if (!nav || nav.dataset.bound) return;
    nav.dataset.bound = '1';
    nav.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-sec]');
      if (!btn) return;
      const panel = document.getElementById('sec-' + btn.dataset.sec);
      if (!panel) return;
      const open = panel.hidden;
      document.querySelectorAll('.csec').forEach((p) => { p.hidden = true; });
      nav.querySelectorAll('button[data-sec]').forEach((b) => b.setAttribute('aria-expanded', 'false'));
      if (open) {
        panel.hidden = false;
        btn.setAttribute('aria-expanded', 'true');
        panel.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  function bindBack() {
    const b = document.getElementById('back-home');
    if (!b || b.dataset.bound) return;
    b.dataset.bound = '1';
    b.addEventListener('click', () => XA.closeCard());
  }

  XA.registerModule({
    id: 'compass',
    order: 1,
    category: 'analyze',
    status: 'ready',
    icon: '🧭',
    titleKey: 'hub.card.compass.t',
    descKey: 'hub.card.compass.d',
    needsKey: 'hub.needs.compass',
    requires: [],
    ready: function (A) {
      if (!A) return { state: 'empty', key: 'hub.state.empty' };
      return { state: 'ready', key: 'hub.state.ready' };
    },
  });

  XA.registerModule({
    id: 'soon-calendar',
    order: 4,
    category: 'soon',
    status: 'soon',
    icon: '🗓️',
    titleKey: 'hub.card.soonCal.t',
    descKey: 'hub.card.soonCal.d',
    needsKey: 'hub.needs.soonCal',
    requires: ['date'],
  });
  XA.registerModule({
    id: 'soon-hooks',
    order: 5,
    category: 'soon',
    status: 'soon',
    icon: '✍️',
    titleKey: 'hub.card.soonHook.t',
    descKey: 'hub.card.soonHook.d',
    needsKey: 'hub.needs.soonHook',
    requires: ['text'],
  });
  bindCompassNav();
  bindBack();
  document.addEventListener('langchange', () => { if (XA.syncHub) XA.syncHub(); });
})();
