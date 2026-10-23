/* 복붙 진단 — 규칙 기반 체크리스트. 브라우저 안에서만 실행.
   기준은 일반적인 경험칙(실제 계정 수치 없음). CSV를 올렸다면 시간대·성과는 그 사람 자신의 평균과 비교. */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const t = (k, p) => XA.t(k, p);
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hourSel = $('#d-hour');
  function fillHours() {
    const v = hourSel.value;
    hourSel.innerHTML = `<option value="">${esc(t('diag.hourNone'))}</option>` + Array.from({ length: 24 }, (_, h) => `<option value="${h}">${esc(t('diag.hourOpt', { h: String(h).padStart(2, '0') }))}</option>`).join('');
    hourSel.value = v;
  }
  fillHours();

  // X 글자 수 근사: 한글·한자·일본어 등은 2, URL은 23으로 계산 (기본 한도 280 = 한글 약 140자)
  function weighted(s) {
    let n = 0; const noUrl = s.replace(/https?:\/\/\S+/g, () => { n += 23; return ''; });
    for (const ch of noUrl) { const c = ch.codePointAt(0); n += (c <= 0x10ff || (c >= 0x2000 && c <= 0x200d) || (c >= 0x2010 && c <= 0x201f) || (c >= 0x2032 && c <= 0x2037)) ? 1 : 2; }
    return n;
  }
  XA.weighted = weighted;
  const updateCount = () => { const s = $('#d-text').value; $('#d-count').textContent = t('diag.count', { n: [...s].length, w: weighted(s) }); };
  $('#d-text').addEventListener('input', updateCount);
  updateCount();

  $('#d-ex').addEventListener('click', () => { $('#d-text').value = t('diag.example'); $('#d-hour').value = '14'; $('#d-media').value = 'image'; updateCount(); });

  // 내 CSV(샘플 제외)를 올렸다면 그 데이터의 시간대·평균을 기준으로 씀
  function ownData() {
    const A = XA.last;
    if (!A || A.mode === 'overview' || XA._isSample || !A.posts) return null;
    const O = A.posts.filter((p) => !p.isReply); const P = O.length ? O : A.posts;
    const timed = P.filter((p) => p.hour != null);
    const all = XA.agg(P);
    const blocks = timed.length >= 10 ? XA.hourBlocks(timed).filter((b) => b.n >= 3) : [];
    const best = [...blocks].sort((a, b) => b.avgLikes - a.avgLikes)[0] || null;
    return { all, blocks, best, hasBm: A.hasBm };
  }

  function diagnose(input) {
    const s = input.text.trim(); const lines = s.split(/\n/).filter((l) => l.trim()); const first = (lines[0] || '').trim();
    const list = XA.countList(s); const checks = []; const own = ownData();
    // 1. 테이크어웨이
    const tk = { prompt: /프롬프트|prompt|プロンプト|"[^"]{15,}"/i.test(s), list: list >= 2, steps: /단계|순서|step|방법|하는\s?법|how[\s-]to|手順|やり方|作り方|ステップ/i.test(s), link: /https?:\/\//.test(s) };
    const tkHas = Object.keys(tk).filter((k) => tk[k]); const tkN = tkHas.length;
    checks.push({ id: 'take', max: 30, pt: tkN >= 2 ? 30 : tkN === 1 ? 20 : 0,
      note: tkN ? t('diag.take.has', { v: tkHas.map((k) => t('diag.take.' + k)).join(', ') }) : t('diag.none'),
      fix: tkN >= 2 ? '' : tkN === 1 ? t('diag.take.fix1') : t('diag.take.fix0') });
    // 2. 첫 줄 훅 (한국어 + 영어)
    const hookWords = [/무료|공짜|\bfree\b|無料/i, /돈\s*쓰기\s*전|결제\s*전|before you (pay|spend|buy)|課金する前|お金を使う前|有料の前/i, /\d+\s*일\s*차|\bday\s*\d+\b|\d+\s*日目/i, /\d+\s*(곳|가지|개|단계|선)|\b\d+\s+(tools|ways|tips|steps|sites|apps|things|ideas|prompts)\b|\d+\s*(選|つ|個|ステップ)/i, /정리|\b(roundup|cheat\s?sheet)\b|まとめ/i, /직접\s*해|\bi (tried|tested|built)\b|やってみた|試してみた/i, /\?$|？$/, /^(이거|이것|아직도|모르면|stop |still |don't |if you |これ|まだ|知らない)/i];
    const hk = hookWords.filter((re) => re.test(first)).length; const fw = weighted(first);
    const hpt = Math.min(25, hk * 10 + (fw > 0 && fw <= 70 ? 10 : fw <= 100 ? 5 : 0));
    checks.push({ id: 'hook', max: 25, pt: hpt, note: t('diag.hook.note', { n: [...first].length, k: hk }),
      fix: hpt >= 20 ? '' : t('diag.hook.fix') + (fw > 70 ? ' ' + t('diag.hook.fixLen') : '') });
    // 3. 길이·가독성
    const w = weighted(s); const len = [...s].length; let lpt, lnote, lfix = '';
    if (len < 20) { lpt = 3; lnote = t('diag.len.short'); lfix = t('diag.len.shortFix'); }
    else if (w > 280) { lpt = 8; lnote = t('diag.len.over', { w }); lfix = t('diag.len.overFix'); }
    else if (lines.length >= 3) { lpt = 15; lnote = t('diag.len.note', { n: len, l: lines.length }); }
    else { lpt = 10; lnote = t('diag.len.note', { n: len, l: lines.length }); lfix = t('diag.len.breakFix'); }
    checks.push({ id: 'len', max: 15, pt: lpt, note: lnote, fix: lfix });
    // 4. 올릴 시간: 내 데이터가 있으면 내 최고 시간대와 비교, 없으면 일반 경험칙(새벽만 감점)
    const h = input.hour === '' ? null : +input.hour; let tpt, tnote, tfix = '';
    const hb = (x) => (own && own.blocks.find((b) => x >= b.a && x < b.b)) || null;
    if (h == null) { tpt = 5; tnote = t('diag.time.unset'); tfix = own && own.best ? t('diag.time.unsetOwn', { b: own.best.label }) : t('diag.time.unsetFix'); }
    else if (own && own.best) {
      const b = hb(h);
      if (b && b === own.best) { tpt = 15; tnote = t('diag.time.ownBest', { h }); }
      else if (b && b.avgLikes >= own.all.avgLikes) { tpt = 12; tnote = t('diag.time.ownOk', { h }); tfix = t('diag.time.ownFix', { b: own.best.label }); }
      else { tpt = 8; tnote = t('diag.time.ownLow', { h }); tfix = t('diag.time.ownFix', { b: own.best.label }); }
    }
    else if (h < 6) { tpt = 6; tnote = t('diag.time.night', { h }); tfix = t('diag.time.nightFix'); }
    else { tpt = 12; tnote = t('diag.time.set', { h }); tfix = t('diag.time.setFix'); }
    checks.push({ id: 'time', max: 15, pt: tpt, note: tnote, fix: tfix });
    // 5. 미디어
    const m = input.media; let mpt, mnote, mfix = '';
    if (m === 'image') { mpt = 10; mnote = t('diag.media.image'); }
    else if (m === 'video' || m === 'gif') { mpt = tkN ? 10 : 6; mnote = t('diag.media.' + m); if (!tkN) mfix = t('diag.media.videoFix'); }
    else { mpt = 4; mnote = t('diag.none'); mfix = t('diag.media.noneFix'); }
    checks.push({ id: 'media', max: 10, pt: mpt, note: mnote, fix: mfix });
    // 6. 마무리 / 형식
    const last = lines.slice(-1)[0] || ''; const endOk = /https?:\/\/|👇|프롬프트|답글|저장|링크|プロンプト|返信|保存して|リンク|\?$|？$|\b(below|link|prompt|reply|save|bookmark)\b/i.test(last);
    let kpt = endOk ? 5 : 0, kfix = endOk ? '' : t('diag.end.fix');
    if (input.kind === 'quote') { kpt = Math.max(0, kpt - 3); kfix = (kfix ? kfix + ' ' : '') + t('diag.end.quoteFix'); }
    checks.push({ id: 'end', max: 5, pt: kpt, note: endOk ? t('diag.has') : t('diag.none'), fix: kfix });

    const score = checks.reduce((a, c) => a + c.pt, 0);
    const grade = score >= 80 ? ['diag.grade.a', '#17a34a'] : score >= 60 ? ['diag.grade.b', '#4f46e5'] : score >= 40 ? ['diag.grade.c', '#f59e0b'] : ['diag.grade.d', '#e5484d'];
    // 성과(선택 입력): 내 CSV 평균과 비교. 없으면 일반 경험칙(북마크 ÷ 좋아요)만.
    let perf = '';
    const v = +input.views || 0, lk = +input.likes || 0, bm = +input.bm || 0; const hasBm = input.bm !== '' && input.bm != null;
    if (v > 0) {
      const lr = lk / v, br = bm / v;
      perf = t('diag.perf.base', { v: v.toLocaleString(XA.locale()), lr: (lr * 100).toFixed(2) + '%' }) + (hasBm ? ' · ' + t('diag.perf.br', { br: (br * 100).toFixed(2) + '%' }) : '') + '. ';
      if (own) {
        perf += t('diag.perf.own', { lr: (own.all.lr * 100).toFixed(2) + '%', x: (lr / (own.all.lr || 1e-9)).toFixed(1) }) + (hasBm && own.hasBm ? ' ' + t('diag.perf.ownBr', { br: (own.all.br * 100).toFixed(2) + '%', x: (br / (own.all.br || 1e-9)).toFixed(1) }) : '');
      } else {
        perf += t('diag.perf.noOwn');
        if (hasBm && lk > 0 && bm >= lk * 0.5) perf += ' ' + t('diag.perf.saveGood');
      }
    }
    return { checks, score, grade, cat: XA.categorize(s), perf, own: !!own };
  }
  XA.diagnose = diagnose;

  let lastInput = null;
  function show(input) {
    const out = $('#d-result');
    if (!input.text.trim()) { out.hidden = false; out.innerHTML = `<div class="alert">${t('diag.empty')}</div>`; return; }
    const R = diagnose(input);
    const C = 2 * Math.PI * 46, off = C * (1 - R.score / 100);
    const fixes = R.checks.filter((c) => c.fix);
    out.hidden = false;
    out.innerHTML = `<div class="card"><div class="score">
      <svg class="ring" viewBox="0 0 110 110"><circle cx="55" cy="55" r="46" fill="none" stroke="#eef2f7" stroke-width="10"/><circle cx="55" cy="55" r="46" fill="none" stroke="${R.grade[1]}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" transform="rotate(-90 55 55)"/><text x="55" y="62" text-anchor="middle" font-size="26" font-weight="800" fill="#14171a">${R.score}</text></svg>
      <div><div class="grade" style="color:${R.grade[1]}">${t(R.grade[0])}</div><div class="muted small">${t('diag.cat')} <span class="chip">${esc(XA.catName(R.cat))}</span> · ${t('diag.of100')}</div>${R.perf ? `<div class="small" style="margin-top:6px">${esc(R.perf)}</div>` : ''}</div></div>
      <ul class="checks">${R.checks.map((c) => `<li><span>${c.pt >= c.max * 0.8 ? '✅' : c.pt >= c.max * 0.4 ? '🟡' : '❌'}</span><span><b>${esc(t('diag.c.' + c.id))}</b> <span class="muted small">${esc(c.note)}</span></span><span class="pt">${c.pt}/${c.max}</span>${c.fix ? `<div class="fix">👉 ${esc(c.fix)}</div>` : ''}</li>`).join('')}</ul>
      ${fixes.length ? '' : `<p class="small">${t('diag.allGood')}</p>`}
      <p class="muted small">${t(R.own ? 'diag.basisOwn' : 'diag.basis')}</p></div>`;
  }
  const readInput = () => ({ text: $('#d-text').value, hour: $('#d-hour').value, media: $('#d-media').value, kind: $('#d-kind').value, views: $('#d-views').value, likes: $('#d-likes').value, bm: $('#d-bm').value });
  $('#d-run').addEventListener('click', () => { lastInput = readInput(); show(lastInput); });
  document.addEventListener('langchange', () => { fillHours(); updateCount(); if (lastInput && !$('#d-result').hidden) show(lastInput); });
})();
