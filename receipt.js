/* 내 X 영수증: 팔로워 1명 얼마?
   줄은 노출 합 ÷ 그 칸의 합이다. 단위가 다른 수를 더하지 않는다.
   나누는 쪽이 0이면 품절. 없는 칸은 0으로 채우지 않는다.
   등급 기준은 XA.PRICE 한곳에만 있다. */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const t = (k, p) => (XA.t ? XA.t(k, p) : k);
  const esc = (s) => (XA.esc ? XA.esc(s) : String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));
  const FONT = '"WenQuanYi Micro Hei","Droid Sans Fallback","Apple SD Gothic Neo","Noto Sans CJK KR",sans-serif';
  const LINES = [
    { key: 'nf', label: 'rc.line.nf' },
    { key: 'likes', label: 'rc.line.likes' },
    { key: 'bm', label: 'rc.line.bm' },
    { key: 'rep', label: 'rc.line.rep' },
    { key: 'prof', label: 'rc.line.prof' },
  ];
  const GRADE_ORDER = ['luxury', 'value', 'window', 'save', 'taste'];
  const GRADE_NAME = {
    luxury: 'rc.grade.luxury', value: 'rc.grade.value', window: 'rc.grade.window', save: 'rc.grade.save',
    taste: 'rc.grade.taste', first: 'rc.grade.first',
  };
  const GRADE_LINE = {
    luxury: 'rc.gradeLine.luxury', value: 'rc.gradeLine.value', window: 'rc.gradeLine.window', save: 'rc.gradeLine.save',
    taste: 'rc.gradeLine.taste', first: 'rc.gradeLine.first',
  };
  const P = {
    MIN_POSTS: 10,
    LUXURY: 5000,
    VALUE: 800,
    WINDOW_VISIT: 300,
    WINDOW_CONV: 0.05,
    SAVE_MULT: 2,
    TASTE: 300,
    EXP_MIN_IMP: 500,
    EXP_MIN_NF: 1,
    COUPON_MIN: 3,
  };
  XA.PRICE = P;

  function pad(n) { return String(n).padStart(2, '0'); }
  function fmtInt(n) {
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
  function hourFromId(p) {
    if (!p || !XA.timeFromId) return null;
    const ms = XA.timeFromId(String(p.id || ''));
    if (ms == null) return null;
    return new Date(ms + 9 * 3600e3).getUTCHours();
  }
  function rowsOf(A) {
    if (!A) return [];
    return A.mode === 'overview' ? (A.days || []) : (A.posts || []);
  }
  function sumKey(rows, key) { return rows.reduce((s, r) => s + (Number(r[key]) || 0), 0); }

  function gradeDistance(id, prices, conv) {
    if (id === 'luxury') {
      const fp = prices.nf;
      if (fp == null) return null;
      if (fp >= P.LUXURY) return 0;
      return (P.LUXURY - fp) / P.LUXURY;
    }
    if (id === 'value') {
      const fp = prices.nf;
      if (fp == null) return null;
      if (fp <= P.VALUE) return 0;
      return (fp - P.VALUE) / P.VALUE;
    }
    if (id === 'window') {
      const vp = prices.prof;
      if (vp == null || conv == null) return null;
      const visitOk = vp <= P.WINDOW_VISIT;
      const convOk = conv < P.WINDOW_CONV;
      if (visitOk && convOk) return 0;
      const dVisit = visitOk ? 0 : Math.max((vp - P.WINDOW_VISIT) / P.WINDOW_VISIT, 1e-9);
      const dConv = convOk ? 0 : Math.max((conv - P.WINDOW_CONV) / P.WINDOW_CONV, 1e-9);
      return Math.max(dVisit, dConv);
    }
    if (id === 'save') {
      const bp = prices.bm;
      const lp = prices.likes;
      if (bp == null || lp == null || !(lp > 0)) return null;
      const line = lp * P.SAVE_MULT;
      if (bp < line) return 0;
      return Math.max((bp - line) / line, 1e-9);
    }
    if (id === 'taste') {
      const rp = prices.rep;
      if (rp == null) return null;
      if (rp <= P.TASTE) return 0;
      return Math.max((rp - P.TASTE) / P.TASTE, 1e-9);
    }
    return null;
  }

  function pickGrade(n, prices, conv) {
    if (n < P.MIN_POSTS) return 'first';
    let best = null;
    let bestD = Infinity;
    GRADE_ORDER.forEach((id) => {
      const d = gradeDistance(id, prices, conv);
      if (d == null || !isFinite(d)) return;
      if (d < bestD) { bestD = d; best = id; }
    });
    return best || 'value';
  }

  XA.receiptModel = function (A, opts) {
    opts = opts || {};
    const hideSnippet = opts.hideSnippet !== false;
    const hideHandle = !!opts.hideHandle;
    if (!A || !A.map) return null;
    const rows = rowsOf(A);
    if (!rows.length) return { blocked: true, key: 'rc.why.empty' };
    if (A.map.imp == null) return { blocked: true, key: 'rc.why.noImp' };
    const imp = sumKey(rows, 'imp');
    const present = LINES.filter((L) => A.map[L.key] != null);
    const missing = LINES.filter((L) => A.map[L.key] == null).map((L) => L.key);
    const prices = {};
    const lines = present.map((L) => {
      const qty = sumKey(rows, L.key);
      if (!(qty > 0)) {
        prices[L.key] = null;
        return { key: L.key, label: t(L.label), sold: true, qty: qty, imp: imp };
      }
      const raw = imp / qty;
      prices[L.key] = raw;
      return { key: L.key, label: t(L.label), sold: false, qty: qty, imp: imp, raw: raw, rounded: Math.round(raw) };
    });
    const conv = (A.map.prof != null && A.map.nf != null && sumKey(rows, 'prof') > 0) ? sumKey(rows, 'nf') / sumKey(rows, 'prof') : null;
    const n = rows.length;
    const grade = pickGrade(n, prices, conv);

    const dayKeys = [];
    rows.forEach((r) => { const key = rowDayKey(A, r); if (key != null) dayKeys.push(key); });
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

    let expensive = null;
    let cheap = null;
    if (A.mode !== 'overview' && A.map.nf != null) {
      rows.forEach((p, i) => {
        const nf = Number(p.nf) || 0;
        const pimp = Number(p.imp) || 0;
        if (nf < P.EXP_MIN_NF || pimp < P.EXP_MIN_IMP) return;
        const day = rowDayKey(A, p);
        if (day == null) return;
        const raw = pimp / nf;
        const item = { day: day, date: ymd(day), raw: raw, rounded: Math.round(raw), i: p.i == null ? i : p.i, snippet: firstLine(p.text) };
        const earlier = !expensive || item.raw > expensive.raw || (item.raw === expensive.raw && (item.day < expensive.day || (item.day === expensive.day && item.i < expensive.i)));
        if (earlier) expensive = item;
        const cheaper = !cheap || item.raw < cheap.raw || (item.raw === cheap.raw && (item.day < cheap.day || (item.day === cheap.day && item.i < cheap.i)));
        if (cheaper) cheap = item;
      });
    }

    let coupon = null;
    if (A.mode !== 'overview' && rows.length && imp > 0) {
      const by = new Map();
      let timedImp = 0;
      let timedN = 0;
      rows.forEach((p) => {
        const h = hourFromId(p);
        if (h == null) return;
        const pimp = Number(p.imp) || 0;
        const cur = by.get(h) || { n: 0, imp: 0 };
        cur.n += 1; cur.imp += pimp;
        by.set(h, cur);
        timedN += 1; timedImp += pimp;
      });
      const overall = rows.length ? imp / rows.length : 0;
      let best = null;
      by.forEach((cur, h) => {
        if (cur.n < P.COUPON_MIN) return;
        const avg = cur.imp / cur.n;
        const pct = overall > 0 ? Math.round((avg / overall - 1) * 100) : 0;
        if (pct <= 0) return;
        if (!best || pct > best.pct || (pct === best.pct && h < best.hour)) best = { hour: h, pct: pct, avg: avg, n: cur.n };
      });
      if (best) coupon = { hour: best.hour, pct: best.pct, avg: best.avg, overall: overall, n: best.n, timed: timedN, timedImp: timedImp };
    }

    let refund = null;
    const ov = XA.lastOverview;
    if (ov && ov.map && ov.map.unf != null && (ov.days || []).length) {
      refund = { qty: sumKey(ov.days, 'unf') };
    }

    const nfPresent = A.map.nf != null;
    const nfQty = nfPresent ? sumKey(rows, 'nf') : null;
    const headlineKind = !nfPresent ? 'miss' : (prices.nf == null ? 'sold' : 'price');
    const show = headlineKind === 'price' ? Math.round(prices.nf) : null;
    return {
      lines: lines,
      missing: missing,
      missingLabels: missing.map((k) => t('col.' + k)),
      prices: prices,
      conv: conv,
      grade: grade,
      headline: show,
      period: period,
      handle: handle,
      hideHandle: hideHandle,
      hideSnippet: hideSnippet,
      expensive: expensive,
      cheap: cheap,
      coupon: coupon,
      refund: refund,
      nfQty: nfQty,
      headlineKind: headlineKind,
      imp: imp,
      n: n,
      mode: A.mode === 'overview' ? 'overview' : 'content',
      showPrice: show,
    };
  };
  function modelHit(raw) { return raw == null ? null : Math.round(raw); }

  XA.priceCaption = function (model, lang) {
    lang = lang || (XA.lang || 'ko');
    const url = XA.siteUrl ? XA.siteUrl({ c: 'price', lang: lang }) : 'https://tuki0609.github.io/account-compass/?c=price&lang=' + lang;
    const dict = (XA.I18N && XA.I18N[lang]) || {};
    const num = model.headlineKind === 'price' ? fmtInt(model.headline) : (model.headlineKind === 'miss' ? '—' : (dict['rc.sold'] || ''));
    if (lang === 'en') return 'One follower cost me ' + num + ' impressions 🧾 What\'s yours?\n' + url;
    if (lang === 'ja') return 'フォロワー1人の値段は表示' + num + '回でした 🧾 あなたはいくら？\n' + url;
    return '제 팔로워 1명 값은 노출 ' + num + '회였습니다 🧾 당신은 얼마?\n' + url;
  };

  function barBits(seed) {
    const s = String(Math.abs(Math.round(Number(seed) || 0))).padStart(6, '0');
    const bits = [];
    for (let i = 0; i < s.length; i++) {
      const n = Number(s[i]);
      bits.push(2 + (n % 3));
      bits.push(1 + (n % 2));
    }
    const out = [];
    while (out.length < 40) out.push.apply(out, bits);
    return out.slice(0, 40);
  }
  function barcodeHTML(seed) {
    const bits = barBits(seed);
    return `<div class="rc-bars" id="rc-barcode" data-seed="${Math.round(Number(seed) || 0)}" aria-hidden="true">${bits.map((w, i) => `<i style="flex:${w} 1 0;background:${i % 2 ? 'transparent' : '#1c1917'}"></i>`).join('')}</div>`;
  }
  function roundRect(g, x, y, w, h, r) {
    g.beginPath();
    g.moveTo(x + r, y);
    g.arcTo(x + w, y, x + w, y + h, r);
    g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r);
    g.arcTo(x, y, x + w, y, r);
    g.closePath();
  }

  function lineHTML(l) {
    if (l.sold) {
      return `<div class="rc-line" data-key="${esc(l.key)}" data-sold="1" data-num="${Math.round(l.qty)}" data-imp="${Math.round(l.imp)}"><span>${esc(l.label)}</span><span class="sold">${esc(t('rc.sold'))}</span></div>`;
    }
    return `<div class="rc-line" data-key="${esc(l.key)}" data-qty="${l.rounded}" data-raw="${l.raw}" data-num="${Math.round(l.qty)}" data-imp="${Math.round(l.imp)}"><span>${esc(l.label)}</span><span><b>${esc(fmtInt(l.rounded))}</b> <span class="u">${esc(t('rc.unit'))}</span></span></div>`;
  }

  function postHTML(item, kind) {
    if (!item) return '';
    const snip = item.snippet && !XA._rcHideSnippetWait ? '' : '';
    return `<p class="rc-post" id="rc-${kind}" data-date="${esc(item.date)}" data-raw="${item.raw}" data-qty="${item.rounded}">${esc(t(kind === 'exp' ? 'rc.exp' : 'rc.cheap', { day: item.date, n: fmtInt(item.rounded) }))}</p>`;
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
    const basis = esc(t(model.mode === 'overview' ? 'rc.basisDays' : 'rc.basisPosts', { n: fmtInt(model.n) }));
    const flag = XA._isSample ? `<p class="rc-flag">${esc(t('rc.sample'))}</p>` : '';
    const gradeName = esc(t(GRADE_NAME[model.grade]));
    const gradeLine = esc(t(GRADE_LINE[model.grade]));
    const headline = model.headlineKind === 'miss'
      ? esc(t('rc.headlineMiss'))
      : (model.headline == null ? esc(t('rc.headlineSold')) : esc(t('rc.headline', { n: fmtInt(model.headline) })));
    const lines = model.lines.map(lineHTML).join('');
    const hideSnip = model.hideSnippet;
    const exp = model.expensive ? `<p class="rc-post" id="rc-exp" data-date="${esc(model.expensive.date)}" data-raw="${model.expensive.raw}" data-qty="${model.expensive.rounded}">${esc(t('rc.exp', { day: model.expensive.date, n: fmtInt(model.expensive.rounded) }))}${(!hideSnip && model.expensive.snippet) ? ' ' + esc(model.expensive.snippet) : ''}</p>` : '';
    const cheap = model.cheap ? `<p class="rc-post" id="rc-cheap" data-date="${esc(model.cheap.date)}" data-raw="${model.cheap.raw}" data-qty="${model.cheap.rounded}">${esc(t('rc.cheap', { day: model.cheap.date, n: fmtInt(model.cheap.rounded) }))}${(!hideSnip && model.cheap.snippet) ? ' ' + esc(model.cheap.snippet) : ''}</p>` : '';
    const refund = model.refund ? `<div class="rc-line" id="rc-refund" data-key="unf" data-qty="${Math.round(model.refund.qty)}"><span>${esc(t('rc.refund'))}</span><b>${esc(fmtInt(model.refund.qty))}</b></div>` : '';
    const coupon = model.coupon ? `<p class="rc-coupon" id="rc-coupon" data-hour="${model.coupon.hour}" data-pct="${model.coupon.pct}">${esc(t('rc.coupon', { h: String(model.coupon.hour), n: String(model.coupon.pct) }))}</p>` : '';
    const sum = model.nfQty == null ? '' : `<div class="rc-line rc-sum" id="rc-sum" data-nf="${Math.round(model.nfQty)}" data-imp="${Math.round(model.imp)}"><span>${esc(t('rc.sum', { nf: fmtInt(model.nfQty), imp: fmtInt(model.imp) }))}</span></div>`;
    const miss = model.missingLabels.length ? `<p class="rc-miss" id="rc-miss">${esc(t('rc.missing', { cols: model.missingLabels.join(', ') }))}</p>` : '';
    return `<div class="rc-paper" id="rc-paper" data-grade="${esc(model.grade)}">
      ${flag}
      <div class="rc-star">${star}</div>
      <p class="rc-kicker">${esc(t('rc.guest'))}</p>
      <h2 class="rc-grade" id="rc-grade">${gradeName}</h2>
      <p class="rc-grade-line">${gradeLine}</p>
      <p class="rc-headline" id="rc-headline" data-kind="${esc(model.headlineKind)}"${model.headline == null ? '' : ` data-price="${model.headline}"`}>${headline}</p>
      <p class="rc-sub" id="rc-handle">${handleLine}</p>
      <p class="rc-sub" id="rc-period"${periodAttrs}>${periodLine}</p>
      <p class="rc-sub">${basis}</p>
      <hr class="rc-rule">
      ${lines}
      ${exp}${cheap}${refund}${coupon}
      <hr class="rc-rule">
      ${sum}
      ${miss}
      ${barcodeHTML(model.imp)}
      <p class="rc-thanks">${esc(t('rc.thanks'))}</p>
      <p class="rc-site">${esc(t('brand.name'))} · tuki0609.github.io/account-compass</p>
    </div>`;
  }

  function fontPx(g) {
    const m = String(g.font).match(/(\d+(?:\.\d+)?)px/);
    return m ? Number(m[1]) : 16;
  }
  function measureInk(g, text) {
    const raw = String(text || '');
    const probe = raw.trim() ? raw : 'Ag가';
    const m = g.measureText(probe);
    const size = fontPx(g);
    let ascent = m.fontBoundingBoxAscent;
    let descent = m.fontBoundingBoxDescent;
    if (!(ascent > 0) || !(descent >= 0)) {
      ascent = m.actualBoundingBoxAscent || 0;
      descent = m.actualBoundingBoxDescent || 0;
    }
    if (!(ascent + descent >= size * 0.9)) {
      ascent = size * 0.8;
      descent = size * 0.25;
    }
    return { ascent: ascent, descent: descent, h: ascent + descent, w: g.measureText(raw).width };
  }
  function pushInk(layout, id, x, y, w, h) {
    if (!layout || !(w > 0) || !(h > 0)) return;
    layout.push({ id: id, x: x, y: y, w: w, h: h });
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

  function drawBarcode(g, x, y, w, h, seed) {
    const bits = barBits(seed);
    const sum = bits.reduce((a, b) => a + b, 0) || 1;
    const unit = w / sum;
    let cx = x;
    g.fillStyle = '#1c1917';
    bits.forEach((bw, i) => {
      const span = unit * bw;
      if (i % 2 === 0) g.fillRect(cx, y, Math.max(2, span - 2), h);
      cx += span;
    });
  }

  function paintReceipt(g, model, W, H, layout) {
    g.fillStyle = '#efe7d6';
    g.fillRect(0, 0, W, H);
    g.fillStyle = '#f7f3ea';
    g.fillRect(48, 24, W - 96, Math.max(0, H - 48));
    g.textBaseline = 'alphabetic';
    g.textAlign = 'center';
    g.fillStyle = '#1c1917';
    let top = 48;

    function space(n) { top += n; }
    function inkGap(size) { space(Math.max(18, Math.round(size * 0.12))); }
    function drawCentered(id, text, font, maxW, color, limit) {
      g.font = font;
      g.fillStyle = color || '#1c1917';
      g.textAlign = 'center';
      const lines = wrapText(g, text, maxW).slice(0, limit || 4);
      const size = fontPx(g);
      lines.forEach((ln, i) => {
        if (i) space(4);
        const box = measureInk(g, ln);
        g.fillText(ln, W / 2, top + box.ascent);
        pushInk(layout, id + '-' + i, W / 2 - box.w / 2, top, box.w, box.h);
        top += box.h;
      });
      return size;
    }
    function drawLeftBlock(id, text, font, maxW) {
      g.font = font;
      g.fillStyle = '#1c1917';
      g.textAlign = 'left';
      const lines = wrapText(g, text, maxW);
      lines.forEach((ln, i) => {
        if (i) space(4);
        const box = measureInk(g, ln);
        g.fillText(ln, 110, top + box.ascent);
        pushInk(layout, id + '-' + i, 110, top, box.w, box.h);
        top += box.h;
      });
    }
    function drawPair(id, label, value) {
      let size = 30;
      let lb;
      let vb;
      while (size >= 18) {
        g.font = '600 ' + size + 'px ' + FONT;
        lb = measureInk(g, label);
        vb = measureInk(g, value);
        if (lb.w + vb.w + 28 <= W - 220) break;
        size -= 2;
      }
      g.font = '600 ' + size + 'px ' + FONT;
      g.fillStyle = '#1c1917';
      g.textAlign = 'left';
      g.fillText(label, 110, top + lb.ascent);
      pushInk(layout, id + '-l', 110, top, lb.w, lb.h);
      g.textAlign = 'right';
      g.fillText(value, W - 110, top + vb.ascent);
      pushInk(layout, id + '-r', W - 110 - vb.w, top, vb.w, vb.h);
      top += Math.max(lb.h, vb.h);
    }

    let size = drawCentered('star', t('rc.star'), '800 32px ' + FONT, W - 180, '#1c1917', 2);
    inkGap(size);
    size = drawCentered('guest', t('rc.guest'), '700 24px ' + FONT, W - 180, '#57534e', 2);
    inkGap(size);
    const grade = t(GRADE_NAME[model.grade]);
    let gsize = 92;
    while (gsize > 68) {
      g.font = '900 ' + gsize + 'px ' + FONT;
      if (g.measureText(grade).width <= W - 180) break;
      gsize -= 4;
    }
    size = drawCentered('grade', grade, '900 ' + gsize + 'px ' + FONT, W - 180, '#1c1917', 3);
    inkGap(size);
    g.font = '800 32px ' + FONT;
    const teaseLines = wrapText(g, t(GRADE_LINE[model.grade]), W - 280).slice(0, 3);
    const teaseMetrics = teaseLines.map((ln) => measureInk(g, ln));
    let teaseInner = 0;
    teaseMetrics.forEach((m, i) => { teaseInner += m.h; if (i) teaseInner += 6; });
    const teasePad = 16;
    const boxH = teaseInner + teasePad * 2;
    g.fillStyle = '#ffffff';
    roundRect(g, 100, top, W - 200, boxH, 18);
    g.fill();
    let ty = top + teasePad;
    g.font = '800 32px ' + FONT;
    g.fillStyle = '#1c1917';
    g.textAlign = 'center';
    teaseLines.forEach((ln, i) => {
      if (i) ty += 6;
      const box = teaseMetrics[i];
      g.fillText(ln, W / 2, ty + box.ascent);
      pushInk(layout, 'tease-' + i, W / 2 - box.w / 2, ty, box.w, box.h);
      ty += box.h;
    });
    top += boxH;
    inkGap(32);
    const head = model.headlineKind === 'miss' ? t('rc.headlineMiss') : (model.headline == null ? t('rc.headlineSold') : t('rc.headline', { n: fmtInt(model.headline) }));
    size = drawCentered('head', head, '800 34px ' + FONT, W - 180, '#1c1917', 3);
    inkGap(size);
    const handleLine = !model.handle ? t('rc.noHandle') : (model.hideHandle ? t('rc.handleHidden') : '@' + model.handle);
    size = drawCentered('handle', handleLine, '600 26px ' + FONT, W - 180, '#1c1917', 2);
    inkGap(size);
    size = drawCentered('period', model.period ? (model.period.from === model.period.to ? model.period.from : t('rc.period', model.period)) : t('rc.noDate'), '600 26px ' + FONT, W - 180, '#1c1917', 2);
    inkGap(size);
    size = drawCentered('basis', t(model.mode === 'overview' ? 'rc.basisDays' : 'rc.basisPosts', { n: fmtInt(model.n) }), '600 24px ' + FONT, W - 180, '#1c1917', 2);
    inkGap(size);
    g.strokeStyle = '#44403c';
    g.lineWidth = 2;
    g.setLineDash([8, 8]);
    g.beginPath(); g.moveTo(110, top); g.lineTo(W - 110, top); g.stroke();
    g.setLineDash([]);
    space(16);
    (model.lines || []).forEach((l) => {
      drawPair(l.key, l.label, l.sold ? t('rc.sold') : (fmtInt(l.rounded) + '  ' + t('rc.unit')));
      space(14);
    });
    if (model.expensive) drawLeftBlock('exp', t('rc.exp', { day: model.expensive.date, n: fmtInt(model.expensive.rounded) }), '500 26px ' + FONT, W - 220);
    if (model.cheap) { space(12); drawLeftBlock('cheap', t('rc.cheap', { day: model.cheap.date, n: fmtInt(model.cheap.rounded) }), '500 26px ' + FONT, W - 220); }
    if (!model.hideSnippet && model.expensive && model.expensive.snippet) { space(12); drawLeftBlock('snip', model.expensive.snippet, '500 24px ' + FONT, W - 220); }
    if (model.refund) { space(12); drawPair('refund', t('rc.refund'), fmtInt(model.refund.qty)); }
    if (model.coupon) { space(12); drawLeftBlock('coupon', t('rc.coupon', { h: String(model.coupon.hour), n: String(model.coupon.pct) }), '500 26px ' + FONT, W - 220); }
    space(16);
    g.setLineDash([8, 8]);
    g.beginPath(); g.moveTo(110, top); g.lineTo(W - 110, top); g.stroke();
    g.setLineDash([]);
    space(18);
    if (model.nfQty != null) {
      drawLeftBlock('sum', t('rc.sum', { nf: fmtInt(model.nfQty), imp: fmtInt(model.imp) }), '800 30px ' + FONT, W - 220);
      space(16);
    }
    if (model.missingLabels && model.missingLabels.length) {
      drawLeftBlock('miss', t('rc.missing', { cols: model.missingLabels.join(', ') }), '400 24px ' + FONT, W - 220);
      space(16);
    }
    const barH = 70;
    const barGap = 22;
    space(barGap);
    drawBarcode(g, 120, top, W - 240, barH, model.imp);
    pushInk(layout, 'barcode', 120, top, W - 240, barH);
    top += barH;
    space(barGap);
    drawCentered('thanks', t('rc.thanks'), '900 36px ' + FONT, W - 160, '#1c1917', 2);
    inkGap(36);
    drawCentered('brand', t('brand.name') + '  ·  tuki0609.github.io/account-compass', '700 24px ' + FONT, W - 160, '#1c1917', 2);
    return top + 8;
  }

  XA.receiptDraw = function (model) {
    const W = 1080;
    const scratch = document.createElement('canvas');
    scratch.width = W;
    scratch.height = 3200;
    const bottom = paintReceipt(scratch.getContext('2d'), model, W, 3200, null);
    const H = Math.max(720, Math.ceil(bottom + 56));
    const c = document.createElement('canvas');
    c.width = W;
    c.height = H;
    c._layout = [];
    paintReceipt(c.getContext('2d'), model, W, H, c._layout);
    return c;
  };

  function prefs() {
    return {
      hideSnippet: XA._rcHideSnippet !== false,
      hideHandle: !!XA._rcHideHandle,
    };
  }
  function say(note, key) {
    if (!note) return;
    note.hidden = false;
    note.textContent = t(key);
  }
  function render(el, A) {
    const mod = XA.moduleById('receipt');
    const st = XA.cardStatus(mod, A);
    if (!A || st.state !== 'ready') {
      el.innerHTML = `<div class="card rc-wrap"><h2>${esc(t('hub.card.receipt.t'))}</h2><p>${esc(t(st.key, st.params))}</p></div>`;
      return;
    }
    const model = XA.receiptModel(A, prefs());
    if (!model || model.blocked) {
      el.innerHTML = `<div class="card rc-wrap"><h2>${esc(t('hub.card.receipt.t'))}</h2><p>${esc(t((model && model.key) || 'rc.why.empty'))}</p></div>`;
      return;
    }
    el.innerHTML = `<div class="rc-wrap">
      ${paperHTML(model)}
      <div class="rc-tools">
        <label><input type="checkbox" id="rc-hide-line" ${model.hideSnippet ? 'checked' : ''}> ${esc(t('rc.hideLine'))}</label>
        <label><input type="checkbox" id="rc-hide-handle" ${model.hideHandle ? 'checked' : ''}> ${esc(t('rc.hideHandle'))}</label>
      </div>
      <p class="rc-honest">${esc(t('rc.honest'))}</p>
      <div class="share-row">
        <button type="button" class="btn" id="rc-save">${esc(t('share.save'))}</button>
        <button type="button" class="btn ghost" id="rc-copy">${esc(t('share.copy'))}</button>
        <button type="button" class="btn ghost" id="rc-x">${esc(t('share.x'))}</button>
      </div>
      <p class="share-note" id="rc-share-note" hidden></p>
      <p class="rc-honest">${esc(t('rc.saveNote'))}</p>
    </div>`;
    const redraw = () => {
      XA._rcHideSnippet = document.getElementById('rc-hide-line').checked;
      XA._rcHideHandle = document.getElementById('rc-hide-handle').checked;
      render(el, A);
    };
    document.getElementById('rc-hide-line').addEventListener('change', redraw);
    document.getElementById('rc-hide-handle').addEventListener('change', redraw);
    const live = () => XA.receiptModel(A, prefs());
    document.getElementById('rc-save').addEventListener('click', () => XA.downloadCanvas(XA.receiptDraw(live()), 'x-receipt.png'));
    document.getElementById('rc-copy').addEventListener('click', () => {
      const note = document.getElementById('rc-share-note');
      XA.copyCanvas(XA.receiptDraw(live()), 'x-receipt.png').then((r) => say(note, r.how === 'clipboard' ? 'share.copied' : 'share.copyFallback'));
    });
    document.getElementById('rc-x').addEventListener('click', () => {
      const note = document.getElementById('rc-share-note');
      const m = live();
      XA.shareToX(XA.receiptDraw(m), XA.priceCaption(m, XA.lang || 'ko'), 'x-receipt.png').then((r) => {
        if (r.how === 'intent') say(note, 'share.paste');
        else if (r.how === 'share') say(note, 'share.shared');
      });
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
      order: 4,
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
