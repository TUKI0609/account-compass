/* 계정 나침반 (Account Compass) — 모든 처리는 브라우저 안에서만. 네트워크 전송 없음.
   샘플 데이터는 samples.js에 내장 → file:// 로 열어도 동작. 문구는 i18n.js 사전(XA.t)에서 가져옴. */
(function () {
  'use strict';
  const XA = (window.XA = window.XA || {});
  const t = (k, p) => XA.t(k, p);
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n) => (n == null || isNaN(n) ? '-' : Math.round(n).toLocaleString(XA.locale()));
  const f1 = (n) => (n == null || !isFinite(n) ? '-' : n.toFixed(1));
  const pct = (x, d = 2) => (x == null || !isFinite(x) ? '-' : (x * 100).toFixed(d) + '%');
  const median = (a) => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const sum = (a) => a.reduce((x, y) => x + y, 0);
  const avg = (a) => (a.length ? sum(a) / a.length : 0);
  const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0];
  const day = (d) => t('day.' + d);
  XA.esc = esc;

  /* ---------- 탭 ---------- */
  function showTab(name) {
    document.querySelectorAll('.tab').forEach((b) => { const on = b.dataset.tab === name; b.classList.toggle('active', on); b.setAttribute('aria-selected', on); });
    document.querySelectorAll('.panel').forEach((p) => p.classList.toggle('active', p.id === 'tab-' + name));
    window.scrollTo({ top: 0 });
  }
  document.querySelectorAll('.tab').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.tab)));
  document.querySelectorAll('[data-goto]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); showTab(a.dataset.goto); }));
  XA.showTab = showTab;

  /* ---------- CSV 파서 (따옴표/줄바꿈/BOM/구분자 자동) ---------- */
  function detectDelim(text) {
    let inQ = false; const cnt = { ',': 0, ';': 0, '\t': 0 };
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '"') inQ = !inQ; else if (!inQ && (c === '\n' || c === '\r')) break; else if (!inQ && c in cnt) cnt[c]++;
    }
    const best = Object.entries(cnt).sort((a, b) => b[1] - a[1])[0];
    return best[1] > 0 ? best[0] : ',';
  }
  function parseCSV(text) {
    text = text.replace(/^\uFEFF/, '');
    const d = detectDelim(text); const rows = []; let row = []; let f = ''; let inQ = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (inQ) {
        if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else inQ = false; } else f += c;
      } else if (c === '"') inQ = true;
      else if (c === d) { row.push(f); f = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(f); f = ''; if (row.some((x) => x.trim() !== '')) rows.push(row); row = []; }
      else f += c;
    }
    row.push(f); if (row.some((x) => x.trim() !== '')) rows.push(row);
    return rows;
  }

  /* ---------- 컬럼 매칭 (영문/한글/일문/구 Tweet activity) — 대소문자·공백·기호 무시 ---------- */
  const norm = (h) => String(h).toLowerCase().replace(/[\s_\-.,:;()\[\]/·'"#&+]/g, '');
  const ALIAS = {
    id: ['postid', 'tweetid', 'id', 'postidentifier', '게시물id', '포스트id', '트윗id', '게시물아이디', 'ポストid', '投稿id', 'ツイートid'],
    date: ['date', 'time', 'day', 'createdat', 'createdate', 'postdate', 'datetime', 'posttime', 'postedat', 'publishedat', 'timestamp', '날짜', '일시', '게시일', '게시일시', '작성일', '작성일시', '日付', '投稿日時', '投稿日', '日時', '時間'],
    text: ['posttext', 'tweettext', 'text', 'content', 'postcontent', 'body', '게시물텍스트', '게시물내용', '게시물본문', '본문', '내용', '텍스트', 'ポスト本文', '投稿内容', 'ポストテキスト', 'ポストのテキスト', 'ツイート本文', '本文'],
    link: ['postlink', 'tweetpermalink', 'permalink', 'link', 'posturl', 'tweeturl', 'url', '게시물링크', '링크', '게시물url', '投稿url', 'ポストのリンク', 'ポストリンク', 'ツイートの固定リンク', '投稿リンク'],
    imp: ['impressions', 'impression', 'views', 'impressioncount', 'postimpressions', '노출수', '노출횟수', '노출', '임프레션', '임프레션수', '조회수', 'インプレッション数', 'インプレッション', '表示回数', 'インプレッション回数'],
    likes: ['likes', 'like', 'favorites', 'favourites', '좋아요', '좋아요수', '마음에들어요', '마음에들어요수', 'いいね', 'いいね数', 'お気に入り'],
    eng: ['engagements', 'engagement', 'totalengagements', '참여', '참여수', '참여횟수', 'エンゲージメント', 'エンゲージメント数'],
    bm: ['bookmarks', 'bookmark', '북마크', '북마크수', 'ブックマーク', 'ブックマーク数'],
    shares: ['shares', 'share', 'sharecount', '공유', '공유수', '공유횟수', '共有', '共有数', 'シェア', 'シェア数'],
    nf: ['newfollows', 'newfollow', 'follows', 'newfollowers', 'followsgained', 'followersgained', '새로운팔로우', '새팔로워', '새팔로우', '새로운팔로워', '新しいフォロー', '新しいフォロワー', '新規フォロー', '新規フォロワー'],
    unf: ['unfollows', 'unfollow', 'unfollowers', 'followslost', '언팔로우', '언팔로우수', 'フォロー解除', 'フォロー解除数', 'アンフォロー'],
    posts: ['posts', 'postscreated', 'postcount', 'createpost', 'createposts', 'createdposts', '게시물작성하기', '게시물수', '작성한게시물', 'ポスト', 'ポストを作成', '投稿数'],
    vid: ['videoviews', 'videoview', '동영상조회수', '동영상재생수', '動画再生数', '動画の再生数', 'ビデオ再生数', '動画の視聴回数'],
    media: ['mediaviews', 'mediaview', '미디어조회수', '미디어재생수', 'メディアの再生数', 'メディア再生数'],
    rep: ['replies', 'reply', '답글', '답글수', '답글횟수', '返信', '返信数', 'リプライ', 'リプライ数'],
    rt: ['reposts', 'retweets', 'repost', 'retweet', '재게시', '재게시수', '재게시물', '리포스트', '리트윗', 'リポスト', 'リポスト数', 'リツイート', 'リツイート数'],
    prof: ['profilevisits', 'profilevisit', 'userprofileclicks', 'profileclicks', 'profileviews', '프로필조회수', '프로필방문', '프로필방문수', '프로필클릭', 'プロフィールへのアクセス数', 'プロフィールへのアクセス', 'プロフィールアクセス', 'ユーザープロフィールクリック', 'プロフィールクリック'],
    det: ['detailexpands', 'detailexpand', 'detailsexpands', 'detailsexpanded', 'detailclicks', '세부정보펼치기', '세부정보확장', '상세보기', '상세클릭', '세부정보클릭', '詳細のクリック数', '詳細表示', '詳細クリック', '詳細の展開'],
    url: ['urlclicks', 'urlclick', 'url클릭수', 'url클릭', 'linkclicks', '링크클릭', '링크클릭수', 'urlのクリック数', 'urlクリック数', 'urlクリック'],
    tag: ['hashtagclicks', 'hashtagclick', '해시태그클릭수', '해시태그클릭', 'ハッシュタグのクリック数', 'ハッシュタグクリック', 'ハッシュタグのクリック'],
    plink: ['permalinkclicks', 'permalinkclick', '고유링크클릭수', '고유링크클릭', '퍼머링크클릭', 'パーマリンクのクリック数', '固定リンクのクリック数', '固定リンクのクリック', 'パーマリンクのクリック'],
  };
  XA.ALIAS = ALIAS;
  function mapColumns(headers) {
    const H = headers.map(norm); const map = {}; const used = new Set();
    const bad = (h) => /promoted|paid|유료|프로모션|광고|プロモ|広告/.test(h);
    // 1차: 정확히 일치하는 칸 먼저 (모든 항목), 2차: 부분 일치 + 제외 규칙
    const ok = (k, h) => !(k === 'eng' && /rate|율|率/.test(h)) && !(k === 'link' && /click|클릭|クリック/.test(h)) && !(k === 'id' && h !== 'id' && !/id|아이디/.test(h)) && !(k === 'text' && /click|클릭|クリック|작성|create|作成/.test(h)) &&
      !(k === 'imp' && /동영상|미디어|프로필|video|media|profile|動画|メディア|プロフィール/.test(h)) && !(k === 'nf' && /^un|언팔|lost|解除|アンフォロー/.test(h)) && !(k === 'url' && /permalink|고유|퍼머|固定リンク|パーマリンク/.test(h)) &&
      !(k === 'likes' && /rate|率/.test(h)) && !(k === 'date' && /update|更新/.test(h));
    for (const [k, al] of Object.entries(ALIAS)) { const idx = H.findIndex((h, i) => !used.has(i) && !bad(h) && al.includes(h)); if (idx >= 0) { map[k] = idx; used.add(idx); } }
    for (const [k, al] of Object.entries(ALIAS)) {
      if (map[k] != null || k === 'posts') continue;
      const idx = H.findIndex((h, i) => !used.has(i) && !bad(h) && al.some((a) => a.length >= 3 && h.includes(a)) && ok(k, h));
      if (idx >= 0) { map[k] = idx; used.add(idx); }
    }
    return map;
  }
  function num(v) {
    if (v == null) return 0; let s = String(v).trim().replace(/,/g, '');
    if (!s || s === '-' || s === '—') return 0;
    let m = 1; if (/k$/i.test(s)) { m = 1e3; s = s.slice(0, -1); } else if (/m$/i.test(s)) { m = 1e6; s = s.slice(0, -1); } else if (/[만万]$/.test(s)) { m = 1e4; s = s.slice(0, -1); }
    const n = parseFloat(s); return isFinite(n) ? n * m : 0;
  }

  /* ---------- 시간: 게시물 ID(snowflake) → 정확한 시각, 없으면 날짜 칸 ---------- */
  function timeFromId(id) {
    if (!/^\d{15,20}$/.test(id || '')) return null;
    try { const ms = Number((BigInt(id) >> 22n) + 1288834974657n); if (ms > Date.UTC(2010, 10, 1) && ms < Date.now() + 864e5 * 2) return ms; } catch (e) { }
    return null;
  }
  function timeFromDate(s) {
    s = String(s || '').trim(); if (!s) return null;
    const hasTime = /\d{1,2}:\d{2}/.test(s);
    let m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?\s*(Z|[+-]\d{2}:?\d{2}|UTC|GMT)?$/i);
    if (m) {
      const [, y, mo, d, hh = '0', mi = '0', ss = '0', tz] = m;
      let ms = Date.UTC(+y, +mo - 1, +d, +hh, +mi, +ss);
      if (!tz) ms -= 9 * 3600e3; // 시간대 표기 없으면 한국 시간으로 가정
      else if (/^[+-]/.test(tz)) { const z = tz.replace(':', ''); const off = (z[0] === '-' ? -1 : 1) * (+z.slice(1, 3) * 60 + +z.slice(3, 5)); ms -= off * 60e3; }
      return { ms, hasTime, assumed: !tz && hasTime };
    }
    m = s.match(/^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일(?:\s*(오전|오후)?\s*(\d{1,2}):(\d{2}))?/);
    if (m) { let h = +(m[5] || 0); if (m[4] === '오후' && h < 12) h += 12; if (m[4] === '오전' && h === 12) h = 0; return { ms: Date.UTC(+m[1], +m[2] - 1, +m[3], h, +(m[6] || 0)) - 9 * 3600e3, hasTime: !!m[5], assumed: !!m[5] }; }
    m = s.match(/^(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日(?:\s*(午前|午後)?\s*(\d{1,2}):(\d{2}))?/);
    if (m) { let h = +(m[5] || 0); if (m[4] === '午後' && h < 12) h += 12; if (m[4] === '午前' && h === 12) h = 0; return { ms: Date.UTC(+m[1], +m[2] - 1, +m[3], h, +(m[6] || 0)) - 9 * 3600e3, hasTime: !!m[5], assumed: !!m[5] }; }
    const p = Date.parse(s);
    if (!isNaN(p)) {
      const tz = /(Z|[+-]\d{2}:?\d{2}|UTC|GMT)\s*$/i.test(s);
      if (!hasTime) { const dd = new Date(p); return { ms: Date.UTC(dd.getFullYear(), dd.getMonth(), dd.getDate()) - 9 * 3600e3, hasTime: false }; }
      return { ms: p, hasTime, assumed: !tz };
    }
    return null;
  }
  const kst = (ms) => new Date(ms + 9 * 3600e3);
  const kstStr = (ms, withTime) => { const d = kst(ms); const s = `${d.getUTCFullYear()}.${String(d.getUTCMonth() + 1).padStart(2, '0')}.${String(d.getUTCDate()).padStart(2, '0')}`; return withTime ? `${s} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}` : s; };

  /* ---------- 답글 감지: 본문이 @아이디로 시작하면 다른 사람 글에 단 답글 ---------- */
  const REPLY_AT = /^\s*[@＠]([A-Za-z0-9_]{1,15})\b/;
  const isReplyText = (s) => REPLY_AT.test(String(s || ''));
  function replyHandle(s) { const m = String(s || '').match(REPLY_AT); return m ? m[1] : ''; }
  XA.isReplyText = isReplyText;
  XA.replyHandle = replyHandle;

  /* ---------- 카테고리 규칙 (한국어 + 영어 + 일본어 키워드, 점수가 가장 높은 쪽). 이름은 i18n 'cat.<id>' ---------- */
  const CATS = ['guide', 'exp', 'video', 'daily', 'news', 'quote', 'etc'];
  XA.CATS = CATS;
  const NUMLIST = /^\s*(\d{1,2}[.)、．]|[①②③④⑤⑥⑦⑧⑨⑩]|step\s*\d|\d{1,2}단계|\d{1,2}\s*ステップ)/gim;
  const countList = (s) => (s.match(NUMLIST) || []).length + Math.max(0, (s.match(/(^|\s)(\d{1,2}\.|[①②③④⑤⑥⑦⑧⑨⑩])\s/g) || []).length - 1);
  const RULES = {
    guide: [
      [/정리|모음|총정리|한\s?눈에/, 2],
      [/가이드|튜토리얼|하는\s?법|만드는\s?법|방법|꿀팁|체크리스트|템플릿|복붙|복사해서|노하우|원스톱|따라\s?(해|하)|사용법|활용법|설정법|해결법|비교/, 2],
      [/프롬프트|prompt|명령어|プロンプト/i, 1], [/무료|공짜|free|無料|タダ/i, 1], [/\d+\s*(곳|가지|단계|선)(?![가-힣])/, 2],
      [/저장해\s?두|저장하고|북마크/, 1], [/공유(합니다|해\s?봅|드려|해요|!)|공유해봄/, 1], [/✅|✔|📌/, 1],
      [/\[[^\]]*(방법|정리|가이드|팁|하는 법|하기|원스톱)[^\]]*\]|\[[^\]]*프롬프트[^\]]*\]\s*$|^\s*\[[^\]]*프롬프트[^\]]*\]/m, 3],
      [/이거부터|확인해\s?보세요|해\s?보세요|추천|쓸\s?만한|유용한/, 1], [/이럴\s?때|해결/, 2],
      [/당신은\s?(지금부터|이제)|너는\s[^\n]{0,30}(전문|ai)\s?야|you are an?\b|act as\b/i, 3],
      // English
      [/\b(guide|tutorial|how[\s-]to|step[\s-]by[\s-]step|tips?|cheat\s?sheet|checklist|template|roundup|round-up|comparison|compared|ways to|playbook|walkthrough)\b/i, 2],
      [/\b\d+\s+(free\s+)?(tools|ways|tips|steps|sites|apps|prompts|resources|things|tricks|hacks|websites|extensions)\b/i, 2],
      [/\b(save this|bookmark this|bookmark it|copy[\s-]paste|you can use)\b/i, 1],
      // 日本語
      [/まとめ|総まとめ|ガイド|チュートリアル|やり方|作り方|使い方|方法|コツ|チェックリスト|テンプレート|コピペ|ノウハウ|比較|おすすめ/, 2],
      [/\d+\s*(選|つ|個|ステップ|件)/, 2],
      [/保存して|保存推奨|ブックマークして/, 1],
    ],
    exp: [
      [/\d+\s*(일|주)\s*차|\d+일째/, 3],
      [/해봤|해\s?봤|해본|해보았|만들어\s?봤|만들었|제작해\s?봤|제작했|제작\s?후|써\s?봤|써본|돌려\s?봤|테스트해|사용해\s?봤|구현해|시도|제작기|실험|도전|후기|시행착오|실패|삽질|빌드|런칭|개발\s?(중|일)|만들고\s?있/, 2],
      [/직접/, 1], [/바이브\s?코딩|vibe\s?coding/i, 1], [/\[[^\]]*(실험|일지|후기|제작기|도전|체험|테스트)[^\]]*\]/, 3],
      // English
      [/\b(day|week)\s*\d+\b/i, 3],
      [/\b(i tried|i built|i made|i tested|i spent|tried out|experiment(ed|ing)?|built (a|an|my)|shipped|launched my|my results|lessons learned|behind the scenes|progress update|build(ing)? in public|devlog|review)\b/i, 2],
      [/\d+\s*日目/, 3],
      [/やってみた|作ってみた|試してみた|使ってみた|実験|制作記|挑戦|レビュー|失敗した|導入してみた/, 2],
    ],
    video: [
      [/뮤비|뮤직\s?비디오|\bep\.?\s?\d+|브이로그|소리\s?켜|🎬|티저|트레일러|\bmv\b/i, 3],
      [/영상|비디오|video/i, 1], [/애니메이션|쇼츠|숏폼|시네마틱|릴스/i, 1],
      [/\b(music video|vlog|sound on|trailer|teaser|short film|animation|cinematic|clip|reel)\b/i, 2],
      [/ミュージックビデオ|ブイログ|音あり|ショートフィルム/, 3],
      [/動画|ビデオ|ショート動画|シネマティック|アニメーション|アニメ/, 1],
    ],
    daily: [
      [/좋은\s?아침|굿\s?밤|점심|저녁|아침|커피|아아\b|퇴근|출근|회사|회식|주말|연휴|피곤|날씨|산책|밥|잠이|잠도|잠들|꿀잠|자야|병원|냥이|고양이|강아지|집들이|이사|팔로워\s?달성|일상|추워|덥다|비가|에피소드|썰\b|사소한|오랜만에|축구|야구|경기|선수/, 2],
      [/\d[\d,]*\s?팔로워|팔로워\s?\d|감사합니다|고맙습니다/, 2], [/(^|\s)(나|ai|AI|회사|팀장)\s?:\s/, 3],
      // English
      [/\b(good morning|gm|good night|gn|lunch|dinner|breakfast|coffee|weekend|tired|sleepy|weather|commute|my cat|my dog|day off|grateful|thank you|thanks everyone|\d[\d,]*\s?followers)\b/i, 2],
      [/(^|\s)(me|my boss|ai)\s?:\s/i, 3],
      [/おはよう|おやすみ|ランチ|夕食|朝食|コーヒー|退勤|出勤|週末|疲れた|天気|散歩|うちの猫|うちの犬|日常|ありがとう|フォロワー/, 2],
    ],
    news: [
      [/출시|발표|공개|속보|소식|뉴스|신버전|새\s?버전|릴리즈|도입|베타|화제|[라다][\"'”’]?고\s?(하네요|합니다|하는데|함)|했다고\s?(하네요|합니다)|발표했|공식\s?(출처|발표)/, 2],
      [/\d+\s?위\b|\d+\s?위(까지|를|에)|차트|순위/, 2], [/알고\s?보니|찾아봤|이유/, 1],
      [/\[오늘의[^\]]*소식\]|30초\s?(ai\s?)?소식/i, 4],
      // English
      [/\b(breaking|just (released|launched|announced|dropped)|announc(ed|es|ement)|released|launches|rolls? out|rolling out|now available|new (model|version|feature|update)|update:|according to|reportedly|this week in)\b/i, 2],
      [/リリース|発表|公開|速報|ニュース|新バージョン|新機能|ベータ|話題|公式発表|配信開始/, 2],
    ],
    quote: [
      [/ㅋㅋ|ㄷㄷ|미쳤|대박|실화|헐|^와\s|이게 ai|반박|😱|🤣|🥲|😂|🤪|^오\s|ㅠㅠ/i, 2],
      [/이거\s?보니|보니까|보고\s?나니|느낀\s?게|기대되|맞는\s?듯|좋겠다|소름|본\s?사람\?|부럽/, 2],
      // English
      [/\b(lol|lmao|omg|wow|insane|crazy|wild|no way|can't believe|cannot believe|mind[\s-]?blown|this is (so|insane|wild|huge)|so true|same here)\b/i, 2],
      [/やばい|すごい|まじで|マジで|草|笑った|えええ|うわ|これ見て|たまらん|やば/, 2],
    ],
  };
  function categorize(text) {
    const s = String(text || ''); const body = s.replace(/https?:\/\/\S+/g, '').trim(); if (!body) return 'etc';
    const sc = {};
    for (const [c, rs] of Object.entries(RULES)) sc[c] = rs.reduce((acc, [re, w]) => acc + (re.test(body) ? w : 0), 0);
    const lines = body.split(/\n/).filter((l) => l.trim());
    if (countList(body) >= 2) sc.guide += 3;
    if (lines.filter((l) => /^\s*[·•\-]/.test(l)).length >= 2) sc.news += 1;
    // "~했다. ~였다." 식 서술이 3문장 이상이면 썰·에세이 → 일상
    if ((body.match(/(었|았|였|했|웠|렸|졌|났|갔|왔|봤|줬|섰|됐|렀|켰)다[.,]|(이|한|는)다[.,]/g) || []).length >= 3) sc.daily += 3;
    // 길이: 한글 글은 글자 수 그대로, 영어 글은 절반으로 환산(영어가 같은 내용에 글자를 약 2배 씀)
    const cjk = (body.match(/[가-힣\u3040-\u30ff\u4e00-\u9fff]/g) || []).length; const compact = body.replace(/\s/g, '').length; const L = cjk >= compact * 0.3 ? body.length : body.length / 2;
    if (L > 160) sc.quote -= 2; else if (L < 40 && /https?:\/\//.test(s)) sc.quote += 1;
    if (/x\.com\/\w+\/status|twitter\.com\/\w+\/status/.test(s)) sc.quote += 2;
    let best = 'etc', bs = 1;
    for (const c of CATS) if ((sc[c] || 0) > bs) { best = c; bs = sc[c]; }
    return best;
  }
  XA.categorize = categorize;
  const catName = (c) => t('cat.' + c);
  XA.catName = catName;

  /* ---------- 훅 키워드 (한국어 + 영어 + 일본어). 이름은 i18n 'hook.<id>' ---------- */
  const HOOKS = [
    ['free', (s) => /무료|공짜|\bfree\b|無料|タダ/i.test(s)],
    ['summary', (s) => /정리|\b(roundup|round-up|cheat\s?sheet|summary|recap)\b|まとめ|総まとめ|要約/i.test(s)],
    ['dayN', (s) => /\d+\s*일\s*차|\b(day|week)\s*\d+\b|\d+\s*日目/i.test(s)],
    ['money', (s) => /돈|\d[\d,]*\s*(만\s*)?원|수익|비용|결제|유료|\$\s?\d|\b(money|paid|cost|price|revenue|income|subscription)\b|お金|\d[\d,]*\s*円|収益|有料|課金/i.test(s)],
    ['beforePay', (s) => /돈\s*쓰기\s*전|결제\s*전|\bbefore (you )?(pay|spend|buy|subscribe)|課金する前|お金を使う前|有料の前|買う前|購入する前/i.test(s)],
    ['prompt', (s) => /프롬프트|prompt|プロンプト/i.test(s)],
    ['list', (s) => countList(s) >= 2],
    ['nItems', (s) => /\d+\s*(곳|가지|개|선|단계)|\b\d+\s+(free\s+)?(tools|ways|tips|steps|sites|apps|things|ideas|prompts|tricks)\b|\d+\s*(選|つ|個|ステップ|件)/i.test(s)],
    ['tried', (s) => /직접\s*해|해봤|해본|\b(i tried|i tested|tried out|hands-on)\b|やってみた|試してみた|使ってみた|作ってみた/i.test(s)],
    ['cta', (s) => { const ls = s.trim().split(/\n/).filter((l) => l.trim()); const last = ls.slice(-2).join(' '); return /https?:\/\/(?!t\.co\/)|👇|프롬프트|답글에|댓글에|링크|아래|プロンプト|返信|リプ|下記|下に|保存して|\b(below|in the replies|link|prompt|reply|comments)\b/i.test(last.replace(/https?:\/\/t\.co\/\S+\s*$/, '')); }],
  ];
  XA.HOOKS = HOOKS; XA.countList = countList;

  /* ---------- 분석 ---------- */
  function analyze(rows) {
    if (rows.length < 2) throw XA.err('err.noRows');
    const headers = rows[0].map((h) => h.trim()); const map = mapColumns(headers);
    if (map.imp == null) throw XA.err('err.noImp', { cols: headers.join(', ') });
    if (map.id == null && map.text == null && map.link == null) {
      if (map.date != null && XA.analyzeOverview) return XA.analyzeOverview(rows, headers, map, num);
      throw XA.err('err.noId', { cols: headers.join(', ') });
    }
    const g = (r, k) => (map[k] != null ? r[map[k]] : undefined);
    const timeSrc = { id: 0, dateTime: 0, dateOnly: 0, none: 0, assumed: 0 };
    const posts = rows.slice(1).map((r, i) => {
      const id = String(g(r, 'id') || '').trim().replace(/^'/, '');
      let link = String(g(r, 'link') || '').trim();
      const linkId = (link.match(/status\/(\d+)/) || [])[1];
      const pid = /^\d+$/.test(id) ? id : linkId || id;
      if (!link && /^\d{10,}$/.test(pid)) link = 'https://x.com/i/status/' + pid;
      let ms = timeFromId(pid), hasTime = false;
      if (ms != null) { hasTime = true; timeSrc.id++; }
      else { const tt = timeFromDate(g(r, 'date')); if (tt) { ms = tt.ms; hasTime = tt.hasTime; tt.hasTime ? timeSrc.dateTime++ : timeSrc.dateOnly++; if (tt.assumed) timeSrc.assumed++; } else timeSrc.none++; }
      const p = { i, id: pid, link, text: String(g(r, 'text') || ''), ms, hasTime,
        imp: num(g(r, 'imp')), likes: num(g(r, 'likes')), eng: num(g(r, 'eng')), bm: num(g(r, 'bm')), shares: num(g(r, 'shares')),
        nf: num(g(r, 'nf')), rep: num(g(r, 'rep')), rt: num(g(r, 'rt')), prof: num(g(r, 'prof')), det: num(g(r, 'det')), url: num(g(r, 'url')), tag: num(g(r, 'tag')), plink: num(g(r, 'plink')) };
      if (map.eng == null) p.eng = p.likes + p.rep + p.rt + p.bm + p.shares + p.prof + p.det + p.url;
      p.er = p.imp ? p.eng / p.imp : 0; p.br = p.imp ? p.bm / p.imp : 0;
      p.isReply = isReplyText(p.text);
      p.replyTo = p.isReply ? replyHandle(p.text) : '';
      p.cat = p.isReply ? 'reply' : categorize(p.text);
      if (ms != null && hasTime) { const d = kst(ms); p.hour = d.getUTCHours(); p.dow = d.getUTCDay(); } else if (ms != null) { p.dow = kst(ms).getUTCDay(); }
      return p;
    }).filter((p) => p.imp > 0 || p.likes > 0 || p.text);
    if (!posts.length) throw XA.err('err.noPosts');
    const unmapped = headers.filter((h, i) => h && !Object.values(map).includes(i));
    return { headers, map, posts, unmapped, nReply: posts.filter((p) => p.isReply).length, timeSrc, hasText: map.text != null && posts.some((p) => p.text.trim()), hasBm: map.bm != null };
  }
  XA.num = num; XA.parseCSV = parseCSV; XA.analyze = analyze; XA.mapColumns = mapColumns; XA.timeFromId = timeFromId; XA.timeFromDate = timeFromDate;

  function agg(list) {
    const imp = sum(list.map((p) => p.imp));
    return { n: list.length, imp, medImp: median(list.map((p) => p.imp)), avgImp: avg(list.map((p) => p.imp)), avgLikes: avg(list.map((p) => p.likes)), avgBm: avg(list.map((p) => p.bm)),
      er: imp ? sum(list.map((p) => p.eng)) / imp : 0, br: imp ? sum(list.map((p) => p.bm)) / imp : 0, lr: imp ? sum(list.map((p) => p.likes)) / imp : 0, nf: sum(list.map((p) => p.nf)),
      nfr: imp ? sum(list.map((p) => p.nf)) / imp * 1e4 : 0, prof: sum(list.map((p) => p.prof)), avgProf: avg(list.map((p) => p.prof)), url: sum(list.map((p) => p.url)), withUrl: list.filter((p) => p.url > 0).length };
  }
  XA.agg = agg;

  /* ---------- 인식한 칸 표시 (X가 CSV 형식을 바꾸면 여기서 바로 보임) ---------- */
  function colInfo(map, unmapped, must) {
    const found = Object.keys(map).map((k) => t('col.' + k)).join(', ');
    const missing = must.filter((k) => map[k] == null).map((k) => t('col.' + k));
    return `${t('colinfo.found', { n: Object.keys(map).length })} ${esc(found)}` +
      (missing.length ? ` · <b>${t('colinfo.missing')} ${esc(missing.join(', '))}</b>` : ` · ${t('colinfo.missing')} ${t('colinfo.none')}`) +
      (unmapped && unmapped.length ? ` · <b>${t('colinfo.unknown')} ${esc(unmapped.join(', '))}</b>` : '');
  }
  XA.colInfo = colInfo;

  function hookRows(posts) {
    return HOOKS.map(([id, fn]) => {
      const w = posts.filter((p) => fn(p.text)), wo = posts.filter((p) => !fn(p.text));
      const a = agg(w), b = agg(wo);
      return { id, a, b, lift: b.br ? a.br / b.br : a.br ? Infinity : 0 };
    });
  }
  XA.hookRows = hookRows;

  /* ---------- 맞는 사람 찾기: 검색 링크만. 요청은 보내지 않음 ---------- */
  const HOOK_Q = {
    free: { ko: '무료', en: 'free', ja: '無料' },
    summary: { ko: '정리', en: 'roundup', ja: 'まとめ' },
    prompt: { ko: '프롬프트', en: 'prompt', ja: 'プロンプト' },
    beforePay: { ko: '결제 전', en: 'before you pay', ja: '課金する前' },
    tried: { ko: '해봤', en: 'I tried', ja: 'やってみた' },
    money: { ko: '수익', en: 'revenue', ja: '収益' },
  };
  function detectPostLang(posts) {
    let ko = 0, ja = 0, en = 0;
    (posts || []).forEach((p) => {
      const s = String(p.text || '');
      ko += (s.match(/[가-힣]/g) || []).length;
      ja += (s.match(/[\u3040-\u30ff]/g) || []).length;
      en += (s.match(/[A-Za-z]/g) || []).length;
    });
    const ranked = [['ko', ko], ['ja', ja], ['en', en]].sort((a, b) => b[1] - a[1]);
    return ranked[0][1] > 0 ? ranked[0][0] : '';
  }
  function favesFloor(posts) {
    const med = median((posts || []).map((p) => p.likes || 0));
    const n = Math.round(med);
    if (n < 5) return 5;
    if (n > 100) return 100;
    return n;
  }
  function cleanTerm(s) {
    const t = String(s || '').replace(/https?:\/\/\S+/g, ' ').replace(/[@＠#]/g, ' ').replace(/["'\\{}]/g, '').replace(/\s+/g, ' ').trim();
    if (!t || t.length < 2 || t.length > 40) return '';
    if (/filter:|min_faves:|min_retweets:|lang:|since:|until:|url:|\bfrom:|\bto:/i.test(t)) return '';
    if (/^[\d\s.]+$/.test(t)) return '';
    return t;
  }
  function quoteTerm(s) {
    const t = cleanTerm(s);
    if (!t) return '';
    return /[\s:]/.test(t) ? '"' + t + '"' : t;
  }
  function xSearchUrl(q, tab) {
    try {
      const u = new URL('https://x.com/search');
      u.searchParams.set('q', q);
      u.searchParams.set('src', 'typed_query');
      if (tab === 'user' || tab === 'live') u.searchParams.set('f', tab);
      const s = u.toString();
      return s.startsWith('https://x.com/search?') ? s : '';
    } catch (e) { return ''; }
  }
  function fittingQueries(originals, hookRowsIn, byCat, hasBm) {
    const posts = (originals || []).filter((p) => !p.isReply && String(p.text || '').trim());
    if (!posts.length) return { queries: [], lang: '', minFaves: 0, medLikes: 0, cat: '', hookId: '' };
    const lang = detectPostLang(posts);
    const medLikes = median(posts.map((p) => p.likes || 0));
    const fav = favesFloor(posts);
    const ok = (byCat || []).filter((x) => x.n >= 3 && x.c !== 'etc' && x.c !== 'reply');
    const best = ok.length ? (hasBm ? [...ok].sort((a, b) => b.br - a.br || b.n - a.n)[0] : [...ok].sort((a, b) => b.er - a.er || b.n - a.n)[0]) : null;
    let pool = best ? posts.filter((p) => p.cat === best.c) : posts;
    if (pool.length < 3) pool = posts;
    const metric = hasBm && pool.some((p) => p.bm > 0) ? 'bm' : 'likes';
    const top = [...pool].sort((a, b) => (b[metric] || 0) - (a[metric] || 0) || b.imp - a.imp).slice(0, Math.max(4, Math.ceil(pool.length * 0.4)));
    let tp = topics(top).map(cleanTerm).filter(Boolean);
    if (tp.length < 2) topics(posts).map(cleanTerm).filter(Boolean).forEach((w) => { if (!tp.some((o) => o.toLowerCase() === w.toLowerCase())) tp.push(w); });
    tp = tp.filter((w, i) => !tp.some((o, j) => j < i && (o.toLowerCase().includes(w.toLowerCase()) || w.toLowerCase().includes(o.toLowerCase())))).slice(0, 3);
    // 번호 목록·CTA처럼 검색어로 쓰기 어려운 훅은 건너뛰고, 단어가 있는 훅 중 배율이 가장 큰 것을 쓴다.
    const bestHook = (hookRowsIn || []).filter((r) => HOOK_Q[r.id] && r.a.n >= 3 && r.b.n >= 3 && isFinite(r.lift) && r.lift >= 1.2).sort((a, b) => b.lift - a.lift)[0];
    const queries = []; const seen = new Set();
    const add = (parts, why) => {
      const bits = parts.map(quoteTerm).filter(Boolean);
      if (!bits.length) return;
      let q = bits.join(' ');
      if (lang) q += ' lang:' + lang;
      q += ' min_faves:' + fav + ' -filter:replies';
      if (seen.has(q)) return;
      seen.add(q);
      const term = parts.map(cleanTerm).filter(Boolean).join(' ');
      queries.push({ term, why, q, postsUrl: xSearchUrl(q, 'live'), peopleUrl: xSearchUrl(q, 'user') });
    };
    tp.forEach((w) => add([w], 'topic'));
    if (bestHook && HOOK_Q[bestHook.id]) {
      const hw = HOOK_Q[bestHook.id][lang] || HOOK_Q[bestHook.id].en;
      if (tp[0]) add([tp[0], hw], 'hook'); else add([hw], 'hook');
    }
    return { queries: queries.slice(0, 4), lang, minFaves: fav, medLikes, cat: best ? best.c : '', hookId: bestHook ? bestHook.id : '' };
  }
  function linkBtn(href, label) {
    if (!href || !/^https:\/\/x\.com\/search\?/.test(href)) return '';
    return `<a class="btn ghost" href="${esc(href)}" target="_blank" rel="noopener">${esc(label)}</a>`;
  }
  function profileLink(handle) {
    const h = String(handle || '').replace(/[^A-Za-z0-9_]/g, '');
    if (!h) return '';
    return `<a href="https://x.com/${h}" target="_blank" rel="noopener">@${esc(h)}</a>`;
  }
  function fitHTML(A, originals, byCat) {
    if (!A.hasText) return `<p class="muted small">${t('fit.noText')}</p>`;
    const F = fittingQueries(originals, XA._hooks, byCat, A.hasBm);
    if (!F.queries.length) return `<p class="muted small">${t('fit.none')}</p>`;
    const langName = F.lang ? t('fit.lang.' + F.lang) : t('fit.lang.none');
    let html = `<p class="muted small">${t('fit.note', { lang: esc(langName), fav: String(F.minFaves), med: f1(F.medLikes) })}</p>`;
    if (F.cat) html += `<p class="muted small">${t('fit.catNote', { c: esc(catName(F.cat)) })}</p>`;
    html += '<div class="fit-list">' + F.queries.map((q) => {
      const why = q.why === 'hook' ? t('fit.why.hook', { h: esc(t('hook.' + (F.hookId || 'free'))) }) : (F.cat ? t('fit.why.topic', { c: esc(catName(F.cat)) }) : t('fit.why.topicAll'));
      return `<div class="fit-item"><div class="t from-data">${esc(q.term)}</div><p class="why">${why}</p><div class="fit-q from-data">${esc(q.q)}</div><div class="fit-links">${linkBtn(q.postsUrl, t('fit.posts'))}${linkBtn(q.peopleUrl, t('fit.people'))}</div></div>`;
    }).join('') + '</div>';
    return html;
  }

  /* ---------- 답글 대상 순위 (상관. 원인으로 읽지 않음) ---------- */
  function replyTargets(list) {
    const groups = new Map();
    (list || []).forEach((p) => {
      const raw = p.replyTo || replyHandle(p.text);
      if (!raw) return;
      const key = raw.toLowerCase();
      let g = groups.get(key);
      if (!g) { g = { handle: raw, key, n: 0, nf: 0, prof: 0, imp: 0, likes: 0 }; groups.set(key, g); }
      g.n += 1; g.nf += p.nf || 0; g.prof += p.prof || 0; g.imp += p.imp || 0; g.likes += p.likes || 0;
    });
    const rows = [...groups.values()].sort((a, b) => b.nf - a.nf || b.prof - a.prof || b.imp - a.imp || b.n - a.n || a.key.localeCompare(b.key));
    const n = sum(rows.map((r) => r.n));
    const avgNf = n ? sum(rows.map((r) => r.nf)) / n : 0;
    const avgProf = n ? sum(rows.map((r) => r.prof)) / n : 0;
    const keep = rows.filter((r) => r.n >= 2 && ((r.nf > 0 && (avgNf <= 0 || r.nf / r.n >= avgNf)) || (avgProf > 0 && r.prof > 0 && r.prof / r.n >= avgProf * 1.25)));
    const drop = rows.filter((r) => r.n >= 3 && r.nf === 0 && r.prof === 0);
    const low = rows.filter((r) => r.n >= 3 && r.nf === 0 && r.prof > 0 && (avgProf <= 0 || r.prof / r.n < avgProf));
    const watch = rows.filter((r) => r.n < 2);
    return { rows, keep, drop, low, watch, avgNf, avgProf, n, handles: rows.length };
  }
  function rtargetHTML(replies) {
    const R = replyTargets(replies);
    if (!R.rows.length) return `<p class="muted small">${t('rtarget.empty')}</p>`;
    const li = (r, key) => `<li>${profileLink(r.handle)} <span class="muted">· ${esc(t(key, { n: fmt(r.n), nf: fmt(r.nf), prof: fmt(r.prof), imp: fmt(r.imp) }))}</span></li>`;
    const card = (cls, title, body, rows, itemKey, emptyKey) => `<div class="card ${cls}"><div class="t">${esc(title)}</div><p>${body}</p>${rows.length ? `<ul class="rt-list">${rows.map((r) => li(r, itemKey)).join('')}</ul>` : `<p class="muted small">${t(emptyKey)}</p>`}</div>`;
    let html = `<p class="note">${t('rtarget.note')}</p><p class="muted small">${t('rtarget.avg', { nf: f1(R.avgNf), prof: f1(R.avgProf), h: String(R.handles), n: fmt(R.n) })}</p><div class="cards2">`;
    html += card('keep', t('rtarget.keep.h'), t('rtarget.keep.p'), R.keep, 'rtarget.keep.item', 'rtarget.noneKeep');
    html += card('drop', t('rtarget.drop.h'), t('rtarget.drop.p'), R.drop, 'rtarget.drop.item', 'rtarget.noneDrop');
    html += '</div>';
    if (R.low.length) html += `<p class="muted small">${t('rtarget.low.h')}</p><ul class="rt-list">${R.low.map((r) => li(r, 'rtarget.low.item')).join('')}</ul>`;
    if (R.watch.length) html += `<p class="muted small"><b>${esc(t('rtarget.watch.h'))}</b> ${t('rtarget.watch.p')}</p><ul class="rt-list">${R.watch.map((r) => li(r, 'rtarget.watch.item')).join('')}</ul>`;
    const th = ['handle', 'replies', 'rtNf', 'rtProf', 'rtImp', 'rtEach'].map((k) => `<th>${esc(t('th.' + k))}</th>`).join('');
    html += `<div class="tbl-wrap"><table class="tbl" id="rtarget-table"><thead><tr>${th}</tr></thead><tbody>` + R.rows.map((r) => {
      const each = r.n ? r.nf / r.n : 0;
      const mark = r.nf > 0 && r.n >= 2 ? 'hi' : (r.n >= 3 && r.nf === 0 && r.prof === 0 ? 'lo' : '');
      const small = r.n < 3 ? ` <span class="chip">${esc(t('rtarget.small'))}</span>` : '';
      return `<tr class="${r.n < 3 ? 'thin' : ''}"><td>${profileLink(r.handle)}${small}</td><td>${fmt(r.n)}</td><td class="${mark}">${fmt(r.nf)}</td><td>${fmt(r.prof)}</td><td>${fmt(r.imp)}</td><td>${f1(each)}</td></tr>`;
    }).join('') + '</tbody></table></div>';
    return html;
  }

  /* ---------- 이번 주 할 일 3개: 올린 파일의 평균과만 비교 ---------- */
  function weeklyActions(A) {
    const originals = A.posts.filter((p) => !p.isReply);
    const base = originals.length ? originals : A.posts;
    const all = agg(base);
    const byCat = CATS.map((c) => ({ c, ...agg(base.filter((p) => p.cat === c)) })).filter((x) => x.n);
    const timed = base.filter((p) => p.hour != null);
    const replies = A.posts.filter((p) => p.isReply);
    const hooks = A.hasText ? hookRows(originals.length ? originals : base) : [];
    const out = [];
    const ok = byCat.filter((x) => x.n >= 3 && x.c !== 'etc' && x.c !== 'reply');
    let best = null;
    if (A.hasText && ok.length) {
      if (A.hasBm) best = [...ok].sort((a, b) => b.br - a.br || b.nfr - a.nfr)[0];
      else if (A.map.nf != null) best = [...ok].sort((a, b) => b.nfr - a.nfr || b.er - a.er)[0];
      else best = [...ok].sort((a, b) => b.er - a.er)[0];
    }
    if (best) {
      const share = best.n / (all.n || 1);
      const useBr = !!(A.hasBm && all.br > 0);
      const mult = useBr ? best.br / all.br : (all.er > 0 ? best.er / all.er : 0);
      const nMore = share < 0.2 ? 2 : 1;
      const C = esc(catName(best.c));
      if (share >= 0.45 && mult >= 1.1) out.push({ id: 'keepcat', t: t('act.keepcat.t', { c: C }), p: t('act.keepcat.p', { c: C, share: pct(share, 0), x: mult.toFixed(1), br: pct(useBr ? best.br : best.er), all: pct(useBr ? all.br : all.er) }) });
      else if (useBr) out.push({ id: 'more', t: t('act.more.t', { c: C, n: nMore }), p: t('act.more.p', { c: C, br: pct(best.br), all: pct(all.br), x: (mult || 0).toFixed(1), share: pct(share, 0), n: nMore }) });
      else out.push({ id: 'more', t: t('act.more.t', { c: C, n: nMore }), p: t('act.more.pNoBm', { c: C, er: pct(best.er), all: pct(all.er), x: (mult || 0).toFixed(1), share: pct(share, 0), n: nMore }) });
    }
    const RT = replyTargets(replies);
    const top = RT.rows.find((r) => r.n >= 2 && r.nf > 0 && (RT.avgNf <= 0 || r.nf / r.n >= RT.avgNf));
    if (top) {
      const h = profileLink(top.handle);
      out.push({ id: 'reply', t: t('act.reply.t', { h }), p: t('act.reply.p', { h, n: fmt(top.n), nf: fmt(top.nf), prof: fmt(top.prof), each: f1(top.nf / top.n), avg: f1(RT.avgNf) }) });
    } else if (replies.length >= 3 && A.map.nf != null) {
      const rAgg = agg(replies), oAgg = agg(originals.length ? originals : base);
      const watch = RT.watch.find((r) => r.nf > 0);
      if (rAgg.nf === 0 && oAgg.nf > 0) {
        const c = best ? esc(catName(best.c)) : esc(t('series.topPosts'));
        out.push({ id: 'replyNone', t: t('act.replyNone.t'), p: t('act.replyNone.p', { rn: fmt(replies.length), rnf: fmt(rAgg.nf), on: fmt(oAgg.n), onf: fmt(oAgg.nf), c }) });
      } else if (watch) {
        const h = profileLink(watch.handle);
        out.push({ id: 'replyWatch', t: t('act.replyWatch.t', { h }), p: t('act.replyWatch.p', { h, nf: fmt(watch.nf), prof: fmt(watch.prof) }) });
      }
    }
    if (timed.length >= 8) {
      const bL = hourBlocks(timed).filter((b) => b.n >= 3).sort((a, b) => b.avgLikes - a.avgLikes || b.n - a.n)[0];
      if (bL) {
        const x = all.avgLikes > 0 ? bL.avgLikes / all.avgLikes : 0;
        out.push({ id: 'time', t: t('act.time.t', { b: esc(bL.label) }), p: t('act.time.p', { b: esc(bL.label), v: f1(bL.avgLikes), all: f1(all.avgLikes), x: x.toFixed(1) }) });
      }
    }
    const weak = ok.filter((x) => (!best || x.c !== best.c) && x.n / (all.n || 1) >= 0.1 && (A.hasBm ? all.br > 0 && x.br < all.br * 0.5 : all.er > 0 && x.er < all.er * 0.5)).sort((a, b) => (A.hasBm ? a.br - b.br : a.er - b.er))[0];
    if (A.hasText && weak) {
      const C = esc(catName(weak.c));
      const share = weak.n / (all.n || 1);
      const mult = A.hasBm ? weak.br / (all.br || 1e-9) : weak.er / (all.er || 1e-9);
      out.push({ id: 'less', t: t('act.less.t', { c: C }), p: t(A.hasBm ? 'act.less.p' : 'act.less.pNoBm', { c: C, share: pct(share, 0), br: pct(A.hasBm ? weak.br : weak.er), all: pct(A.hasBm ? all.br : all.er), x: mult.toFixed(1) }) });
    }
    const bestHook = hooks.filter((r) => r.a.n >= 3 && r.b.n >= 3 && isFinite(r.lift) && r.lift >= 1.3).sort((a, b) => b.lift - a.lift)[0];
    if (bestHook) out.push({ id: 'hook', t: t('act.hook.t', { h: esc(t('hook.' + bestHook.id)) }), p: t('act.hook.p', { h: esc(t('hook.' + bestHook.id)), a: pct(bestHook.a.br), b: pct(bestHook.b.br), x: bestHook.lift.toFixed(1), n: bestHook.a.n }) });
    if (out.length < 3) out.push({ id: 'moreData', t: t('act.moreData.t'), p: t('act.moreData.p') });
    const picked = []; const seen = new Set();
    out.forEach((a) => { if (picked.length < 3 && !seen.has(a.id)) { seen.add(a.id); picked.push(a); } });
    while (picked.length < 3) picked.push({ id: 'moreData', t: t('act.moreData.t'), p: t('act.moreData.p') });
    return picked.slice(0, 3);
  }

  /* ---------- 글 vs 그 밖 새 팔로우 (콘텐츠 합 ÷ 겹친 기간의 개요 합) ---------- */
  function kstDayKey(ms) { const d = kst(ms); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()); }
  function dayKeyStr(k) {
    if (k == null || !isFinite(k)) return '-';
    const d = new Date(k);
    return `${d.getUTCFullYear()}.${String(d.getUTCMonth() + 1).padStart(2, '0')}.${String(d.getUTCDate()).padStart(2, '0')}`;
  }
  function followShare(posts, overview) {
    if (!overview || !overview.days) return { status: 'missing' };
    if (overview.map && overview.map.nf == null) return { status: 'noNf' };
    const days = overview.days;
    const postAll = sum((posts || []).map((p) => p.nf || 0));
    const ovAll = sum(days.map((d) => d.nf || 0));
    const postDays = (posts || []).filter((p) => p.ms != null).map((p) => ({ key: kstDayKey(p.ms), nf: p.nf || 0 }));
    if (!postDays.length || !days.length) return { status: 'noDate', postAll, ovAll };
    const p0 = Math.min(...postDays.map((p) => p.key)), p1 = Math.max(...postDays.map((p) => p.key));
    const o0 = Math.min(...days.map((d) => d.key)), o1 = Math.max(...days.map((d) => d.key));
    const a = Math.max(p0, o0), b = Math.min(p1, o1);
    if (b < a) return { status: 'noOverlap', postAll, ovAll, postStart: p0, postEnd: p1, ovStart: o0, ovEnd: o1 };
    const postNf = sum(postDays.filter((p) => p.key >= a && p.key <= b).map((p) => p.nf));
    const ovDays = days.filter((d) => d.key >= a && d.key <= b);
    const ovNf = sum(ovDays.map((d) => d.nf || 0));
    const span = Math.round((b - a) / 864e5) + 1;
    const base = { postNf, ovNf, start: a, end: b, days: ovDays.length, span, postAll, ovAll };
    if (ovNf <= 0) return Object.assign({ status: 'zeroOv' }, base);
    if (postNf > ovNf) return Object.assign({ status: 'over' }, base);
    return Object.assign({ status: 'ok', share: postNf / ovNf, elsewhere: (ovNf - postNf) / ovNf }, base);
  }
  function cachedSample(name, key) {
    if (XA[key]) return XA[key];
    const s = (XA.SAMPLES || {})[name];
    if (!s) return null;
    try { XA[key] = analyze(parseCSV(s)); } catch (e) { XA[key] = null; }
    return XA[key];
  }
  function pairForContent(isSample) {
    const userOv = XA.lastOverview;
    if (userOv && userOv.mode === 'overview') {
      if (!!XA.lastOverviewSample === !!isSample) return { ov: userOv, kind: isSample ? 'sample' : 'user' };
      return { ov: null, kind: 'mismatch' };
    }
    if (isSample) { const ov = cachedSample('sample_overview.csv', '_sampleOverview'); if (ov) return { ov, kind: 'sample' }; }
    return { ov: null, kind: 'missing' };
  }
  function pairForOverview(isSample) {
    const userC = XA.lastContent;
    if (userC && userC.mode !== 'overview') {
      if (!!XA.lastContentSample === !!isSample) return { content: userC, kind: isSample ? 'sample' : 'user' };
      return { content: null, kind: 'mismatch' };
    }
    if (isSample) { const c = cachedSample('sample.csv', '_sampleContent'); if (c) return { content: c, kind: 'sample' }; }
    return { content: null, kind: 'missing' };
  }
  function followShareModel(side, isSample) {
    const pair = side === 'overview' ? pairForOverview(isSample) : pairForContent(isSample);
    if (pair.kind === 'missing' || pair.kind === 'mismatch') return { kind: pair.kind };
    const content = side === 'overview' ? pair.content : XA.lastContent;
    const ov = side === 'overview' ? XA.lastOverview : pair.ov;
    if (!content || !ov) return { kind: 'missing' };
    if (content.map.nf == null || ov.map.nf == null) return { kind: 'noNf' };
    const stat = followShare(content.posts, ov);
    stat.kind = stat.status;
    stat.pairKind = pair.kind;
    return stat;
  }
  function followShareInner(side, isSample) {
    const m = followShareModel(side, isSample);
    if (m.kind === 'missing') return `<p class="muted small">${t('fsrc.missing')}</p>`;
    if (m.kind === 'mismatch') return `<p class="note">${t('fsrc.mismatch')}</p>`;
    if (m.kind === 'noNf' || m.status === 'noNf') return `<p class="muted small">${t('fsrc.noNf')}</p>`;
    const src = m.pairKind === 'sample' ? t('fsrc.sample') : t('fsrc.both');
    if (m.status === 'noDate') return `<p class="muted small">${src}</p><p class="muted small">${t('fsrc.noDate')}</p>`;
    if (m.status === 'noOverlap') return `<p class="muted small">${src}</p><p class="muted small">${t('fsrc.noOverlap', { a: esc(dayKeyStr(m.postStart)), b: esc(dayKeyStr(m.postEnd)), c: esc(dayKeyStr(m.ovStart)), d: esc(dayKeyStr(m.ovEnd)) })}</p>`;
    if (m.status === 'zeroOv') return `<p class="muted small">${src} ${t('fsrc.period', { a: esc(dayKeyStr(m.start)), b: esc(dayKeyStr(m.end)), d: fmt(m.span) })}</p><p class="muted small">${t('fsrc.zeroOv', { p: fmt(m.postNf) })}</p>`;
    const grid = (share, elsewhere) => `<div class="fsrc-grid"><div class="fsrc"><div class="k">${esc(t('fsrc.share'))}</div><div class="v">${share}</div><div class="s">${esc(t('fsrc.shareSub', { p: fmt(m.postNf), o: fmt(m.ovNf) }))}</div></div><div class="fsrc"><div class="k">${esc(t('fsrc.else'))}</div><div class="v">${elsewhere}</div><div class="s">${esc(t('fsrc.elseSub'))}</div></div><div class="fsrc"><div class="k">${esc(t('fsrc.periodK'))}</div><div class="v">${esc(t('unit.days', { n: fmt(m.span) }))}</div><div class="s">${esc(dayKeyStr(m.start))} ~ ${esc(dayKeyStr(m.end))}</div></div></div>`;
    if (m.status === 'over') return `<p class="muted small">${src}</p>${grid('–', '–')}<p class="note">${t('fsrc.over', { p: fmt(m.postNf), o: fmt(m.ovNf) })}</p>`;
    return `<p class="muted small">${t('fsrc.note')}</p><p class="muted small">${src}</p>${grid(esc(pct(m.share, 0)), esc(pct(m.elsewhere, 0)))}<p class="muted small">${t('fsrc.caveat')}</p>`;
  }

  XA.detectPostLang = detectPostLang;
  XA.favesFloor = favesFloor;
  XA.xSearchUrl = xSearchUrl;
  XA.fittingQueries = fittingQueries;
  XA.replyTargets = replyTargets;
  XA.weeklyActions = weeklyActions;
  XA.followShare = followShare;
  XA.followShareInner = followShareInner;
  XA.pairForContent = pairForContent;
  XA.pairForOverview = pairForOverview;
  XA.cleanTerm = cleanTerm;

  /* ---------- 렌더링 ---------- */
  function render(A, isSample, keepScroll) {
    XA._isSample = isSample;
    const inc = !!XA.includeReplies;
    const O = A.posts.filter((p) => !p.isReply), RP = A.posts.filter((p) => p.isReply);
    const P = inc || !O.length ? A.posts : O; const all = agg(P); const allO = agg(O.length ? O : A.posts);
    $('#results').hidden = false; $('#sample-banner').hidden = !isSample;
    $('#col-info').innerHTML = colInfo(A.map, A.unmapped, ['text', 'bm', 'eng', 'likes']) + ` <span class="hint">${t('colinfo.hint')}</span>`;
    // 답글 요약 + 토글
    const rb = $('#reply-box');
    if (RP.length) {
      const r = agg(RP);
      rb.hidden = false;
      rb.innerHTML = `<div>${t('reply.head', { n: fmt(RP.length), total: fmt(A.posts.length), share: pct(RP.length / A.posts.length, 0) })}</div>
        <div class="small">${t('reply.stats', { avg: fmt(r.avgImp), med: fmt(r.medImp), likes: f1(r.avgLikes), nf: fmt(r.nf), prof: fmt(r.prof), no: fmt(O.length), oavg: fmt(allO.avgImp), omed: fmt(allO.medImp), olikes: f1(allO.avgLikes) })}</div>
        <label class="tgl"><input type="checkbox" id="inc-replies" ${inc ? 'checked' : ''}> ${t('reply.toggle')} <span class="muted small">${t('reply.toggleNote')}</span></label>`;
      $('#inc-replies').onchange = (e) => { XA.includeReplies = e.target.checked; render(A, isSample, true); };
    } else { rb.hidden = true; rb.innerHTML = ''; }

    const times = P.filter((p) => p.ms != null).map((p) => p.ms);
    const period = times.length ? `${kstStr(Math.min(...times))} ~ ${kstStr(Math.max(...times))}` : '';
    const K = [[inc ? t('kpi.postsInc') : (RP.length ? t('kpi.originals') : t('kpi.posts')), t('unit.posts', { n: fmt(all.n) }), period],
      [t('kpi.imp'), fmt(all.imp), t('kpi.avg', { v: fmt(all.avgImp) })], [t('kpi.medImp'), fmt(all.medImp), t('kpi.medImpSub')],
      [t('kpi.er'), pct(all.er), t('kpi.erSub')], [t('kpi.br'), A.hasBm ? pct(all.br) : '-', A.hasBm ? t('kpi.brSub', { v: f1(all.avgBm) }) : t('kpi.noBm')], [t('kpi.likes'), f1(all.avgLikes), t('kpi.likesSub', { v: pct(all.lr) })]];
    if (A.map.nf != null) K.push([t('kpi.nfr'), t('unit.people', { n: f1(all.nfr) }), t('kpi.nfrSub', { n: fmt(all.nf) })]);
    if (A.map.prof != null) K.push([t('kpi.prof'), fmt(all.prof), t('kpi.profSub', { v: f1(all.avgProf) }) + (all.prof ? ' · ' + t('kpi.profConv', { v: pct(all.nf / all.prof, 1) }) : '')]);
    if (A.map.url != null && all.url > 0) K.push([t('kpi.url'), fmt(all.url), t('kpi.urlSub', { n: all.withUrl })]);
    $('#summary').innerHTML = K.map(([k, v, s]) => `<div class="kpi"><div class="k">${esc(k)}</div><div class="v">${esc(v)}</div><div class="s">${esc(s)}</div></div>`).join('');

    // 카테고리
    const byCat = [...CATS, 'reply'].map((c) => ({ c, ...agg(P.filter((p) => p.cat === c)) })).filter((x) => x.n);
    const byCatO = byCat.filter((x) => x.c !== 'reply');
    const hasNf = A.map.nf != null, hasProf = A.map.prof != null;
    const maxNfr = Math.max(...byCatO.filter((x) => x.n >= 3).map((x) => x.nfr), 0);
    const maxBr = Math.max(...byCatO.map((x) => x.br)), maxMed = Math.max(...byCatO.map((x) => x.medImp)), maxEr = Math.max(...byCatO.map((x) => x.er));
    if (A.hasText) {
      const th = ['cat', 'n', 'share', 'medImp', 'avgLikes', 'avgBm', 'er', 'br'].map((k) => `<th>${t('th.' + k)}</th>`).join('') + (hasNf ? `<th>${t('th.nfr')}</th>` : '') + (hasProf ? `<th>${t('th.prof')}</th>` : '');
      $('#cat-table').innerHTML = `<thead><tr>${th}</tr></thead><tbody>` +
        byCat.map((x) => `<tr><td>${esc(catName(x.c))}</td><td>${x.n}</td><td>${pct(x.n / all.n, 0)}</td><td class="${x.medImp === maxMed ? 'hi' : ''}">${fmt(x.medImp)}</td><td>${f1(x.avgLikes)}</td><td>${f1(x.avgBm)}</td><td class="${x.er === maxEr ? 'hi' : x.er < all.er * 0.3 ? 'lo' : ''}">${pct(x.er)}</td><td class="${x.br === maxBr ? 'hi' : ''}">${pct(x.br)}</td>${hasNf ? `<td class="${x.n >= 3 && x.nfr === maxNfr && x.c !== 'reply' ? 'hi' : ''}">${f1(x.nfr)}</td>` : ''}${hasProf ? `<td>${f1(x.avgProf)}</td>` : ''}</tr>`).join('') + '</tbody>';
      $('#cat-chart').innerHTML = barChart(byCatO.map((x) => ({ label: catName(x.c), v: x.br, sub: t('unit.posts', { n: x.n }) })), t('chart.br'), (v) => pct(v)) +
        barChart(byCatO.map((x) => ({ label: catName(x.c), v: x.medImp, sub: '' })), t('chart.medImp'), fmt, '#94a3b8') +
        (hasNf ? barChart(byCatO.map((x) => ({ label: catName(x.c), v: x.nfr, sub: '' })), t('chart.nfr'), (v) => t('unit.people', { n: f1(v) }), '#f97316') : '');
    } else {
      $('#cat-table').innerHTML = `<tbody><tr><td>${t('cat.noText')}</td></tr></tbody>`;
      $('#cat-chart').innerHTML = `<p class="muted small">${t('cat.noTextChart')}</p>`;
    }

    // 랭킹
    const rank = () => {
      const m = $('#rank-metric').value; const key = { imp: 'imp', likes: 'likes', bm: 'bm', er: 'er', nf: 'nf', prof: 'prof' }[m] || 'imp';
      const sorted = [...P].sort((a, b) => b[key] - a[key]);
      const cutoff = Date.now() - 2 * 864e5;
      const bottomPool = sorted.filter((p) => !(p.ms != null && p.ms > cutoff) && (m !== 'er' || p.imp >= 50));
      $('#top5').innerHTML = sorted.slice(0, 5).map(li).join('');
      $('#bottom5').innerHTML = bottomPool.slice(-5).reverse().map(li).join('') + `<p class="muted small">${t('rank.recentNote')}</p>`;
    };
    const li = (p) => `<li><div class="txt">${esc(p.text.trim() || t('rank.noText', { id: p.id }))}</div><div class="meta">${A.hasText ? `<span class="chip">${esc(catName(p.cat))}</span>` : ''}${t('rank.meta', { imp: fmt(p.imp), likes: fmt(p.likes), bm: fmt(p.bm), er: pct(p.er, 1) })}${p.nf ? ' · ' + t('rank.nf', { n: fmt(p.nf) }) : ''}${p.prof ? ' · ' + t('rank.prof', { n: fmt(p.prof) }) : ''}${p.ms != null ? ' · ' + kstStr(p.ms, p.hasTime) : ''}${p.link ? ` · <a href="${esc(p.link)}" target="_blank" rel="noopener">${t('rank.view')}</a>` : ''}</div></li>`;
    $('#rank-metric').onchange = rank; rank();

    // 히트맵
    const timed = P.filter((p) => p.hour != null); const timedO = O.filter((p) => p.hour != null);
    const ts = A.timeSrc;
    $('#time-src').textContent = ts.id ? t('heat.srcId', { all: ts.id, n: timed.length }) + (!inc && RP.length ? t('heat.srcNoReply') : '') : ts.dateTime ? t('heat.srcDate') + (ts.assumed ? t('heat.srcAssumed') : '') : '';
    const heat = () => {
      if (!timed.length) { $('#heatmap').innerHTML = `<p class="muted small">${t('heat.none')}</p>`; $('#hour-blocks').innerHTML = ''; return; }
      const m = $('#heat-metric').value; const cell = {};
      timed.forEach((p) => { const k = p.dow + '-' + p.hour; (cell[k] = cell[k] || []).push(p); });
      const val = (l) => (m === 'n' ? l.length : m === 'likes' ? avg(l.map((p) => p.likes)) : avg(l.map((p) => p.imp)));
      const vals = Object.values(cell).map(val); const mx = Math.max(...vals, 1);
      let h = '<div class="heat"><div></div>' + Array.from({ length: 24 }, (_, i) => `<div class="h">${i}</div>`).join('');
      DAY_ORDER.forEach((d) => {
        h += `<div class="d">${day(d)}</div>`;
        for (let hr = 0; hr < 24; hr++) {
          const l = cell[d + '-' + hr];
          if (!l) { h += `<div class="c" title="${esc(t('heat.cellEmpty', { d: day(d), h: hr }))}"></div>`; continue; }
          const v = val(l); const a = 0.15 + 0.85 * (v / mx);
          h += `<div class="c" data-n="${l.length}" style="background:rgba(79,70,229,${a.toFixed(2)})" title="${esc(t('heat.cell', { d: day(d), h: hr, n: l.length, likes: f1(avg(l.map((p) => p.likes))), imp: fmt(avg(l.map((p) => p.imp))) }))}">${l.length > 1 ? l.length : ''}</div>`;
        }
      });
      h += `</div><div class="legend">${t('heat.less')} <i style="background:rgba(79,70,229,.15)"></i><i style="background:rgba(79,70,229,.5)"></i><i style="background:rgba(79,70,229,1)"></i> ${t('heat.more')}</div>`;
      $('#heatmap').innerHTML = h;
      const blocks = hourBlocks(timed);
      $('#hour-blocks').innerHTML = barChart(blocks.map((b) => ({ label: b.label, v: b.avgLikes, sub: t('unit.posts', { n: b.n }) })), t('chart.hourLikes'), f1) + barChart(blocks.map((b) => ({ label: b.label, v: b.medImp, sub: '' })), t('chart.hourImp'), fmt, '#94a3b8');
    };
    $('#heat-metric').onchange = heat; heat();

    // 훅 (제안·맞는 사람 찾기·이번 주 할 일이 같이 씀)
    const hookBase = O.length ? O : P;
    XA._hooks = A.hasText ? hookRows(hookBase) : null;
    if (XA._hooks) {
      $('#hook-table').innerHTML = `<thead><tr>${['hook', 'used', 'hookImp', 'hookLikes', 'hookBr', 'lift'].map((k) => `<th>${t('th.' + k)}</th>`).join('')}</tr></thead><tbody>` +
        XA._hooks.map((r) => `<tr><td>${esc(t('hook.' + r.id))}</td><td>${r.a.n}</td><td>${r.a.n ? fmt(r.a.medImp) : '-'} / ${fmt(r.b.medImp)}</td><td>${r.a.n ? f1(r.a.avgLikes) : '-'} / ${f1(r.b.avgLikes)}</td><td>${r.a.n ? pct(r.a.br) : '-'} / ${pct(r.b.br)}</td><td class="${r.a.n >= 3 && r.lift >= 1.5 ? 'hi' : r.a.n >= 3 && r.lift < 0.7 ? 'lo' : ''}">${r.a.n ? (isFinite(r.lift) ? t('unit.times', { n: r.lift.toFixed(1) }) : '∞') : '-'}${r.a.n && r.a.n < 3 ? ` <span class="muted small">${t('hook.small')}</span>` : ''}</td></tr>`).join('') + '</tbody>';
    } else $('#hook-table').innerHTML = `<tbody><tr><td>${t('hook.noText')}</td></tr></tbody>`;

    // 제안 & 시리즈
    const S = suggestions(A, allO, byCatO, timedO, O.length ? O : A.posts);
    $('#suggest').innerHTML = S.sug.map((s) => `<div class="card sug"><div class="t">${s.t}</div><p>${s.p}</p></div>`).join('');
    $('#series').innerHTML = S.series.map((s, i) => `<div class="card ser"><div class="n">${t('series.n', { n: i + 1 })}</div><div class="t">${s.t}</div><p>${s.p}</p></div>`).join('');

    const actions = weeklyActions(A);
    const actBox = $('#actions');
    if (actBox) actBox.innerHTML = actions.map((s, i) => `<div class="action" data-act="${esc(s.id)}"><div class="n">${esc(t('act.n', { n: i + 1 }))}</div><div class="t">${s.t}</div><p>${s.p}</p></div>`).join('');
    const fsBox = $('#follow-src');
    if (fsBox) fsBox.innerHTML = followShareInner('content', isSample);
    const fitBox = $('#fit');
    if (fitBox) fitBox.innerHTML = fitHTML(A, hookBase, byCatO);
    const rtBox = $('#rtarget');
    if (rtBox) rtBox.innerHTML = rtargetHTML(RP);
    if (!keepScroll) $('#results').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function hourBlocks(timed) {
    const B = [[0, 6], [6, 9], [9, 13], [13, 17], [17, 20], [20, 24]];
    return B.map(([a, b]) => { const l = timed.filter((p) => p.hour >= a && p.hour < b); return { label: t('hourBlock', { a: String(a).padStart(2, '0'), b: String(b - 1).padStart(2, '0') }), a, b, n: l.length, avgLikes: avg(l.map((p) => p.likes)), medImp: median(l.map((p) => p.imp)), avgImp: avg(l.map((p) => p.imp)) }; });
  }
  XA.hourBlocks = hourBlocks;

  // 소재 추출: 소재 사전 우선, 없으면 자주 나온 단어(2회 이상)
  const TOPIC_DICT = ['AI 이미지', 'AI 영상', 'AI 음악', '이미지 생성', '썸네일', '자막', '폰트', '로고', '블로그', '노션', '쇼츠', '자동화', '부업', 'N잡', '디자인', '코딩', '엑셀', '제품 사진', '굿즈', '웹툰', '동화책', '팟캐스트', '음성', '캐릭터', '인스타', '유튜브', '챗GPT', 'GPT', '클로드', '미드저니', '제미나이', '그록', '커서', '바이브코딩', '업스케일', '배경 제거', '무료 크레딧', '콘텐츠 캘린더', '사진', '영상', '음악', '이미지',
    'AI image', 'AI video', 'AI music', 'image generation', 'thumbnail', 'subtitles', 'captions', 'font', 'logo', 'blog', 'Notion', 'Shorts', 'automation', 'side hustle', 'design', 'coding', 'Excel', 'product photo', 'merch', 'webtoon', 'podcast', 'voice', 'character', 'Instagram', 'YouTube', 'ChatGPT', 'Claude', 'Midjourney', 'Gemini', 'Cursor', 'vibe coding', 'upscale', 'background removal', 'free credits', 'content calendar', 'newsletter', 'photo', 'video', 'music', 'image',
    'AI画像', 'AI動画', 'AI音楽', '画像生成', 'サムネイル', '字幕', 'フォント', 'ロゴ', 'ブログ', 'ショート', '自動化', '副業', 'デザイン', 'コーディング', '物撮り', 'グッズ', 'ウェブトゥーン', 'ポッドキャスト', '音声', 'キャラクター', 'インスタ', 'バイブコーディング', 'アップスケール', '背景除去', '無料クレジット', 'コンテンツカレンダー', 'ニュースレター', '写真', '動画', '音楽', '画像'];
  const EN_STOP = new Set('this that with from your have just what when they them then than there their about into will would could should more most very really here also only some like make made using used use been were was are the and for you not but all can get got how why who our out one two new now today week day time post posts thread free tools tool link prompt below best first last next every still even much many need want know think going look best'.split(' '));
  function topics(list) {
    const txt = list.map((p) => p.text.replace(/https?:\/\/\S+/g, ' ')).join('\n');
    const dict = TOPIC_DICT.map((w) => [w, (txt.match(new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')) || []).length]).filter((x) => x[1] > 0).sort((a, b) => b[1] - a[1]).map((x) => x[0]);
    const out = dict.filter((w, i) => !dict.some((o, j) => j < i && (o.toLowerCase().includes(w.toLowerCase()) || w.toLowerCase().includes(o.toLowerCase()))));
    const stop = /^(이거|이건|이게|그냥|진짜|너무|오늘|그리고|저는|제가|여러분|이번|다음|아래|정리|무료|링크|답글|저장|기준|추천|방법|직접|요즘|하나|생각|정말|완전|결과|시간|하루|만들|해보|써보)/;
    const c = {};
    (txt.match(/[가-힣A-Za-z][가-힣A-Za-z0-9]{1,9}/g) || []).forEach((w) => {
      if (/^[A-Za-z0-9]+$/.test(w)) { if (w.length < 4 || EN_STOP.has(w.toLowerCase())) return; c[w] = (c[w] || 0) + 1; return; }
      w = w.replace(/(으로|에서|까지|부터|이랑|하고|해서|은|는|이|가|을|를|에|의|도|로|과|와)$/, ''); if (w.length < 2 || stop.test(w) || /(다|요|음|함|게|고|서|면|죠|네|해|임)$/.test(w)) return; c[w] = (c[w] || 0) + 1;
    });
    const freq = Object.entries(c).filter((x) => x[1] >= 2).sort((a, b) => b[1] - a[1]).map((x) => x[0]).filter((w) => !out.some((o) => o.toLowerCase().includes(w.toLowerCase()) || w.toLowerCase().includes(o.toLowerCase())));
    return [...out, ...freq];
  }

  /* 제안: 전부 업로드한 사람 자신의 평균과 비교 (고정 기준치 없음) */
  function suggestions(A, all, byCat, timed, P) {
    const sug = []; const series = [];
    const ok = byCat.filter((x) => x.n >= 3 && x.c !== 'etc' && x.c !== 'reply');
    const bestBr = [...ok].sort((a, b) => b.br - a.br)[0];
    const bestImp = [...ok].sort((a, b) => b.medImp - a.medImp)[0];
    const C = (x) => esc(catName(x.c));
    if (A.hasText && bestBr && A.hasBm) sug.push({ t: t('sug.save.t', { c: C(bestBr) }), p: t('sug.save.p', { br: pct(bestBr.br), all: pct(all.br), x: (bestBr.br / (all.br || 1e-9)).toFixed(1), bm: f1(bestBr.avgBm), share: pct(bestBr.n / all.n, 0) }) });
    if (A.hasText && bestImp && bestImp.er < all.er * 0.5) sug.push({ t: t('sug.reach.t', { c: C(bestImp) }), p: t('sug.reach.p', { med: fmt(bestImp.medImp), er: pct(bestImp.er), all: pct(all.er) }) });
    const weak = ok.filter((x) => x !== bestBr && x.n / all.n >= 0.1 && x.br < all.br * 0.4).sort((a, b) => b.n - a.n)[0];
    if (A.hasText && weak && sug.length < 3) sug.push({ t: t('sug.weak.t', { c: C(weak) }), p: t('sug.weak.p', { share: pct(weak.n / all.n, 0), br: pct(weak.br), all: pct(all.br) }) });
    if (timed.length >= 10) {
      const bl = hourBlocks(timed).filter((b) => b.n >= 3);
      const bL = [...bl].sort((a, b) => b.avgLikes - a.avgLikes)[0], wI = [...bl].sort((a, b) => a.medImp - b.medImp)[0];
      if (bL) sug.push({ t: t('sug.time.t', { b: bL.label }), p: t('sug.time.p', { v: f1(bL.avgLikes), all: f1(all.avgLikes) }) + (wI && wI !== bL ? ' ' + t('sug.time.p2', { b: wI.label, v: fmt(wI.medImp) }) : '') + ' ' + t('sug.time.p3', { b: bL.label }) });
    }
    if (A.map.nf != null && all.nf > 0) {
      const fc = ok.filter((x) => x.nf >= 2).sort((a, b) => b.nfr - a.nfr)[0];
      const byImp = [...P].sort((a, b) => b.imp - a.imp); const k = Math.max(3, Math.round(P.length * 0.1));
      const topA = agg(byImp.slice(0, k)), restA = agg(byImp.slice(k));
      const topBy = [...P].sort((a, b) => b.nf - a.nf)[0];
      if (fc) sug.push({ t: t('sug.follow.t', { c: C(fc) }), p: t('sug.follow.p', { v: f1(fc.nfr), all: f1(all.nfr), prof: f1(fc.avgProf) }) +
        (topA.nfr < restA.nfr * 0.7 ? ' ' + t('sug.follow.p2', { k, a: f1(topA.nfr), b: f1(restA.nfr) }) : '') +
        (topBy && topBy.nf ? ' ' + t('sug.follow.p3', { n: fmt(topBy.nf), imp: fmt(topBy.imp) }) : '') });
    }
    let bestHook = null;
    if (A.hasText && XA._hooks) {
      bestHook = XA._hooks.filter((r) => r.a.n >= 3 && r.b.n >= 3 && isFinite(r.lift) && r.lift >= 1.3).sort((a, b) => b.lift - a.lift)[0];
      if (bestHook && sug.length < 5) sug.push({ t: t('sug.hook.t', { h: esc(t('hook.' + bestHook.id)) }), p: t('sug.hook.p', { a: pct(bestHook.a.br), b: pct(bestHook.b.br), x: bestHook.lift.toFixed(1), n: bestHook.a.n }) });
    }
    if (sug.length < 3) sug.push({ t: t('sug.more.t'), p: t('sug.more.p') });

    // 시리즈 아이디어 (내 데이터 기반)
    const bestCatPosts = bestBr ? P.filter((p) => p.cat === bestBr.c) : P;
    const topBm = [...bestCatPosts].sort((a, b) => b.bm - a.bm).slice(0, 10);
    const tp = topics(topBm.length ? topBm : P); const t1 = tp[0] || t('series.myField');
    const tpE = topics(P.filter((p) => p.cat === 'exp')).filter((w) => w !== t1); const t2 = tpE[0] || tp[1] || t1;
    const t3 = tp.find((w) => w !== t1 && w !== t2) || t1;
    const bl = timed.length >= 10 ? hourBlocks(timed).filter((b) => b.n >= 3).sort((a, b) => b.avgLikes - a.avgLikes)[0] : null;
    const dayC = {}; timed.forEach((p) => (dayC[p.dow] = dayC[p.dow] || []).push(p.likes));
    const bestDay = Object.entries(dayC).filter(([, l]) => l.length >= 3).sort((a, b) => avg(b[1]) - avg(a[1]))[0];
    const when = bestDay ? t('series.whenDay', { d: t('dayFull.' + bestDay[0]), b: bl ? bl.label : t('series.afternoon') }) : t('series.when', { b: bl ? bl.label : t('series.afternoon') });
    const hookId = bestHook && ['free', 'beforePay', 'prompt'].includes(bestHook.id) ? bestHook.id : 'free';
    series.push({ t: t('series.1.t', { h: esc(t('serhook.' + hookId)), topic: esc(t1) }), p: t('series.1.p', { c: esc(bestBr ? catName(bestBr.c) : t('series.topPosts')), topic: esc(t1), when }) });
    const exp = byCat.find((x) => x.c === 'exp');
    series.push(exp ? { t: t('series.2.t', { topic: esc(t2) }), p: t('series.2.p', { n: exp.n, br: pct(exp.br), all: pct(all.br) }) } : { t: t('series.2.t', { topic: esc(t2) }), p: t('series.2.p0') });
    const news = byCat.find((x) => x.c === 'news'), quote = byCat.find((x) => x.c === 'quote');
    const what = [news ? t('series.3.news', { br: pct(news.br) }) : '', quote ? t('series.3.quote', { er: pct(quote.er) }) : ''].filter(Boolean).join(' · ');
    series.push({ t: t('series.3.t', { topic: esc(t3) }), p: what ? t('series.3.p', { what }) : t('series.3.p0') });
    return { sug: sug.slice(0, 5), series };
  }

  /* ---------- SVG 가로 막대 차트 ---------- */
  function barChart(items, title, f, color = '#4f46e5') {
    const W = 520, rowH = 26, lw = 150, top = 26, H = top + items.length * rowH + 6; const mx = Math.max(...items.map((x) => x.v), 1e-9);
    let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" role="img" aria-label="${esc(title)}" style="display:inline-block;vertical-align:top;margin:0 8px 8px 0"><text x="0" y="16" font-size="13" font-weight="700" fill="#14171a">${esc(title)}</text>`;
    items.forEach((x, i) => { const y = top + i * rowH; const w = Math.max(2, (W - lw - 100) * (x.v / mx));
      s += `<text x="0" y="${y + 16}" font-size="12" fill="#334155">${esc(x.label)}</text><rect x="${lw}" y="${y + 4}" width="${w.toFixed(1)}" height="16" rx="4" fill="${color}"/><text x="${lw + w + 6}" y="${y + 16}" font-size="12" fill="#14171a">${esc(f(x.v))}${x.sub ? ' · ' + esc(x.sub) : ''}</text>`; });
    return s + '</svg>';
  }
  XA.barChart = barChart;

  /* ---------- 파일 입력 ---------- */
  let lastErr = null;
  function showErr(e) {
    lastErr = e || null; const box = $('#csv-error');
    if (!e) { box.textContent = ''; box.hidden = true; return; }
    box.textContent = '😢 ' + (e.key ? t(e.key, e.params) : e.message); box.hidden = false;
    $('#results').hidden = true; const o = $('#overview'); if (o) o.hidden = true;
  }
  function handleText(text, isSample) {
    showErr(null);
    try {
      const A = analyze(parseCSV(text)); XA.last = A; XA._isSample = isSample; XA.includeReplies = false;
      if (A.mode === 'overview') {
        XA.lastOverview = A; XA.lastOverviewSample = !!isSample;
        $('#results').hidden = true; XA.renderOverview(A, isSample);
      } else {
        XA.lastContent = A; XA.lastContentSample = !!isSample;
        const o = $('#overview'); if (o) o.hidden = true; render(A, isSample);
      }
    }
    catch (e) { console.warn(e); showErr(e); }
  }
  XA.handleText = handleText;
  function readFile(f) {
    if (!f) return; if (f.size > 30 * 1024 * 1024) return showErr(XA.err('err.tooBig'));
    const r = new FileReader();
    r.onload = () => { const s = r.result; if ((s.match(/\uFFFD/g) || []).length > 5) { const r2 = new FileReader(); r2.onload = () => handleText(r2.result, false); r2.readAsText(f, 'euc-kr'); } else handleText(s, false); };
    r.readAsText(f, 'utf-8');
  }
  const drop = $('#drop'), file = $('#file');
  drop.addEventListener('click', () => file.click());
  drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); file.click(); } });
  file.addEventListener('change', () => { readFile(file.files[0]); file.value = ''; });
  ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', (e) => readFile(e.dataTransfer.files[0]));
  // 샘플: fetch 없이 samples.js에 내장된 문자열 사용 (file:// 에서도 동작)
  document.querySelectorAll('[data-sample]').forEach((btn) => btn.addEventListener('click', () => {
    const s = (XA.SAMPLES || {})[btn.dataset.sample];
    if (!s) return showErr(XA.err('err.sample'));
    handleText(s, true);
  }));

  // 언어가 바뀌면 지금 보고 있는 결과를 새 언어로 다시 그림
  document.addEventListener('langchange', () => {
    if (lastErr) showErr(lastErr);
    if (!XA.last) return;
    if (XA.last.mode === 'overview') { if (!$('#overview').hidden) XA.renderOverview(XA.last, XA._isSample, true); }
    else if (!$('#results').hidden) render(XA.last, XA._isSample, true);
  });
})();
