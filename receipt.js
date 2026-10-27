/* 내 X 영수증.
   올린 CSV에 있는 칸만 더해서 영수증처럼 보여 준다.
   없는 칸은 0으로 채우지 않고 빠졌다고 말한다.
   그림은 canvas로 이 브라우저에서만 만든다. */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const t = (k, p) => (XA.t ? XA.t(k, p) : k);
  const esc = (s) => (XA.esc ? XA.esc(s) : String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));
  const FONT = '"WenQuanYi Micro Hei","Droid Sans Fallback","Apple SD Gothic Neo","Noto Sans CJK KR",sans-serif';
  const LINES = [
    { key: 'imp', label: 'rc.line.imp', unit: 'rc.unit.imp' },
    { key: 'likes', label: 'rc.line.likes', unit: 'rc.unit.likes' },
    { key: 'rt', label: 'rc.line.rt', unit: 'rc.unit.rt' },
    { key: 'rep', label: 'rc.line.rep', unit: 'rc.unit.rep' },
    { key: 'bm', label: 'rc.line.bm', unit: 'rc.unit.bm' },
    { key: 'prof', label: 'rc.line.prof', unit: 'rc.unit.prof' },
    { key: 'nf', label: 'rc.line.nf', unit: 'rc.unit.nf' },
  ];

  function pad(n) { return String(n).padStart(2, '0'); }
  function fmtQty(n) {
    const v = Math.round(Number(n) || 0);
    try { return v.toLocaleString(XA.locale ? XA.locale() : 'ko-KR'); } catch (e) { return String(v); }
  }
  function ymd(key) {
    const d = new Date(key);
    return d.getUTCFullYear() + '.' + pad(d.getUTCMonth() + 1) + '.' + pad(d.getUTCDate());
  }
  function kstDayKey(ms) {
    const d = new Date(ms + 9 * 3600e3);
    return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  }
  function rowDayKey(A, r) {
    if (!A || !r) return null;
    if (A.mode === 'overview') return r.key == null ? null : r.key;
    if (r.dateRaw && XA.parseDay) {
      const k = XA.parseDay(r.dateRaw);
      if (k != null) return k;
    }
    if (r.ms != null) return kstDayKey(r.ms);
    return null;
  }
  function handleFrom(link) {
    const m = String(link || '').match(/https?:\/\/(?:www\.)?(?:x|twitter)\.com\/([^/?#]+)\/status\//i);
    if (!m) return '';
    if (/^(i|intent|share|home|search)$/i.test(m[1])) return '';
    return m[1];
  }
  function firstLine(text) {
    const line = String(text || '').split(/\n/).map((s) => s.trim()).find(Boolean) || '';
    const clean = line.replace(/https?:\/\/\S+/gi, '').replace(/\s+/g, ' ').trim();
    const chars = Array.from(clean);
    if (chars.length <= 32) return clean;
    return chars.slice(0, 32).join('') + '…';
  }
  function bars(n) {
    const s = String(Math.abs(Math.round(Number(n) || 0))).padStart(12, '0').slice(-12);
    return s.split('').map((ch) => (Number(ch) % 3) + 1);
  }

  function rowsOf(A) {
    if (!A) return [];
    return A.mode === 'overview' ? (A.days || []) : (A.posts || []);
  }

  XA.receiptModel = function (A, opts) {
    opts = opts || {};
    const hideSnippet = opts.hideSnippet !== false;
    const hideHandle = !!opts.hideHandle;
    if (!A || !A.map) return null;
    const rows = rowsOf(A);
    if (!rows.length) return { blocked: true, key: 'rc.why.empty' };
    if (A.map.imp == null) return { blocked: true, key: 'rc.why.noImp' };
    const present = LINES.filter((L) => A.map[L.key] != null);
    const missing = LINES.filter((L) => A.map[L.key] == null).map((L) => L.key);
    const lines = present.map((L) => {
      const qty = rows.reduce((s, r) => s + (Number(r[L.key]) || 0), 0);
      return { key: L.key, label: t(L.label), unit: t(L.unit), qty: qty };
    });
    const total = lines.reduce((s, l) => s + l.qty, 0);

    const dayKeys = [];
    rows.forEach((r) => {
      const key = rowDayKey(A, r);
      if (key != null) dayKeys.push(key);
    });
    const period = dayKeys.length ? { from: ymd(Math.min.apply(null, dayKeys)), to: ymd(Math.max.apply(null, dayKeys)) } : null;

    let handle = '';
    if (A.mode !== 'overview') {
      const counts = new Map();
      rows.forEach((p) => {
        const h = handleFrom(p.link);
        if (!h) return;
        counts.set(h, (counts.get(h) || 0) + 1);
      });
      let bestN = 0;
      counts.forEach((c, h) => { if (c > bestN) { handle = h; bestN = c; } });
    }

    let bestDay = null;
    if (A.map.imp != null) {
      const by = new Map();
      rows.forEach((r) => {
        const key = rowDayKey(A, r);
        if (key == null) return;
        by.set(key, (by.get(key) || 0) + (Number(r.imp) || 0));
      });
      by.forEach((qty, key) => {
        if (!bestDay || qty > bestDay.qty || (qty === bestDay.qty && key < bestDay.key)) bestDay = { key: key, qty: qty, label: ymd(key) };
      });
    }

    let busiest = null;
    if (A.mode !== 'overview') {
      const by = new Map();
      rows.forEach((p) => {
        if (p.hour == null) return;
        by.set(p.hour, (by.get(p.hour) || 0) + 1);
      });
      by.forEach((n, h) => {
        if (!busiest || n > busiest.n || (n === busiest.n && h < busiest.hour)) busiest = { hour: h, n: n };
      });
    }

    let snippet = '';
    let snippetPost = null;
    if (A.mode !== 'overview' && A.map.text != null) {
      rows.forEach((p) => {
        const line = firstLine(p.text);
        if (!line) return;
        const score = A.map.imp != null ? (Number(p.imp) || 0) : (Number(p.likes) || 0);
        const idx = p.i == null ? 0 : p.i;
        if (!snippetPost || score > snippetPost.score || (score === snippetPost.score && idx < snippetPost.idx)) {
          snippetPost = { score: score, idx: idx, line: line };
        }
      });
      if (snippetPost) snippet = snippetPost.line;
    }

    const pool = [];
    if (bestDay) pool.push({ id: 'day', qty: bestDay.qty, text: t('rc.note.day', { day: bestDay.label, n: fmtQty(bestDay.qty) }) });
    if (busiest) pool.push({ id: 'hour', qty: busiest.n, text: t('rc.note.hour', { h: String(busiest.hour), n: fmtQty(busiest.n) }) });
    if (snippet && !hideSnippet) pool.push({ id: 'line', text: t('rc.note.line', { line: snippet }) });
    let notes = [];
    if (snippet && !hideSnippet) {
      const lineNote = pool.find((n) => n.id === 'line');
      const other = pool.find((n) => n.id !== 'line');
      if (other) notes.push(other);
      if (lineNote) notes.push(lineNote);
    } else notes = pool.filter((n) => n.id !== 'line').slice(0, 2);
    if (!notes.length) notes = [{ id: 'plain', text: t('rc.note.plain') }];

    return {
      lines: lines,
      missing: missing,
      missingLabels: missing.map((k) => t('col.' + k)),
      total: total,
      period: period,
      handle: handle,
      hideHandle: hideHandle,
      hideSnippet: hideSnippet,
      snippet: snippet,
      bestDay: bestDay,
      busiest: busiest,
      notes: notes,
      n: rows.length,
      mode: A.mode === 'overview' ? 'overview' : 'content',
      bars: bars(total),
    };
  };

  function blockedHTML(st) {
    return `<div class="card rc-wrap"><h2>${esc(t('hub.card.receipt.t'))}</h2><p>${esc(t(st.key, st.params))}</p></div>`;
  }

  function paperHTML(model) {
    const star = esc(t('rc.star'));
    const handleLine = !model.handle
      ? esc(t('rc.noHandle'))
      : (model.hideHandle ? esc(t('rc.handleHidden')) : esc('@' + model.handle));
    const periodLine = model.period
      ? esc(model.period.from === model.period.to ? model.period.from : t('rc.period', model.period))
      : esc(t('rc.noDate'));
    const periodAttrs = model.period ? ` data-from="${esc(model.period.from)}" data-to="${esc(model.period.to)}"` : '';
    const basis = esc(t(model.mode === 'overview' ? 'rc.basisDays' : 'rc.basisPosts', { n: fmtQty(model.n) }));
    const flag = XA._isSample ? `<p class="rc-flag">${esc(t('rc.sample'))}</p>` : '';
    const lines = model.lines.map((l) => `<div class="rc-line" data-key="${esc(l.key)}" data-qty="${Math.round(l.qty)}"><span>${esc(l.label)}</span><span><b>${esc(fmtQty(l.qty))}</b> <span class="u">${esc(l.unit)}</span></span></div>`).join('');
    const notes = model.notes.map((n) => `<p class="rc-note" data-note="${esc(n.id)}"${n.qty != null ? ` data-qty="${Math.round(n.qty)}"` : ''}>${esc(n.text)}</p>`).join('');
    const miss = model.missingLabels.length
      ? `<p class="rc-miss" id="rc-miss">${esc(t('rc.missing', { cols: model.missingLabels.join(', ') }))}</p>`
      : '';
    const bar = model.bars.map((w) => `<i style="width:${w * 3}px"></i>`).join('');
    return `<div class="rc-paper" id="rc-paper">
      ${flag}
      <div class="rc-star">${star}</div>
      <p class="rc-sub" id="rc-handle">${handleLine}</p>
      <p class="rc-sub" id="rc-period"${periodAttrs}>${periodLine}</p>
      <p class="rc-sub">${basis}</p>
      <hr class="rc-rule">
      ${lines}
      <hr class="rc-rule">
      <div class="rc-line rc-total" data-key="total" data-qty="${Math.round(model.total)}"><span>${esc(t('rc.total'))}</span><b>${esc(fmtQty(model.total))}</b></div>
      <p class="rc-sub">${esc(t('rc.totalHint'))}</p>
      <hr class="rc-rule">
      <div id="rc-note">${notes}</div>
      ${miss}
      <div class="rc-bars" aria-hidden="true">${bar}</div>
      <p class="rc-thanks">${esc(t('rc.thanks'))}</p>
      <p class="rc-site">${esc(t('brand.name'))} · tuki0609.github.io/account-compass</p>
    </div><p class="rc-honest">${esc(t('rc.honest'))}</p>`;
  }

  function wrapText(g, text, maxW) {
    const out = [];
    let line = '';
    for (const ch of Array.from(String(text || ''))) {
      if (g.measureText(line + ch).width > maxW && line) { out.push(line); line = ch; }
      else line += ch;
    }
    if (line) out.push(line);
    return out.length ? out : [''];
  }

  XA.receiptDraw = function (model) {
    const W = 1080;
    const lineH = 54;
    const noteLines = [];
    const missLines = [];
    const c0 = document.createElement('canvas');
    const g0 = c0.getContext('2d');
    g0.font = '400 32px ' + FONT;
    model.notes.forEach((n) => wrapText(g0, n.text, W - 160).forEach((ln) => noteLines.push(ln)));
    if (model.missingLabels.length) {
      g0.font = '400 28px ' + FONT;
      wrapText(g0, t('rc.missing', { cols: model.missingLabels.join(', ') }), W - 160).forEach((ln) => missLines.push(ln));
    }
    const H = 220 + model.lines.length * lineH + 80 + noteLines.length * 44 + missLines.length * 40 + 280;
    const c = document.createElement('canvas');
    c.width = W; c.height = Math.max(H, 1350);
    const g = c.getContext('2d');
    g.fillStyle = '#efe7d6';
    g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = '#f7f3ea';
    g.fillRect(70, 48, W - 140, c.height - 96);
    g.fillStyle = '#1c1917';
    g.textAlign = 'center';
    g.font = '800 54px ' + FONT;
    let y = 140;
    g.fillText(t('rc.star'), W / 2, y);
    g.font = '600 32px ' + FONT;
    y += 58;
    const handleLine = !model.handle ? t('rc.noHandle') : (model.hideHandle ? t('rc.handleHidden') : '@' + model.handle);
    g.fillText(handleLine, W / 2, y);
    y += 46;
    g.fillText(model.period ? (model.period.from === model.period.to ? model.period.from : t('rc.period', model.period)) : t('rc.noDate'), W / 2, y);
    y += 46;
    g.fillText(t(model.mode === 'overview' ? 'rc.basisDays' : 'rc.basisPosts', { n: fmtQty(model.n) }), W / 2, y);
    y += 36;
    g.strokeStyle = '#44403c';
    g.setLineDash([8, 8]);
    g.beginPath(); g.moveTo(120, y); g.lineTo(W - 120, y); g.stroke();
    g.setLineDash([]);
    y += 64;
    g.textAlign = 'left';
    g.font = '600 36px ' + FONT;
    model.lines.forEach((l) => {
      g.fillText(l.label, 120, y);
      const right = fmtQty(l.qty) + '  ' + l.unit;
      g.textAlign = 'right';
      g.fillText(right, W - 120, y);
      g.textAlign = 'left';
      y += lineH;
    });
    y += 8;
    g.setLineDash([8, 8]);
    g.beginPath(); g.moveTo(120, y); g.lineTo(W - 120, y); g.stroke();
    g.setLineDash([]);
    y += 64;
    g.font = '800 42px ' + FONT;
    g.fillText(t('rc.total'), 120, y);
    g.textAlign = 'right';
    g.fillText(fmtQty(model.total), W - 120, y);
    g.textAlign = 'left';
    y += 48;
    g.font = '400 28px ' + FONT;
    g.fillText(t('rc.totalHint'), 120, y);
    y += 56;
    g.font = '400 32px ' + FONT;
    noteLines.forEach((ln) => { g.fillText(ln, 120, y); y += 44; });
    if (missLines.length) {
      y += 8;
      g.font = '400 28px ' + FONT;
      missLines.forEach((ln) => { g.fillText(ln, 120, y); y += 40; });
    }
    y += 16;
    let x = 120;
    model.bars.forEach((w) => {
      const bw = w * 10;
      g.fillRect(x, y, bw, 70);
      x += bw + 8;
    });
    y += 120;
    g.textAlign = 'center';
    g.font = '800 40px ' + FONT;
    g.fillText(t('rc.thanks'), W / 2, y);
    y += 48;
    g.font = '700 26px ' + FONT;
    g.fillText(t('brand.name') + '  ·  tuki0609.github.io/account-compass', W / 2, Math.min(y, c.height - 70));
    return c;
  };

  function prefs() {
    return {
      hideSnippet: XA._rcHideSnippet !== false,
      hideHandle: !!XA._rcHideHandle,
    };
  }

  function render(el, A) {
    const mod = XA.moduleById('receipt');
    const st = XA.cardStatus(mod, A);
    if (!A || st.state !== 'ready') {
      el.innerHTML = blockedHTML(st.state === 'ready' ? { key: 'rc.why.empty' } : st);
      return;
    }
    const model = XA.receiptModel(A, prefs());
    if (!model || model.blocked) {
      el.innerHTML = blockedHTML(model || { key: 'rc.why.empty' });
      return;
    }
    el.innerHTML = `<div class="rc-wrap">
      <div class="rc-tools">
        <label><input type="checkbox" id="rc-hide-line" ${model.hideSnippet ? 'checked' : ''}> ${esc(t('rc.hideLine'))}</label>
        <label><input type="checkbox" id="rc-hide-handle" ${model.hideHandle ? 'checked' : ''}> ${esc(t('rc.hideHandle'))}</label>
      </div>
      ${paperHTML(model)}
      <div class="row gap wrap-row" style="margin-top:10px"><button type="button" class="btn" id="rc-save">${esc(t('rc.save'))}</button></div>
      <p class="rc-honest">${esc(t('rc.saveNote'))}</p>
    </div>`;
    const redraw = () => {
      XA._rcHideSnippet = document.getElementById('rc-hide-line').checked;
      XA._rcHideHandle = document.getElementById('rc-hide-handle').checked;
      render(el, A);
    };
    document.getElementById('rc-hide-line').addEventListener('change', redraw);
    document.getElementById('rc-hide-handle').addEventListener('change', redraw);
    document.getElementById('rc-save').addEventListener('click', () => {
      const live = XA.receiptModel(A, prefs());
      const canvas = XA.receiptDraw(live);
      const a = document.createElement('a');
      a.href = canvas.toDataURL('image/png');
      a.download = 'x-receipt.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  }

  function receiptReady(A) {
    if (!A) return { state: 'empty', key: 'hub.state.empty' };
    if (!A.map || A.map.imp == null) return { state: 'blocked', key: 'rc.why.noImp' };
    if (!rowsOf(A).length) return { state: 'blocked', key: 'rc.why.empty' };
    return { state: 'ready', key: 'hub.state.ready' };
  }

  if (XA.registerModule) {
    XA.registerModule({
      id: 'receipt',
      order: 3,
      category: 'fun',
      status: 'ready',
      icon: '🧾',
      titleKey: 'hub.card.receipt.t',
      descKey: 'hub.card.receipt.d',
      needsKey: 'hub.needs.receipt',
      requires: ['imp'],
      ready: receiptReady,
      render: render,
    });
  }
  if (XA.mountHome) XA.mountHome();
})();
