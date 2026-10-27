/* 말투 날씨 예보.
   내 글 본문의 기호·글자 수를 세서 날씨 비유로 보여 준다.
   심리 분석이나 감정 AI가 아니다. 네트워크로 글을 보내지 않는다.
   공유 그림은 canvas로 이 브라우저에서만 만든다. */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const t = (k, p) => XA.t(k, p);
  const esc = (s) => (XA.esc ? XA.esc(s) : String(s ?? ''));

  function chars(s) { return Array.from(String(s || '')).length; }
  function clamp01(x) { return Math.max(0, Math.min(1, x)); }
  function pct(x) { return Math.round((x || 0) * 100); }
  function median(a) {
    if (!a.length) return 0;
    const s = a.slice().sort((x, y) => x - y);
    const m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }
  function share(list, fn) { return list.length ? list.filter(fn).length / list.length : 0; }

  function lastCore(text) {
    const lines = String(text || '').split(/\n/).map((s) => s.trim()).filter(Boolean);
    let s = lines.length ? lines[lines.length - 1] : String(text || '').trim();
    s = s.replace(/https?:\/\/\S+/gi, '')
      .replace(/#[^\s#]+/g, '')
      .replace(/\p{Extended_Pictographic}/gu, '')
      .replace(/[ㅋㅎㅠㅜ]{2,}/g, '')
      .replace(/[wｗ]{2,}/gi, '')
      .replace(/[?？!！.。…~～、,，"'「」『』（）()[\]【】\s]+$/g, '')
      .trim();
    return s;
  }
  function endingKind(core) {
    if (!core) return null;
    if (/(습니다|입니다|합니까|세요|셔요|예요|이에요|에요|네요|데요|군요|지요|죠|나요|까요|니다|요)$/.test(core)) return 'polite';
    if (/(です|ます|でした|ました|ください|でしょうか)$/.test(core)) return 'polite';
    if (/(だよ|だね|じゃん|だろ|てる|んだ|かな|だ)$/.test(core)) return 'casual';
    if (/(다|야|어|아|지|냐|군|네|임|음|함|걸|래|데)$/.test(core)) return 'casual';
    return null;
  }
  function hasQuestion(text) {
    if (/[?？]/.test(text)) return true;
    return /(?:나요|까요|습니까|을까|인가요|일까요|ですか|ますか|かな|까)$/.test(lastCore(text));
  }
  function hasLaugh(text) {
    return /ㅋ{2,}|ㅎ{2,}|[wｗ]{2,}|(?:^|\s)草(?:$|\s|[!！。])|（笑）|\(笑\)|\blol\b|\blmao\b/i.test(text);
  }
  function hasEllipsis(text) { return /\.{3,}|…|⋯|ㅠ{2,}|ㅜ{2,}/.test(text); }
  function hasEmoji(text) { return /\p{Extended_Pictographic}/u.test(text); }
  function hasEx(text) { return /[!！]/.test(text); }
  function hasFP(text) {
    if (/(?:^|[^\p{L}\p{N}])(?:나는|난|내가|나의|저는|제가|저의|저도|우리도|우리는|私|僕|俺|わたし|ぼく|おれ|私たち)(?=$|[^\p{L}\p{N}])/u.test(text)) return true;
    return /\b(I|I'm|I've|I'd|I'll|me|my|mine)\b/i.test(text);
  }
  function hasCta(text) {
    return /저장해|저장\s*해|북마크|팔로우|댓글에|답글에|알려\s*주|save this|bookmark this|follow me|\breply\b|コメント|保存して|フォローして|教えて/i.test(text);
  }
  function hasList(text) { return /(^|\n)\s*(?:\d{1,2}[.)．、]|[①②③④⑤⑥⑦⑧⑨⑩]|[-*・])\s+\S/.test(text); }
  function hasHash(text) { return /#[^\s#]{1,}/.test(text); }
  function hasLink(text) { return /https?:\/\/|t\.co\//i.test(text); }
  function hasNumber(text) { return /\d/.test(text); }

  function feat(text) {
    const kind = endingKind(lastCore(text));
    const laugh = hasLaugh(text);
    const ell = hasEllipsis(text);
    const emoji = hasEmoji(text);
    const ex = hasEx(text);
    const q = hasQuestion(text);
    const cta = hasCta(text);
    return {
      len: chars(text.trim()),
      breaks: (String(text).match(/\n/g) || []).length,
      q: q, ex: ex, emoji: emoji, laugh: laugh, ell: ell,
      fog: laugh || ell,
      express: emoji || ex || laugh || ell,
      fp: hasFP(text),
      cta: cta,
      precip: q || cta,
      list: hasList(text),
      hash: hasHash(text),
      link: hasLink(text),
      num: hasNumber(text),
      vis: hasList(text) || hasNumber(text),
      ending: kind,
    };
  }

  XA.toneStats = function (posts) {
    const all = (posts || []).filter((p) => String(p && p.text || '').trim());
    if (!all.length) return null;
    const orig = all.filter((p) => !p.isReply);
    const use = orig.length >= 3 ? orig : all;
    const rows = use.map((p) => Object.assign({ hour: p.hour, isReply: !!p.isReply }, feat(p.text)));
    const n = rows.length;
    const ends = rows.filter((r) => r.ending);
    const politeN = ends.filter((r) => r.ending === 'polite').length;
    const casualN = ends.filter((r) => r.ending === 'casual').length;
    const politeRate = ends.length >= 3 ? politeN / ends.length : null;
    const lens = rows.map((r) => r.len);
    const day = rows.filter((r) => r.hour != null && r.hour >= 7 && r.hour <= 18);
    const night = rows.filter((r) => r.hour != null && (r.hour < 7 || r.hour > 18));
    const timed = rows.filter((r) => r.hour != null).length;
    let time = { kind: 'none' };
    if (!timed) time = { kind: 'none' };
    else if (day.length < 3 || night.length < 3) time = { kind: 'few', dayN: day.length, nightN: night.length };
    else {
      const dL = share(day, (r) => r.laugh), nL = share(night, (r) => r.laugh);
      const dE = share(day, (r) => r.ex), nE = share(night, (r) => r.ex);
      const useEx = Math.abs(nE - dE) > Math.abs(nL - dL) && (dL + nL === 0);
      const metric = useEx ? 'ex' : 'laugh';
      const dayPct = pct(useEx ? dE : dL);
      const nightPct = pct(useEx ? nE : nL);
      const gap = nightPct - dayPct;
      time = { kind: Math.abs(gap) < 8 ? 'flat' : 'shift', metric: metric, dayN: day.length, nightN: night.length, dayPct: dayPct, nightPct: nightPct, gap: gap };
    }
    return {
      n: n,
      nOrig: orig.length,
      nReply: all.length - orig.length,
      basis: n === 1 ? 'one' : (use === orig ? 'original' : 'all'),
      q: share(rows, (r) => r.q),
      ex: share(rows, (r) => r.ex),
      em: share(rows, (r) => r.emoji),
      laugh: share(rows, (r) => r.laugh),
      ell: share(rows, (r) => r.ell),
      fog: share(rows, (r) => r.fog),
      express: share(rows, (r) => r.express),
      fp: share(rows, (r) => r.fp),
      precipShare: share(rows, (r) => r.precip),
      hash: share(rows, (r) => r.hash),
      link: share(rows, (r) => r.link),
      vis: share(rows, (r) => r.vis),
      breaks: share(rows, (r) => r.breaks > 0),
      avgBreaks: rows.reduce((s, r) => s + r.breaks, 0) / n,
      medLen: median(lens),
      politeRate: politeRate,
      endN: ends.length,
      politeN: politeN,
      casualN: casualN,
      time: time,
    };
  };

  XA.toneWarmth = function (s) {
    if (!s) return 0;
    const politePart = s.politeRate == null ? 0.35 : s.politeRate;
    const raw = 0.16
      + s.em * 0.30
      + s.ex * 0.14
      + s.laugh * 0.18
      + s.fp * 0.16
      + politePart * 0.12
      - Math.min(0.16, Math.max(0, (s.medLen - 180) / 900));
    return clamp01(raw);
  };

  function skyOf(s) {
    if (s.ex >= 0.35 || (s.em >= 0.45 && s.ex >= 0.18)) return 'storm';
    if (s.fog >= 0.45 && s.q < 0.22 && s.ex < 0.25) return 'fog';
    if (s.q >= 0.30) return 'rain';
    if (s.politeRate != null && s.politeRate >= 0.62 && s.ex < 0.22 && s.em < 0.35) return 'snow';
    if (s.medLen >= 160 && s.em < 0.18 && s.ex < 0.18) return 'cloudy';
    return 'clear';
  }
  function tempLabel(c) {
    if (c <= 9) return 'cold';
    if (c <= 16) return 'cool';
    if (c <= 23) return 'mild';
    if (c <= 28) return 'warm';
    return 'hot';
  }
  function windOf(medLen) {
    const kmh = Math.max(3, Math.min(48, Math.round(1400 / Math.max(medLen, 12))));
    const label = kmh >= 28 ? 'strong' : kmh >= 16 ? 'breeze' : kmh >= 8 ? 'light' : 'calm';
    return { kmh: kmh, label: label };
  }

  XA.toneForecast = function (s) {
    if (!s) return null;
    const sky = skyOf(s);
    const warmth = XA.toneWarmth(s);
    const tempC = Math.round(5 + warmth * 29);
    const wind = windOf(s.medLen);
    const humidity = pct(s.express);
    const precip = pct(s.precipShare);
    const humidSky = sky === 'clear' && humidity >= 55;
    const head = humidSky ? 'clearHumid' : sky;
    return {
      sky: sky,
      head: head,
      warmth: warmth,
      tempC: tempC,
      tempLabel: tempLabel(tempC),
      humidity: humidity,
      wind: wind.kmh,
      windLabel: wind.label,
      precip: precip,
      vis: pct(s.vis),
      qPct: pct(s.q),
      exPct: pct(s.ex),
      emPct: pct(s.em),
      laughPct: pct(s.laugh),
      fogPct: pct(s.fog),
      fpPct: pct(s.fp),
      hashPct: pct(s.hash),
      linkPct: pct(s.link),
      brPct: pct(s.breaks),
      avgBreaks: Math.round(s.avgBreaks * 10) / 10,
      medLen: Math.round(s.medLen),
      politePct: s.politeRate == null ? null : pct(s.politeRate),
    };
  };

  function polText(f) {
    return f.politePct == null ? t('wx.polNone') : (f.politePct + '%');
  }
  function nums(s, f) {
    return {
      n: s.n, r: s.nReply, o: s.nOrig,
      ex: f.exPct, em: f.emPct, q: f.qPct, fog: f.fogPct, laugh: f.laughPct, fp: f.fpPct,
      len: f.medLen, temp: f.tempC, h: f.humidity, p: f.precip, v: f.vis,
      pol: polText(f), w: f.warmth.toFixed(2),
      hash: f.hashPct, link: f.linkPct, br: f.brPct, avg: f.avgBreaks,
      wind: f.wind,
    };
  }

  function timeLine(s) {
    const tm = s.time || { kind: 'none' };
    if (tm.kind === 'none') return t('wx.time.none');
    if (tm.kind === 'few') return t('wx.time.few', { d: tm.dayN, n: tm.nightN });
    const metric = t(tm.metric === 'ex' ? 'wx.metric.ex' : 'wx.metric.laugh');
    const key = tm.kind === 'flat' ? 'wx.time.flat' : 'wx.time.shift';
    return t(key, { metric: metric, d: tm.dayN, n: tm.nightN, dp: tm.dayPct, np: tm.nightPct, gap: Math.abs(tm.gap) });
  }

  function basisLine(s) {
    if (s.basis === 'one') return t('wx.basis.one');
    if (s.basis === 'original') return s.nReply ? t('wx.basis.original', { n: s.n, r: s.nReply }) : t('wx.basis.originalOnly', { n: s.n });
    return t('wx.basis.all', { o: s.nOrig, n: s.n });
  }

  XA.toneModel = function (posts) {
    const s = XA.toneStats(posts);
    if (!s) return null;
    const f = XA.toneForecast(s);
    const p = nums(s, f);
    return {
      stats: s,
      forecast: f,
      kicker: t('wx.kicker'),
      headline: t('wx.h.' + f.head, p),
      week: t('wx.week.' + f.head, p),
      basis: basisLine(s),
      time: timeLine(s),
      extra: t('wx.extra', p),
      formula: t('wx.formula'),
      honest: t('wx.honest'),
      share: t('wx.share'),
      shareNote: t('wx.shareNote'),
      sample: t('wx.sampleFlag'),
      cards: [
        { k: t('wx.sky'), v: t('wx.skyName.' + f.sky), real: t('wx.skyReal', p) },
        { k: t('wx.temp'), v: f.tempC + '°C · ' + t('wx.temp.' + f.tempLabel), real: t('wx.tempReal', p) },
        { k: t('wx.humid'), v: f.humidity + '%', real: t('wx.humidReal', p) },
        { k: t('wx.wind'), v: t('wx.wind.' + f.windLabel) + ' · ' + f.wind + 'km/h', real: t('wx.windReal', p) },
        { k: t('wx.precip'), v: f.precip + '%', real: t('wx.precipReal', p) },
        { k: t('wx.vis'), v: f.vis + '%', real: t('wx.visReal', p) },
      ],
    };
  };

  function cardHTML(model, isSample) {
    const cards = model.cards.map((c) => `<article class="wx-m"><div class="wx-m-k">${esc(c.k)}</div><div class="wx-m-v">${esc(c.v)}</div><p class="wx-m-real">${esc(c.real)}</p></article>`).join('');
    const flag = isSample ? `<p class="wx-flag">${esc(model.sample)}</p>` : '';
    return `<div class="wx">
      ${flag}
      <p class="wx-kicker">${esc(model.kicker)}</p>
      <h2 class="wx-headline">${esc(model.headline)}</h2>
      <p class="wx-week">${esc(model.week)}</p>
      <div class="wx-metrics">${cards}</div>
      <p class="wx-note">${esc(model.basis)}</p>
      <p class="wx-note">${esc(model.time)}</p>
      <p class="wx-note">${esc(model.extra)}</p>
      <p class="wx-note">${esc(model.formula)}</p>
      <p class="wx-honest">${esc(model.honest)}</p>
      <div class="row gap wrap-row"><button type="button" class="btn" id="wx-share">${esc(model.share)}</button></div>
      <p class="wx-note">${esc(model.shareNote)}</p>
    </div>`;
  }

  function blockedHTML(mod, st) {
    return `<div class="card wx wx-blocked"><p class="wx-kicker">${esc(t('wx.kicker'))}</p><h2>${esc(t(mod.titleKey))}</h2><p>${esc(t(st.key, st.params))}</p><p class="wx-honest">${esc(t('wx.honest'))}</p></div>`;
  }

  const FONT = '"WenQuanYi Micro Hei","Droid Sans Fallback","Apple SD Gothic Neo","Noto Sans CJK KR",sans-serif';

  function wrapText(g, text, maxW) {
    const out = [];
    const parts = String(text || '').split(/(\s+)/);
    let line = '';
    const pushLong = (token) => {
      let buf = '';
      for (const ch of Array.from(token)) {
        if (g.measureText(buf + ch).width > maxW && buf) { out.push(buf); buf = ch; }
        else buf += ch;
      }
      return buf;
    };
    for (const tk of parts) {
      const trial = line + tk;
      if (g.measureText(trial).width <= maxW) line = trial;
      else {
        if (line.trim()) out.push(line.trimEnd());
        if (g.measureText(tk.trim()).width > maxW) line = pushLong(tk.trim());
        else line = tk.trimStart();
      }
    }
    if (line.trim()) out.push(line.trimEnd());
    return out.length ? out : [''];
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

  function drawSky(g, sky, x, y) {
    g.save();
    g.translate(x, y);
    if (sky === 'clear' || sky === 'cloudy' || sky === 'storm' || sky === 'rain' || sky === 'snow' || sky === 'fog') {
      if (sky === 'clear') {
        g.fillStyle = '#fde68a';
        g.beginPath(); g.arc(0, 0, 28, 0, Math.PI * 2); g.fill();
        g.strokeStyle = '#fde68a'; g.lineWidth = 4;
        for (let i = 0; i < 8; i++) {
          const a = i * Math.PI / 4;
          g.beginPath();
          g.moveTo(Math.cos(a) * 36, Math.sin(a) * 36);
          g.lineTo(Math.cos(a) * 48, Math.sin(a) * 48);
          g.stroke();
        }
      } else {
        g.fillStyle = sky === 'storm' ? '#334155' : '#e2e8f0';
        g.beginPath(); g.ellipse(-16, 6, 26, 18, 0, 0, Math.PI * 2); g.fill();
        g.beginPath(); g.ellipse(14, 2, 32, 22, 0, 0, Math.PI * 2); g.fill();
        g.beginPath(); g.ellipse(0, 16, 36, 16, 0, 0, Math.PI * 2); g.fill();
        if (sky === 'rain' || sky === 'storm') {
          g.strokeStyle = sky === 'storm' ? '#fde68a' : '#93c5fd';
          g.lineWidth = 4;
          [[-18, 28], [0, 34], [18, 28]].forEach(([dx, dy]) => {
            g.beginPath(); g.moveTo(dx, dy); g.lineTo(dx - 8, dy + 18); g.stroke();
          });
        }
        if (sky === 'snow') {
          g.fillStyle = '#fff';
          [[-16, 36], [2, 44], [18, 34]].forEach(([dx, dy]) => { g.beginPath(); g.arc(dx, dy, 4, 0, Math.PI * 2); g.fill(); });
        }
        if (sky === 'fog') {
          g.strokeStyle = 'rgba(255,255,255,.85)'; g.lineWidth = 4;
          [34, 46, 58].forEach((dy) => { g.beginPath(); g.moveTo(-30, dy); g.lineTo(34, dy); g.stroke(); });
        }
      }
    }
    g.restore();
  }

  XA.toneDraw = function (model, opts) {
    opts = opts || {};
    const W = 1080, H = 1350;
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const g = c.getContext('2d');
    const bg = g.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, '#1e1b4b');
    bg.addColorStop(0.55, '#4338ca');
    bg.addColorStop(1, '#818cf8');
    g.fillStyle = bg;
    g.fillRect(0, 0, W, H);
    if (opts.sample) {
      g.fillStyle = '#fde68a';
      roundRect(g, 48, 36, 280, 42, 21); g.fill();
      g.fillStyle = '#78350f';
      g.font = '700 24px ' + FONT;
      g.fillText(model.sample, 72, 65);
    }
    g.fillStyle = 'rgba(255,255,255,.88)';
    g.font = '700 28px ' + FONT;
    g.fillText(model.kicker, 48, opts.sample ? 130 : 100);
    drawSky(g, model.forecast.sky, 980, opts.sample ? 110 : 90);
    g.fillStyle = '#fff';
    g.font = '800 54px ' + FONT;
    const lines = wrapText(g, model.headline, 980);
    let y = opts.sample ? 200 : 170;
    lines.slice(0, 4).forEach((ln) => { g.fillText(ln, 48, y); y += 68; });
    y += 12;
    const shown = model.cards.slice(1, 5);
    const gap = 20, cw = (W - 96 - gap) / 2, ch = 250;
    shown.forEach((card, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 48 + col * (cw + gap);
      const cy = y + row * (ch + gap);
      g.fillStyle = '#fff';
      roundRect(g, x, cy, cw, ch, 24); g.fill();
      g.fillStyle = '#4338ca';
      g.font = '700 28px ' + FONT;
      g.fillText(card.k, x + 28, cy + 52);
      g.fillStyle = '#14171a';
      g.font = '800 48px ' + FONT;
      const vLines = wrapText(g, card.v, cw - 56);
      g.fillText(vLines[0], x + 28, cy + 116);
      g.fillStyle = '#3d4a5c';
      g.font = '400 28px ' + FONT;
      const real = wrapText(g, card.real, cw - 56).slice(0, 3);
      real.forEach((ln, li) => g.fillText(ln, x + 28, cy + 168 + li * 36));
    });
    y += 2 * (ch + gap) + 16;
    g.fillStyle = 'rgba(255,255,255,.16)';
    roundRect(g, 48, y, W - 96, 150, 20); g.fill();
    g.fillStyle = '#fff';
    g.font = '700 32px ' + FONT;
    wrapText(g, model.week, W - 160).slice(0, 3).forEach((ln, i) => g.fillText(ln, 76, y + 52 + i * 40));
    y += 180;
    g.fillStyle = 'rgba(255,255,255,.85)';
    g.font = '400 26px ' + FONT;
    wrapText(g, model.honest, W - 96).slice(0, 2).forEach((ln, i) => g.fillText(ln, 48, y + i * 34));
    g.font = '700 26px ' + FONT;
    g.fillText(t('brand.name') + '  ·  tuki0609.github.io/account-compass', 48, H - 48);
    return c;
  };

  function bindShare(model) {
    const btn = document.getElementById('wx-share');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const canvas = XA.toneDraw(model, { sample: !!XA._isSample });
      const a = document.createElement('a');
      a.href = canvas.toDataURL('image/png');
      a.download = 'tone-weather.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  }

  function render(el, A) {
    const mod = XA.moduleById('weather');
    const st = XA.cardStatus(mod, A);
    if (!A || st.state !== 'ready') {
      el.innerHTML = blockedHTML(mod, st.state === 'ready' ? { key: 'hub.why.emptyText' } : st);
      return;
    }
    const posts = A.posts || [];
    const model = XA.toneModel(posts);
    if (!model) {
      el.innerHTML = blockedHTML(mod, { key: 'hub.why.emptyText' });
      return;
    }
    el.innerHTML = cardHTML(model, !!XA._isSample);
    bindShare(model);
  }

  function weatherReady(A) {
    if (!A) return { state: 'empty', key: 'hub.state.empty' };
    if (A.mode === 'overview') return { state: 'blocked', key: 'hub.why.overview' };
    if (!A.map || A.map.text == null) return { state: 'blocked', key: 'hub.why.noTextCol' };
    const n = (A.posts || []).filter((p) => String(p.text || '').trim()).length;
    if (!n) return { state: 'blocked', key: 'hub.why.emptyText' };
    return { state: 'ready', key: 'hub.state.ready' };
  }

  if (XA.registerModule) {
    XA.registerModule({
      id: 'weather',
      order: 2,
      category: 'fun',
      status: 'ready',
      icon: '⛅',
      titleKey: 'hub.card.weather.t',
      descKey: 'hub.card.weather.d',
      needsKey: 'hub.needs.weather',
      requires: ['text'],
      ready: weatherReady,
      render: render,
    });
  }
  XA.renderWeather = render;
  if (XA.mountHome) XA.mountHome();
})();
