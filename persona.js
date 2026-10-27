/* X 부캐 카드.
   숫자는 올린 CSV에서만 계산한다. 다른 사람과 순위는 만들지 않는다.
   기준값은 XA.PERSONA 한곳에만 있다. 같은 파일이면 같은 결과가 나온다. */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const t = (k, p) => (XA.t ? XA.t(k, p) : k);
  const esc = (s) => (XA.esc ? XA.esc(s) : String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));
  const FONT = '"WenQuanYi Micro Hei","Droid Sans Fallback","Apple SD Gothic Neo","Noto Sans CJK KR",sans-serif';

  const C = {
    MIN_POSTS: 10,
    MIN_IMP: 100,
    SAVE_LO: 0.45, SAVE_HI: 0.9,
    CHAT_LO: 0.6, CHAT_HI: 1.2,
    HIT_LO: 8, HIT_HI: 30,
    ANT_ACTIVE_LO: 0.75, ANT_ACTIVE_HI: 0.95,
    ANT_HIT_MAX: 3.2,
    DAWN_LO: 0.4, DAWN_HI: 0.7,
    MAGNET_LO: 4, MAGNET_HI: 12,
    WINDOW_VISIT_LO: 20, WINDOW_VISIT_HI: 50,
    WINDOW_CONV_MAX: 0.05,
    REPOST_LO: 0.4, REPOST_HI: 1,
    LINK_LO: 0.45, LINK_HI: 0.75,
    SHORT_FULL: 24, SHORT_ZERO: 80,
    LONG_ZERO: 140, LONG_FULL: 280,
    BAR_SAVE: [0, 1],
    BAR_CHAT: [0, 1.5],
    BAR_HIT: [1, 40],
    BAR_STEADY: [0, 1],
    BAR_MAGNET: [0, 10],
    TIE: ['save', 'chat', 'hit', 'ant', 'dawn', 'magnet', 'window', 'repost', 'link', 'short', 'long'],
  };
  XA.PERSONA = C;

  const STAT_KEY = {
    save: 'ps.stat.save', chat: 'ps.stat.chat', hit: 'ps.stat.hit', steady: 'ps.stat.steady', magnet: 'ps.stat.magnet',
  };
  const THEME = {
    save: { emoji: '📚', color: '#7c3aed' },
    chat: { emoji: '💬', color: '#ea580c' },
    hit: { emoji: '🎰', color: '#db2777' },
    ant: { emoji: '🐜', color: '#4d7c0f' },
    dawn: { emoji: '🦉', color: '#1e3a8a' },
    magnet: { emoji: '🧲', color: '#dc2626' },
    window: { emoji: '👀', color: '#0e7490' },
    repost: { emoji: '🔁', color: '#4f46e5' },
    link: { emoji: '🚚', color: '#b45309' },
    short: { emoji: '✂️', color: '#0f766e' },
    long: { emoji: '📜', color: '#7f1d1d' },
    sprout: { emoji: '🌱', color: '#15803d' },
  };
  const NAME_KEY = {
    save: 'ps.name.save', chat: 'ps.name.chat', hit: 'ps.name.hit', ant: 'ps.name.ant',
    dawn: 'ps.name.dawn', magnet: 'ps.name.magnet', window: 'ps.name.window', repost: 'ps.name.repost',
    link: 'ps.name.link', short: 'ps.name.short', long: 'ps.name.long', sprout: 'ps.name.sprout',
  };
  const ROAST_KEY = {
    save: ['ps.roast.save.0', 'ps.roast.save.1', 'ps.roast.save.2', 'ps.roast.save.3'],
    chat: ['ps.roast.chat.0', 'ps.roast.chat.1', 'ps.roast.chat.2', 'ps.roast.chat.3'],
    hit: ['ps.roast.hit.0', 'ps.roast.hit.1', 'ps.roast.hit.2', 'ps.roast.hit.3'],
    ant: ['ps.roast.ant.0', 'ps.roast.ant.1', 'ps.roast.ant.2', 'ps.roast.ant.3'],
    dawn: ['ps.roast.dawn.0', 'ps.roast.dawn.1', 'ps.roast.dawn.2', 'ps.roast.dawn.3'],
    magnet: ['ps.roast.magnet.0', 'ps.roast.magnet.1', 'ps.roast.magnet.2', 'ps.roast.magnet.3'],
    window: ['ps.roast.window.0', 'ps.roast.window.1', 'ps.roast.window.2', 'ps.roast.window.3'],
    repost: ['ps.roast.repost.0', 'ps.roast.repost.1', 'ps.roast.repost.2', 'ps.roast.repost.3'],
    link: ['ps.roast.link.0', 'ps.roast.link.1', 'ps.roast.link.2', 'ps.roast.link.3'],
    short: ['ps.roast.short.0', 'ps.roast.short.1', 'ps.roast.short.2', 'ps.roast.short.3'],
    long: ['ps.roast.long.0', 'ps.roast.long.1', 'ps.roast.long.2', 'ps.roast.long.3'],
    sprout: ['ps.roast.sprout.0', 'ps.roast.sprout.1', 'ps.roast.sprout.2', 'ps.roast.sprout.3'],
  };

  function pad(n) { return String(n).padStart(2, '0'); }
  function fmtInt(n) {
    const v = Math.round(Number(n) || 0);
    try { return v.toLocaleString(XA.locale ? XA.locale() : 'ko-KR'); } catch (e) { return String(v); }
  }
  function finite(v) { return typeof v === 'number' && isFinite(v); }
  function rampUp(v, lo, hi) {
    if (!finite(v) || v <= lo) return 0;
    if (v >= hi) return 100;
    return (v - lo) / (hi - lo) * 100;
  }
  function rampDown(v, full, zero) {
    if (!finite(v) || v >= zero) return 0;
    if (v <= full) return 100;
    return (zero - v) / (zero - full) * 100;
  }
  function toBar(v, pair) {
    if (!finite(v)) return null;
    const lo = pair[0], hi = pair[1];
    const x = hi === lo ? (v >= hi ? 1 : 0) : Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
    return Math.max(1, Math.min(99, Math.round(1 + x * 98)));
  }
  function median(nums) {
    if (!nums.length) return null;
    const a = nums.slice().sort((x, y) => x - y);
    const m = a.length >> 1;
    return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
  }
  function sum(list, key) { return list.reduce((s, r) => s + (Number(r[key]) || 0), 0); }
  function ymd(key) {
    const d = new Date(key);
    return d.getUTCFullYear() + '.' + pad(d.getUTCMonth() + 1) + '.' + pad(d.getUTCDate());
  }
  function dayKeyOf(p) {
    if (p.dateRaw && XA.parseDay) {
      const k = XA.parseDay(p.dateRaw);
      if (k != null) return k;
    }
    if (p.ms != null) {
      const d = new Date(p.ms + 9 * 3600e3);
      return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
    }
    return null;
  }
  function hourFromId(p) {
    if (!p || !XA.timeFromId) return null;
    const ms = XA.timeFromId(String(p.id || ''));
    if (ms == null) return null;
    return new Date(ms + 9 * 3600e3).getUTCHours();
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
  function hashIds(ids) {
    const s = ids.map(String).sort().join('\n');
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }
  XA.personaHash = hashIds;
  function hitShow(raw) {
    if (!finite(raw)) return null;
    const rounded = raw >= 10 ? Math.round(raw) : Math.round(raw * 10) / 10;
    return String(rounded);
  }
  function rawAttr(v) {
    if (!finite(v)) return '';
    return String(Math.round(v * 1e6) / 1e6);
  }

  function namesOf(id) {
    const key = NAME_KEY[id];
    return { ko: (XA.I18N && XA.I18N.ko[key]) || t(key), en: (XA.I18N && XA.I18N.en[key]) || t(key), ja: (XA.I18N && XA.I18N.ja[key]) || t(key) };
  }

  XA.personaModel = function (A, opts) {
    opts = opts || {};
    const hideSnippet = opts.hideSnippet !== false;
    const hideHandle = opts.hideHandle !== false;
    const includeReplies = !!opts.includeReplies;
    if (!A || A.mode === 'overview') return { blocked: true, key: 'ps.why.overview' };
    if (!A.map || A.map.imp == null) return { blocked: true, key: 'ps.why.noImp' };
    const all = A.posts || [];
    if (!all.length) return { blocked: true, key: 'ps.why.empty' };
    const posts = includeReplies ? all.slice() : all.filter((p) => !p.isReply);
    const map = A.map;
    const has = (k) => map[k] != null;
    const impSum = sum(posts, 'imp');
    const likesSum = has('likes') ? sum(posts, 'likes') : null;
    const bmSum = has('bm') ? sum(posts, 'bm') : null;
    const repSum = has('rep') ? sum(posts, 'rep') : null;
    const rtSum = has('rt') ? sum(posts, 'rt') : null;
    const nfSum = has('nf') ? sum(posts, 'nf') : null;
    const profSum = has('prof') ? sum(posts, 'prof') : null;
    const urlSum = has('url') ? sum(posts, 'url') : null;
    const imps = posts.map((p) => Number(p.imp) || 0);
    const maxImp = imps.length ? Math.max.apply(null, imps) : 0;
    const medImp = median(imps);
    const hitRaw = finite(medImp) && medImp > 0 ? maxImp / medImp : null;
    const days = [];
    posts.forEach((p) => { const k = dayKeyOf(p); if (k != null) days.push(k); });
    let active = null;
    if (days.length) {
      const uniq = new Set(days);
      const span = (Math.max.apply(null, days) - Math.min.apply(null, days)) / 864e5 + 1;
      active = span > 0 ? uniq.size / span : null;
    } else if (XA.lastOverview && XA.lastOverview.days && XA.lastOverview.days.length) {
      const od = XA.lastOverview.days.filter((d) => d.key != null);
      if (od.length) {
        const keys = od.map((d) => d.key);
        const span = (Math.max.apply(null, keys) - Math.min.apply(null, keys)) / 864e5 + 1;
        const activeN = od.filter((d) => (Number(d.posts) || 0) > 0).length;
        active = span > 0 ? activeN / span : null;
      }
    }
    const hours = [];
    posts.forEach((p) => { const h = hourFromId(p); if (h != null) hours.push(h); });
    const dawnN = hours.filter((h) => h >= 0 && h <= 5).length;
    const dawnShare = hours.length ? dawnN / hours.length : null;
    const saveRatio = likesSum > 0 && bmSum != null ? bmSum / likesSum : null;
    const chatRatio = likesSum > 0 && repSum != null ? repSum / likesSum : null;
    const repostRatio = likesSum > 0 && rtSum != null ? rtSum / likesSum : null;
    const per1k = nfSum != null && impSum > 0 ? nfSum / impSum * 1000 : null;
    const visitsPer1k = profSum != null && impSum > 0 ? profSum / impSum * 1000 : null;
    const conv = profSum > 0 && nfSum != null ? nfSum / profSum : null;
    let linkShare = null;
    if (has('text') || has('url')) {
      const nLink = posts.filter((p) => (has('text') && /https?:\/\//i.test(p.text || '')) || (has('url') && (Number(p.url) || 0) > 0)).length;
      linkShare = posts.length ? nLink / posts.length : null;
    }
    let medLen = null;
    if (has('text')) {
      const lens = posts.map((p) => Array.from(String(p.text || '').trim()).length).filter((n) => n > 0);
      medLen = median(lens);
    }
    const thin = posts.length < C.MIN_POSTS || impSum < C.MIN_IMP;
    const scores = {
      save: rampUp(saveRatio, C.SAVE_LO, C.SAVE_HI),
      chat: rampUp(chatRatio, C.CHAT_LO, C.CHAT_HI),
      hit: rampUp(hitRaw, C.HIT_LO, C.HIT_HI),
      ant: active != null && (hitRaw == null || hitRaw <= C.ANT_HIT_MAX) ? rampUp(active, C.ANT_ACTIVE_LO, C.ANT_ACTIVE_HI) : 0,
      dawn: rampUp(dawnShare, C.DAWN_LO, C.DAWN_HI),
      magnet: rampUp(per1k, C.MAGNET_LO, C.MAGNET_HI),
      window: conv != null && conv < C.WINDOW_CONV_MAX ? rampUp(visitsPer1k, C.WINDOW_VISIT_LO, C.WINDOW_VISIT_HI) : 0,
      repost: rampUp(repostRatio, C.REPOST_LO, C.REPOST_HI),
      link: rampUp(linkShare, C.LINK_LO, C.LINK_HI),
      short: rampDown(medLen, C.SHORT_FULL, C.SHORT_ZERO),
      long: rampUp(medLen, C.LONG_ZERO, C.LONG_FULL),
    };
    let id = 'sprout';
    let best = 0;
    if (!thin) {
      C.TIE.forEach((k) => {
        if (scores[k] > best) { best = scores[k]; id = k; }
      });
      if (!(best > 0)) id = 'sprout';
    }
    const roastKeys = ROAST_KEY[id];
    const roastIndex = hashIds(posts.map((p) => p.id)) % roastKeys.length;
    const theme = THEME[id];
    const names = namesOf(id);
    let handle = '';
    const counts = new Map();
    posts.forEach((p) => {
      const h = handleFrom(p.link);
      if (!h) return;
      counts.set(h, (counts.get(h) || 0) + 1);
    });
    let bestN = 0;
    counts.forEach((c, h) => { if (c > bestN) { handle = h; bestN = c; } });
    let snippet = '';
    let bestPost = null;
    if (has('text')) {
      posts.forEach((p) => {
        const line = firstLine(p.text);
        if (!line) return;
        const score = Number(p.imp) || 0;
        const idx = p.i == null ? 0 : p.i;
        if (!bestPost || score > bestPost.score || (score === bestPost.score && idx < bestPost.idx)) bestPost = { score: score, idx: idx, line: line };
      });
      if (bestPost) snippet = bestPost.line;
    }
    const period = days.length ? { from: ymd(Math.min.apply(null, days)), to: ymd(Math.max.apply(null, days)) } : null;
    const bars = [
      { id: 'save', raw: saveRatio, bar: toBar(saveRatio, C.BAR_SAVE), num: bmSum, den: likesSum, miss: !has('bm') || !has('likes') },
      { id: 'chat', raw: chatRatio, bar: toBar(chatRatio, C.BAR_CHAT), num: repSum, den: likesSum, miss: !has('rep') || !has('likes') },
      { id: 'hit', raw: hitRaw, bar: toBar(hitRaw, C.BAR_HIT), num: maxImp, den: medImp, miss: false },
      { id: 'steady', raw: active, bar: toBar(active, C.BAR_STEADY), num: days.length ? new Set(days).size : null, den: days.length ? ((Math.max.apply(null, days) - Math.min.apply(null, days)) / 864e5 + 1) : null, miss: active == null },
      { id: 'magnet', raw: per1k, bar: toBar(per1k, C.BAR_MAGNET), num: nfSum, den: impSum, miss: !has('nf') },
    ];
    const missing = ['likes', 'bm', 'rep', 'rt', 'nf', 'prof', 'url', 'text', 'date', 'id'].filter((k) => !has(k));
    return {
      id: id,
      emoji: theme.emoji,
      color: theme.color,
      names: names,
      name: names[XA.lang] || names.ko,
      roastIndex: roastIndex,
      roast: t(roastKeys[roastIndex]),
      play: t('ps.play'),
      hitRaw: hitRaw,
      hitShow: hitShow(hitRaw),
      maxImp: maxImp,
      medImp: medImp,
      scores: scores,
      bars: bars,
      impSum: impSum,
      likesSum: likesSum,
      bmSum: bmSum,
      repSum: repSum,
      rtSum: rtSum,
      nfSum: nfSum,
      profSum: profSum,
      urlSum: urlSum,
      per1k: per1k,
      visitsPer1k: visitsPer1k,
      conv: conv,
      dawnShare: dawnShare,
      dawnN: dawnN,
      timed: hours.length,
      active: active,
      linkShare: linkShare,
      medLen: medLen,
      n: posts.length,
      nAll: all.length,
      nReply: all.filter((p) => p.isReply).length,
      includeReplies: includeReplies,
      thin: thin,
      period: period,
      handle: handle,
      hideHandle: hideHandle,
      hideSnippet: hideSnippet,
      snippet: snippet,
      missing: missing,
      whyDawn: hours.length ? '' : 'ps.why.noTime',
    };
  };

  XA.personaCaption = function (model, lang) {
    lang = lang || (XA.lang || 'ko');
    const names = model.names || {};
    const name = names[lang] || names.ko || model.name;
    const emoji = model.emoji || '';
    const num = model.hitShow == null ? '—' : model.hitShow;
    const url = XA.siteUrl ? XA.siteUrl({ c: 'persona', lang: lang }) : 'https://tuki0609.github.io/account-compass/?c=persona&lang=' + lang;
    if (lang === 'en') return 'My X alter ego is "' + name + '" ' + emoji + '\nHit index ×' + num + '\n\nWhat\'s yours? Drop your X analytics CSV, 30 sec 👇\n' + url;
    if (lang === 'ja') return '私のXの裏キャラは「' + name + '」' + emoji + '\n一発指数 ×' + num + '\n\nあなたは何タイプ？CSVを入れるだけ30秒👇\n' + url + '\n#Xの裏キャラ診断';
    return '제 X 부캐는 「' + name + '」 ' + emoji + '\n한 방 지수 ×' + num + '\n\n당신의 부캐는? CSV만 넣으면 30초 👇\n' + url + '\n#X부캐카드';
  };

  function whyRows(model) {
    const rows = [];
    const push = (k, raw, text) => rows.push({ k: k, raw: raw, text: text });
    push('pick', null, t('ps.why.pick', { name: model.name }));
    push('hit', model.hitRaw, model.hitRaw == null ? t('ps.hitNone') : t('ps.why.hit', { max: fmtInt(model.maxImp), med: fmtInt(model.medImp), n: model.hitShow }));
    push('save', model.bars[0].raw, model.bars[0].miss ? t('ps.why.miss', { col: t('col.bm') + ', ' + t('col.likes') }) : (model.bars[0].raw == null ? t('ps.why.nodiv', { a: t('col.bm'), b: t('col.likes') }) : t('ps.why.ratio', { a: t('col.bm'), b: t('col.likes'), n: fmtInt(model.bmSum), d: fmtInt(model.likesSum) })));
    push('chat', model.bars[1].raw, model.bars[1].miss ? t('ps.why.miss', { col: t('col.rep') }) : (model.bars[1].raw == null ? t('ps.why.nodiv', { a: t('col.rep'), b: t('col.likes') }) : t('ps.why.ratio', { a: t('col.rep'), b: t('col.likes'), n: fmtInt(model.repSum), d: fmtInt(model.likesSum) })));
    push('steady', model.active, model.active == null ? t('ps.why.noDay') : t('ps.why.active', { n: rawAttr(model.active) }));
    push('magnet', model.per1k, model.nfSum == null ? t('ps.why.miss', { col: t('col.nf') }) : (model.per1k == null ? t('ps.why.noImpDiv') : t('ps.why.per1k', { n: rawAttr(model.per1k), nf: fmtInt(model.nfSum), imp: fmtInt(model.impSum) })));
    push('conv', model.conv, model.profSum == null ? t('ps.why.miss', { col: t('col.prof') }) : (model.conv == null ? t('ps.why.nodiv', { a: t('col.nf'), b: t('col.prof') }) : t('ps.why.conv', { n: rawAttr(model.conv), v: rawAttr(model.visitsPer1k) })));
    push('dawn', model.dawnShare, model.whyDawn ? t(model.whyDawn) : t('ps.why.dawn', { n: rawAttr(model.dawnShare), h: fmtInt(model.dawnN), t: fmtInt(model.timed) }));
    push('repost', model.scores ? null : null, model.rtSum == null ? t('ps.why.miss', { col: t('col.rt') }) : (model.likesSum > 0 ? t('ps.why.ratio', { a: t('col.rt'), b: t('col.likes'), n: fmtInt(model.rtSum), d: fmtInt(model.likesSum) }) : t('ps.why.nodiv', { a: t('col.rt'), b: t('col.likes') })));
    rows[rows.length - 1].raw = (model.likesSum > 0 && model.rtSum != null) ? model.rtSum / model.likesSum : null;
    push('link', model.linkShare, model.linkShare == null ? t('ps.why.noLink') : t('ps.why.link', { n: rawAttr(model.linkShare) }));
    push('len', model.medLen, model.medLen == null ? t('ps.why.miss', { col: t('col.text') }) : t('ps.why.len', { n: fmtInt(model.medLen) }));
    if (model.missing.length) push('miss', null, t('ps.missing', { cols: model.missing.map((k) => t('col.' + k)).join(', ') }));
    if (model.thin) push('thin', null, t('ps.why.thin', { n: fmtInt(model.n), imp: fmtInt(model.impSum) }));
    return rows;
  }

  function barHTML(model) {
    return model.bars.map((b) => {
      if (b.bar == null) {
        return `<div class="ps-stat" data-stat="${esc(b.id)}" data-miss="1"><span>${esc(t(STAT_KEY[b.id]))}</span><span class="ps-miss">${esc(t('ps.barMiss'))}</span></div>`;
      }
      return `<div class="ps-stat" data-stat="${esc(b.id)}" data-raw="${esc(rawAttr(b.raw))}" data-bar="${b.bar}"><span>${esc(t(STAT_KEY[b.id]))}</span><b>${b.bar}</b><div class="ps-bar" aria-hidden="true"><i style="width:${b.bar}%"></i></div></div>`;
    }).join('');
  }

  function cardHTML(model) {
    const flag = XA._isSample ? `<p class="ps-flag">${esc(t('ps.sample'))}</p>` : '';
    const hit = model.hitShow == null
      ? `<p class="ps-hit" id="ps-hit">${esc(t('ps.hitNone'))}</p>`
      : `<p class="ps-kicker">${esc(t('ps.hitK'))}</p><p class="ps-hit" id="ps-hit" data-raw="${esc(rawAttr(model.hitRaw))}" data-show="${esc(model.hitShow)}">×${esc(model.hitShow)}</p><p class="ps-hitline">${esc(t('ps.hitLine', { n: model.hitShow }))}</p>`;
    const period = model.period ? esc(model.period.from === model.period.to ? model.period.from : t('ps.period', model.period)) : esc(t('ps.noDate'));
    const handleLine = !model.handle ? '' : (model.hideHandle ? `<p class="ps-handle" id="ps-handle">${esc(t('ps.handleHidden'))}</p>` : `<p class="ps-handle" id="ps-handle">@${esc(model.handle)}</p>`);
    const snip = model.snippet && !model.hideSnippet ? `<p class="ps-snip" id="ps-snip">${esc(model.snippet)}</p>` : '';
    const why = whyRows(model).map((r) => `<li data-k="${esc(r.k)}"${finite(r.raw) ? ` data-raw="${esc(rawAttr(r.raw))}"` : ''}>${esc(r.text)}</li>`).join('');
    return `<article class="ps-visual" id="ps-card" data-id="${esc(model.id)}" data-roast="${model.roastIndex}" data-n="${model.n}" data-imp="${Math.round(model.impSum)}" style="--ps:${model.color};background:${model.color}">
      ${flag}
      <p class="ps-emoji" aria-hidden="true">${model.emoji}</p>
      <h2 class="ps-name">${model.emoji} ${esc(model.name)}</h2>
      <p class="ps-roast" id="ps-roast">${esc(model.roast)}</p>
      <p class="ps-play">${esc(model.play)}</p>
      ${hit}
      <div class="ps-stats">${barHTML(model)}</div>
      ${handleLine}
      ${snip}
      <p class="ps-foot">${esc(t('ps.footer'))}</p>
      <p class="ps-meta" id="ps-period"${model.period ? ` data-from="${esc(model.period.from)}" data-to="${esc(model.period.to)}"` : ''}>${period} · ${esc(t('ps.count', { n: fmtInt(model.n) }))}</p>
      <p class="ps-site">tuki0609.github.io/account-compass</p>
    </article>
    <details class="ps-why" id="ps-why"><summary>${esc(t('ps.why'))}</summary><ul>${why}</ul></details>`;
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

  XA.personaDraw = function (model, opt) {
    opt = opt || {};
    const wide = !!opt.wide;
    const W = wide ? 1200 : 1080;
    const H = wide ? 675 : 1350;
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const g = c.getContext('2d');
    g.fillStyle = model.color || '#15803d';
    g.fillRect(0, 0, W, H);
    g.fillStyle = '#ffffff';
    g.textAlign = 'center';
    const name = (model.emoji || '') + '  ' + (model.name || '');
    if (wide) {
      g.font = '800 64px ' + FONT;
      g.fillText(name, W / 2, 120);
      g.font = '600 28px ' + FONT;
      wrapText(g, model.roast, W - 120).slice(0, 2).forEach((ln, i) => g.fillText(ln, W / 2, 180 + i * 36));
      g.font = '800 92px ' + FONT;
      g.fillText(model.hitShow == null ? t('ps.hitNone') : '×' + model.hitShow, W / 2, 320);
      g.font = '700 28px ' + FONT;
      g.fillText(t('ps.footer'), W / 2, 560);
      g.font = '700 24px ' + FONT;
      g.fillText('tuki0609.github.io/account-compass', W / 2, 620);
      return c;
    }
    g.font = '800 72px ' + FONT;
    g.fillText(model.emoji || '', W / 2, 150);
    g.font = '800 64px ' + FONT;
    wrapText(g, model.name, W - 140).slice(0, 2).forEach((ln, i) => g.fillText(ln, W / 2, 250 + i * 74));
    g.font = '600 32px ' + FONT;
    let y = 430;
    wrapText(g, model.roast, W - 160).slice(0, 4).forEach((ln) => { g.fillText(ln, W / 2, y); y += 42; });
    g.font = '500 26px ' + FONT;
    g.fillText(model.play, W / 2, y + 10);
    y += 90;
    g.font = '800 120px ' + FONT;
    g.fillText(model.hitShow == null ? '—' : '×' + model.hitShow, W / 2, y + 80);
    y += 120;
    g.font = '700 30px ' + FONT;
    if (model.hitShow != null) { g.fillText(t('ps.hitLine', { n: model.hitShow }), W / 2, y); y += 48; }
    g.textAlign = 'left';
    g.font = '700 28px ' + FONT;
    model.bars.forEach((b) => {
      if (b.bar == null) return;
      y += 46;
      g.fillText(t(STAT_KEY[b.id]), 120, y);
      g.textAlign = 'right';
      g.fillText(String(b.bar), W - 120, y);
      g.textAlign = 'left';
      g.fillStyle = 'rgba(255,255,255,.3)';
      g.fillRect(120, y + 12, W - 240, 14);
      g.fillStyle = '#ffffff';
      g.fillRect(120, y + 12, (W - 240) * (b.bar / 99), 14);
      y += 20;
    });
    if (!model.hideHandle && model.handle) {
      y += 48;
      g.font = '700 28px ' + FONT;
      g.textAlign = 'center';
      g.fillText('@' + model.handle, W / 2, y);
    }
    if (!model.hideSnippet && model.snippet) {
      y += 40;
      g.font = '500 26px ' + FONT;
      g.textAlign = 'center';
      g.fillText(model.snippet, W / 2, y);
    }
    g.textAlign = 'center';
    g.font = '700 26px ' + FONT;
    g.fillText(t('ps.footer'), W / 2, H - 120);
    const meta = (model.period ? (model.period.from === model.period.to ? model.period.from : t('ps.period', model.period)) : t('ps.noDate')) + '  ·  ' + t('ps.count', { n: fmtInt(model.n) });
    g.font = '600 24px ' + FONT;
    g.fillText(meta, W / 2, H - 80);
    g.font = '700 26px ' + FONT;
    g.fillText('tuki0609.github.io/account-compass', W / 2, H - 40);
    return c;
  };

  function prefs() {
    return {
      hideSnippet: XA._psHideSnippet !== false,
      hideHandle: XA._psHideHandle !== false,
      includeReplies: !!XA._psIncludeReplies,
    };
  }
  function say(note, key) {
    if (!note) return;
    note.hidden = false;
    note.textContent = t(key);
  }
  function render(el, A) {
    const mod = XA.moduleById('persona');
    const st = XA.cardStatus(mod, A);
    if (!A || st.state !== 'ready') {
      el.innerHTML = `<div class="card ps-blocked"><h2>${esc(t('hub.card.persona.t'))}</h2><p>${esc(t(st.key || 'ps.why.empty', st.params))}</p></div>`;
      return;
    }
    const model = XA.personaModel(A, prefs());
    if (!model || model.blocked) {
      el.innerHTML = `<div class="card ps-blocked" id="ps-blocked"><h2>${esc(t('hub.card.persona.t'))}</h2><p>${esc(t((model && model.key) || 'ps.why.overview'))}</p></div>`;
      return;
    }
    el.innerHTML = `<div class="ps-wrap">
      ${cardHTML(model)}
      <div class="ps-tools">
        <label><input type="checkbox" id="ps-hide-handle" ${model.hideHandle ? 'checked' : ''}> ${esc(t('ps.hideHandle'))}</label>
        <label><input type="checkbox" id="ps-hide-line" ${model.hideSnippet ? 'checked' : ''}> ${esc(t('ps.hideLine'))}</label>
        <label><input type="checkbox" id="ps-replies" ${model.includeReplies ? 'checked' : ''}> ${esc(t('ps.replies'))}</label>
      </div>
      <div class="share-row">
        <button type="button" class="btn" id="ps-save">${esc(t('share.save'))}</button>
        <button type="button" class="btn ghost" id="ps-copy">${esc(t('share.copy'))}</button>
        <button type="button" class="btn ghost" id="ps-x">${esc(t('share.x'))}</button>
      </div>
      <p class="share-note" id="ps-share-note" hidden></p>
      <p class="ps-honest">${esc(t('ps.shareNote'))}</p>
    </div>`;
    const redraw = () => {
      XA._psHideHandle = document.getElementById('ps-hide-handle').checked;
      XA._psHideSnippet = document.getElementById('ps-hide-line').checked;
      XA._psIncludeReplies = document.getElementById('ps-replies').checked;
      render(el, A);
    };
    document.getElementById('ps-hide-handle').addEventListener('change', redraw);
    document.getElementById('ps-hide-line').addEventListener('change', redraw);
    document.getElementById('ps-replies').addEventListener('change', redraw);
    const live = () => XA.personaModel(A, prefs());
    document.getElementById('ps-save').addEventListener('click', () => {
      XA.downloadCanvas(XA.personaDraw(live()), 'x-persona.png');
    });
    document.getElementById('ps-copy').addEventListener('click', () => {
      const note = document.getElementById('ps-share-note');
      XA.copyCanvas(XA.personaDraw(live()), 'x-persona.png').then((r) => say(note, r.how === 'clipboard' ? 'share.copied' : 'share.copyFallback'));
    });
    document.getElementById('ps-x').addEventListener('click', () => {
      const note = document.getElementById('ps-share-note');
      const m = live();
      const caption = XA.personaCaption(m, XA.lang || 'ko');
      XA.shareToX(XA.personaDraw(m), caption, 'x-persona.png').then((r) => {
        if (r.how === 'intent') say(note, 'share.paste');
        else if (r.how === 'share') say(note, 'share.shared');
      });
    });
  }

  function personaReady(A) {
    if (!A) return { state: 'empty', key: 'hub.state.empty' };
    if (A.mode === 'overview') return { state: 'blocked', key: 'ps.why.overview' };
    if (!A.map || A.map.imp == null) return { state: 'blocked', key: 'ps.why.noImp' };
    if (!(A.posts || []).length) return { state: 'blocked', key: 'ps.why.empty' };
    return { state: 'ready', key: 'hub.state.ready' };
  }

  if (XA.registerModule) {
    XA.registerModule({
      id: 'persona',
      order: 2,
      category: 'fun',
      status: 'ready',
      icon: '🎭',
      titleKey: 'hub.card.persona.t',
      descKey: 'hub.card.persona.d',
      needsKey: 'hub.needs.persona',
      requires: ['imp'],
      ready: personaReady,
      render: render,
    });
  }
  XA.renderPersona = render;
  if (XA.mountHome) XA.mountHome();
})();
