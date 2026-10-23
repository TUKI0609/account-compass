/* 일별 개요(Overview) CSV 분석 — 하루 단위 합계 파일. 브라우저 안에서만 실행. 문구는 i18n.js */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const t = (k, p) => XA.t(k, p);
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n) => (n == null || !isFinite(n) ? '-' : Math.round(n).toLocaleString(XA.locale()));
  const f1 = (n) => (n == null || !isFinite(n) ? '-' : (Math.round(n * 10) / 10).toLocaleString(XA.locale(), { maximumFractionDigits: 1 }));
  const pct = (x, d = 2) => (x == null || !isFinite(x) ? '-' : (x * 100).toFixed(d) + '%');
  const sum = (a) => a.reduce((x, y) => x + y, 0);
  const avg = (a) => (a.length ? sum(a) / a.length : NaN);
  const median = (a) => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0];
  const MON = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
  const day = (d) => t('day.' + d);

  // 날짜 칸은 "달력 날짜"로만 취급 (시간대 변환 없음) → 요일도 그 날짜 기준
  function parseDay(s) {
    s = String(s || '').trim(); let m;
    if ((m = s.match(/([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})/))) { const mo = MON[m[1].toLowerCase()]; if (mo) return Date.UTC(+m[3], mo - 1, +m[2]); }
    if ((m = s.match(/(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?,?\s+(\d{4})/))) { const mo = MON[m[2].toLowerCase()]; if (mo) return Date.UTC(+m[3], mo - 1, +m[1]); }
    if ((m = s.match(/(\d{4})\s*[-./년年]\s*(\d{1,2})\s*[-./월月]\s*(\d{1,2})/))) return Date.UTC(+m[1], +m[2] - 1, +m[3]);
    if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/))) return Date.UTC(+m[3], +m[1] - 1, +m[2]);
    return null;
  }
  const md = (k) => { const d = new Date(k); return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`; };
  const ymd = (k) => { const d = new Date(k); return `${d.getUTCFullYear()}.${String(d.getUTCMonth() + 1).padStart(2, '0')}.${String(d.getUTCDate()).padStart(2, '0')}`; };
  const dayLabel = (k) => `${md(k)}(${day(new Date(k).getUTCDay())})`;
  XA.parseDay = parseDay;

  function analyzeOverview(rows, headers, map, num) {
    const g = (r, k) => (map[k] != null ? num(r[map[k]]) : 0);
    const days = rows.slice(1).map((r) => {
      const key = parseDay(r[map.date]); if (key == null) return null;
      const d = { key, dow: new Date(key).getUTCDay(), imp: g(r, 'imp'), likes: g(r, 'likes'), eng: g(r, 'eng'), bm: g(r, 'bm'), shares: g(r, 'shares'), nf: g(r, 'nf'), unf: g(r, 'unf'),
        rep: g(r, 'rep'), rt: g(r, 'rt'), prof: g(r, 'prof'), posts: g(r, 'posts'), vid: g(r, 'vid'), media: g(r, 'media') };
      d.net = d.nf - d.unf; return d;
    }).filter(Boolean).sort((a, b) => a.key - b.key);
    if (!days.length) throw XA.err('err.ovDate', { cols: headers.join(', ') });
    if (map.imp == null) throw XA.err('err.noImp', { cols: headers.join(', ') });
    const hasPosts = map.posts != null;
    // 활동 시작 전(준비 기간) 제거: 첫 게시일부터. 게시물 칸이 없으면 노출이 평소의 5% 미만인 앞쪽 날 제외
    let start = 0;
    if (hasPosts && days.some((d) => d.posts > 0)) start = days.findIndex((d) => d.posts > 0);
    else { const th = 0.05 * median(days.filter((d) => d.imp > 0).map((d) => d.imp)); start = Math.max(0, days.findIndex((d) => d.imp >= th)); }
    const pre = days.slice(0, start), act = days.slice(start);
    // 오늘(KST) 이후 날짜는 집계 중
    const now = new Date(Date.now() + 9 * 3600e3); const todayKey = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    act.forEach((d) => (d.partial = d.key >= todayKey));
    const unmapped = headers.filter((h, i) => h && !Object.values(map).includes(i));
    return { mode: 'overview', headers, map, unmapped, days, pre, act, hasPosts, hasBm: map.bm != null, hasUnf: map.unf != null };
  }
  XA.analyzeOverview = analyzeOverview;

  function totals(list) {
    const o = {}; ['imp', 'likes', 'eng', 'bm', 'shares', 'nf', 'unf', 'net', 'rep', 'rt', 'prof', 'posts', 'vid', 'media'].forEach((k) => (o[k] = sum(list.map((d) => d[k])))); o.n = list.length; return o;
  }

  function dailyChart(days, preN) {
    const W = 920, H = 300, L = 54, R = 46, T = 24, B = 40, iw = W - L - R, ih = H - T - B; const n = days.length; const bw = iw / n;
    const mxI = Math.max(...days.map((d) => d.imp), 1); const nets = days.map((d) => d.net); const mxN = Math.max(...nets, 1), mnN = Math.min(...nets, 0);
    const yI = (v) => T + ih - (v / mxI) * ih; const yN = (v) => T + ih - ((v - mnN) / (mxN - mnN || 1)) * ih;
    const big = (v) => (XA.lang === 'ko' && v >= 1e4 ? f1(v / 1e4) + '만' : v >= 1e3 && XA.lang !== 'ko' ? f1(v / 1e3) + 'k' : fmt(v));
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(t('ov.chartAria'))}">`;
    for (let i = 0; i <= 4; i++) { const v = (mxI * i) / 4, y = yI(v); s += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" stroke="#eef1f5"/><text x="${L - 6}" y="${y + 4}" font-size="11" text-anchor="end" fill="#657786">${big(v)}</text>`; }
    [mnN, 0, mxN].filter((v, i, a) => a.indexOf(v) === i).forEach((v) => (s += `<text x="${W - R + 6}" y="${yN(v) + 4}" font-size="11" fill="#f97316">${fmt(v)}</text>`));
    if (mnN < 0) s += `<line x1="${L}" x2="${W - R}" y1="${yN(0)}" y2="${yN(0)}" stroke="#fdba74" stroke-dasharray="3 3"/>`;
    const step = Math.ceil(n / 12);
    days.forEach((d, i) => {
      const x = L + i * bw, y = yI(d.imp); const c = i < preN ? '#cbd5e1' : d.partial ? '#a5b4fc' : '#4f46e5';
      s += `<rect x="${(x + bw * 0.15).toFixed(1)}" y="${y.toFixed(1)}" width="${(bw * 0.7).toFixed(1)}" height="${(T + ih - y).toFixed(1)}" rx="2" fill="${c}"><title>${esc(t('ov.barTip', { d: ymd(d.key), dow: day(d.dow), imp: fmt(d.imp), net: fmt(d.net), bm: fmt(d.bm), posts: fmt(d.posts) }))}${d.partial ? ' · ' + esc(t('ov.partial')) : ''}</title></rect>`;
      if (i % step === 0 || i === n - 1) s += `<text x="${(x + bw / 2).toFixed(1)}" y="${H - B + 16}" font-size="11" text-anchor="middle" fill="#657786">${md(d.key)}</text>`;
    });
    s += `<polyline fill="none" stroke="#f97316" stroke-width="2.2" points="${days.map((d, i) => `${(L + i * bw + bw / 2).toFixed(1)},${yN(d.net).toFixed(1)}`).join(' ')}"/>`;
    days.forEach((d, i) => (s += `<circle cx="${(L + i * bw + bw / 2).toFixed(1)}" cy="${yN(d.net).toFixed(1)}" r="2.6" fill="#f97316"/>`));
    s += `<text x="${L}" y="14" font-size="12" fill="#4f46e5" font-weight="700">${esc(t('ov.legImp'))}</text><text x="${L + 150}" y="14" font-size="12" fill="#f97316" font-weight="700">${esc(t('ov.legNet'))}</text>`;
    if (preN) s += `<text x="${L + 520}" y="14" font-size="12" fill="#94a3b8" font-weight="700">${esc(t('ov.legPre'))}</text>`;
    return s + '</svg>';
  }

  function renderOverview(A, isSample, keepScroll) {
    XA._isSample = isSample;
    const box = $('#overview'); box.hidden = false;
    const act = A.act, full = act.filter((d) => !d.partial), T = totals(act);
    const withPosts = A.hasPosts ? act.filter((d) => d.posts > 0) : act; const TP = totals(withPosts);
    const er = TP.imp ? TP.eng / TP.imp : NaN, br = TP.imp ? TP.bm / TP.imp : NaN;
    const first = act[0], last = act[act.length - 1];
    const partialDays = act.filter((d) => d.partial);
    const sign = (v) => (v >= 0 ? '+' : '') + fmt(v);

    const kpis = [
      [t('ov.k.period'), t('unit.days', { n: act.length }), `${ymd(first.key)} ~ ${ymd(last.key)}`],
      [t('kpi.imp'), fmt(T.imp), t('ov.k.impSub', { a: fmt(T.imp / act.length), m: fmt(median(act.map((d) => d.imp))) })],
      [t('ov.k.eng'), fmt(T.eng), t('ov.k.engSub', { v: pct(er) })],
      [t('ov.k.likes'), fmt(T.likes), t('ov.k.perDay', { v: f1(T.likes / act.length) })],
      [t('ov.k.bm'), A.hasBm ? fmt(T.bm) : '-', t('ov.k.bmSub', { v: pct(br) })],
      [t('ov.k.nf'), fmt(T.nf), A.hasUnf ? t('ov.k.nfSub', { v: fmt(T.unf) }) : ''],
      [t('ov.k.net'), sign(T.net), A.hasUnf ? t('ov.k.netSub') : t('ov.k.noUnf')],
      [t('ov.k.posts'), A.hasPosts ? t('unit.posts', { n: fmt(T.posts) }) : '-', A.hasPosts ? t('ov.k.postsSub', { a: f1(T.posts / act.length), b: fmt(T.imp / (T.posts || 1)) }) : t('ov.k.noCol')],
    ];
    const byDow = DAY_ORDER.map((dw) => { const l = full.filter((d) => d.dow === dw); return { dw, n: l.length, imp: avg(l.map((d) => d.imp)), eng: avg(l.map((d) => d.eng)), bm: avg(l.map((d) => d.bm)), net: avg(l.map((d) => d.net)), posts: avg(l.map((d) => d.posts)) }; });
    const mx = (k) => Math.max(...byDow.filter((x) => x.n).map((x) => x[k]));
    const top = (k) => [...full].sort((a, b) => b[k] - a[k]).slice(0, 3);
    const topCard = (title, k) => `<div class="card"><h3>${title}</h3><ol class="posts">${top(k).map((d) => `<li><b>${dayLabel(d.key)}</b> ${k === 'net' ? sign(d.net) : fmt(d[k])}<div class="meta">${t('ov.topMeta', { imp: fmt(d.imp), bm: fmt(d.bm), net: sign(d.net) })}${A.hasPosts ? ' · ' + t('ov.topPosts', { n: fmt(d.posts) }) : ''}</div></li>`).join('')}</ol></div>`;
    const B = [['0', (p) => p === 0], ['1to3', (p) => p >= 1 && p <= 3], ['4plus', (p) => p >= 4]].map(([id, fn]) => { const l = full.filter((d) => fn(d.posts)); const o = totals(l); return { label: t('ov.bucket.' + id), n: l.length, imp: avg(l.map((d) => d.imp)), medImp: median(l.map((d) => d.imp)), ipp: o.posts ? o.imp / o.posts : NaN, net: avg(l.map((d) => d.net)), medNet: median(l.map((d) => d.net)), bm: avg(l.map((d) => d.bm)), er: o.imp ? o.eng / o.imp : NaN }; });

    const obs = observations(A, act, full, T, er, br, B, byDow);
    const notes = [];
    if (A.pre.length) notes.push(t('ov.note.pre', { n: A.pre.length, a: ymd(A.pre[0].key), b: ymd(A.pre[A.pre.length - 1].key), imp: fmt(sum(A.pre.map((d) => d.imp))) }));
    if (partialDays.length) notes.push(t('ov.note.partial', { d: partialDays.map((d) => ymd(d.key)).join(', ') }));
    if (A.hasPosts) notes.push(t('ov.note.posted'));
    const th = (keys) => keys.map((k) => `<th>${t('ov.th.' + k)}</th>`).join('');
    box.innerHTML = `
      ${isSample ? `<div class="banner">${t('ov.sampleBanner')}</div>` : ''}
      <div class="banner info">${t('ov.detected')}</div>
      <div class="muted small" id="ov-col-info">${XA.colInfo(A.map, A.unmapped, ['imp', 'eng', 'nf'])}${notes.length ? ' · ' + notes.join(' · ') : ''} <span class="hint">${t('colinfo.hint')}</span></div>
      <h2>${t('ov.h.summary')}</h2>
      <div class="kpis">${kpis.map(([k, v, s]) => `<div class="kpi"><div class="k">${esc(k)}</div><div class="v">${esc(v)}</div><div class="s">${esc(s)}</div></div>`).join('')}</div>
      <h2>${t('ov.h.obs')}</h2>
      <div class="cards2">${obs.map((o) => `<div class="card sug"><div class="t">${o.t}</div><p>${o.p}</p></div>`).join('')}</div>
      <h2>${t('ov.h.daily')}</h2>
      <div class="chart">${dailyChart(A.days, A.pre.length)}<div class="legend">${t('ov.chartHint')}${partialDays.length ? ' ' + t('ov.chartPartial') : ''}</div></div>
      <h2>${t('ov.h.dow')}</h2>
      <p class="muted small">${t('ov.dowNote')}</p>
      <div class="tbl-wrap"><table class="tbl"><thead><tr>${th(['dow', 'days', 'imp', 'eng', 'bm', 'net'])}${A.hasPosts ? th(['posts']) : ''}</tr></thead><tbody>${byDow.map((x) => `<tr><td>${day(x.dw)}</td><td>${x.n}</td><td class="${x.n && x.imp === mx('imp') ? 'hi' : ''}">${x.n ? fmt(x.imp) : '-'}</td><td class="${x.n && x.eng === mx('eng') ? 'hi' : ''}">${x.n ? fmt(x.eng) : '-'}</td><td class="${x.n && x.bm === mx('bm') ? 'hi' : ''}">${x.n ? f1(x.bm) : '-'}</td><td class="${x.n && x.net === mx('net') ? 'hi' : ''}">${x.n ? f1(x.net) : '-'}</td>${A.hasPosts ? `<td>${x.n ? f1(x.posts) : '-'}</td>` : ''}</tr>`).join('')}</tbody></table></div>
      <h2>${t('ov.h.top')}</h2>
      <div class="cards3">${topCard(t('ov.top.bm'), 'bm')}${topCard(t('ov.top.net'), 'net')}${topCard(t('ov.top.imp'), 'imp')}</div>
      ${A.hasPosts ? `<h2>${t('ov.h.bucket')}</h2>
      <p class="muted small">${t('ov.bucketNote')}</p>
      <div class="tbl-wrap"><table class="tbl"><thead><tr>${th(['bucket', 'days', 'imp', 'medImp', 'ipp', 'net', 'medNet', 'bm', 'er'])}</tr></thead><tbody>${B.map((b) => `<tr><td>${b.label}</td><td>${b.n}</td><td>${b.n ? fmt(b.imp) : '-'}</td><td>${b.n ? fmt(b.medImp) : '-'}</td><td>${b.n && isFinite(b.ipp) ? fmt(b.ipp) : '-'}</td><td>${b.n ? f1(b.net) : '-'}</td><td>${b.n ? f1(b.medNet) : '-'}</td><td>${b.n ? f1(b.bm) : '-'}</td><td>${b.n ? pct(b.er) : '-'}</td></tr>`).join('')}</tbody></table></div>` : ''}
      <div class="card prose" style="margin-top:22px"><h3>${t('ov.toContent.h')}</h3>
        <ol><li>${t('ov.toContent.1')}</li><li>${t('ov.toContent.2')}</li><li>${t('ov.toContent.3')}</li></ol>
        <p class="small muted">${t('ov.toContent.p')}</p></div>
      <p class="muted small foot-note">${t('results.footnote')}</p>`;
    if (!keepScroll) box.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  XA.renderOverview = renderOverview;

  /* 관찰: 모두 업로드한 사람 자신의 기간 평균과 비교 */
  function observations(A, act, full, T, er, br, B, byDow) {
    const o = [];
    if (full.length >= 5) {
      const byImp = [...full].sort((a, b) => b.imp - a.imp); const top = byImp.slice(0, 3), rest = byImp.slice(3);
      const fpk = (l) => { const x = totals(l); return x.imp ? (x.net / x.imp) * 1e4 : NaN; };
      const a = fpk(top), b = fpk(rest); const topNet = [...full].sort((x, y) => y.net - x.net)[0];
      const share = sum(top.map((d) => d.imp)) / (sum(full.map((d) => d.imp)) || 1);
      if (isFinite(a) && isFinite(b) && b > a * 1.5) o.push({ t: t('ov.o.reach.t'), p: t('ov.o.reach.p', { days: top.map((d) => md(d.key)).join(', '), share: pct(share, 0), a: f1(a), b: f1(b), best: dayLabel(topNet.key), net: fmt(topNet.net), imp: fmt(topNet.imp) }) });
      else if (share >= 0.4) o.push({ t: t('ov.o.spiky.t'), p: t('ov.o.spiky.p', { share: pct(share, 0) }) });
    }
    if (A.hasBm && full.length) {
      const d = [...full].sort((a, b) => b.bm - a.bm)[0]; const r = d.imp ? d.bm / d.imp : 0;
      if (d.bm > 0) o.push({ t: t('ov.o.bm.t', { d: dayLabel(d.key) }), p: t('ov.o.bm.p', { bm: fmt(d.bm), r: pct(r), br: pct(br), x: f1(r / (br || 1e-9)) }) + (d.imp < median(full.map((x) => x.imp)) * 1.2 ? ' ' + t('ov.o.bm.p2', { imp: fmt(d.imp) }) : '') + ' ' + t('ov.o.bm.p3') });
    }
    if (A.hasPosts) {
      const lo = B[1], hi = B[2];
      if (lo.n >= 3 && hi.n >= 3) {
        const ri = hi.imp / lo.imp;
        const P = { hn: hi.n, ln: lo.n, hi: fmt(hi.imp), lo: fmt(lo.imp), x: f1(ri), hipp: fmt(hi.ipp), lipp: fmt(lo.ipp), hnet: f1(hi.net), lnet: f1(lo.net), hmed: f1(hi.medNet), lmed: f1(lo.medNet) };
        o.push(ri >= 1.3 ? { t: t('ov.o.more.t'), p: t('ov.o.more.p', P) } : { t: t('ov.o.less.t'), p: t('ov.o.less.p', P) });
      }
    }
    if (A.hasUnf && T.nf > 0 && T.unf / T.nf >= 0.25) o.push({ t: t('ov.o.unf.t'), p: t('ov.o.unf.p', { nf: fmt(T.nf), unf: fmt(T.unf), r: pct(T.unf / T.nf, 0) }) });
    if (full.length >= 14 && o.length < 4) { const b = byDow.filter((x) => x.n >= 2).sort((a, c) => c.imp - a.imp)[0]; if (b) o.push({ t: t('ov.o.dow.t', { d: t('dayFull.' + b.dw) }), p: t('ov.o.dow.p', { d: t('dayFull.' + b.dw), imp: fmt(b.imp), n: b.n }) }); }
    if (o.length < 3) o.push({ t: t('ov.o.longer.t'), p: t('ov.o.longer.p') });
    return o.slice(0, 3);
  }
})();
