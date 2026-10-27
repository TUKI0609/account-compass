"""자동 테스트 (Playwright + 로컬 서버 + file://).
- 샘플 로드 / 파서 변형(한국어·영어·일본어·구 Tweet activity) / 영어 헤더 / 영어 카테고리 규칙
- i18n: ko 키가 전부 en·ja에 있음, 화면에 쓰는 키가 전부 사전에 있음, 언어 토글·저장·<html lang>
- 헤더: 언어 선택기(한국어/English/日本語)가 로고와 탭 사이, 제작자 표시가 1280·1440·1024·390에서 잘리지 않음
- 실제 데이터 흔적 없음(소유자 이름은 제작자 표시에만), file:// 동작, 외부 요청 없음
- v2 스크린샷(가상 샘플 데이터만) → screenshots/v2_*.png
실제 파일 회귀 테스트(선택): REAL_CONTENT=/path REAL_OVERVIEW=/path  — 실제 파일은 스크린샷을 찍지 않음.
실행: .venv/bin/python tools/test.py   (x-analyzer 폴더 또는 그 상위 폴더에서)"""
import subprocess, time, sys, json, os, re, glob, struct
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = f'{ROOT}/screenshots'
os.makedirs(SHOT, exist_ok=True)
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8765', '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
URL = 'http://127.0.0.1:8765/'
FILE_URL = 'file://' + ROOT + '/index.html'
fails = []
def check(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)
def header_box(page):
    return page.evaluate("""() => {
      const c = document.querySelector('.topbar .credit');
      const a = document.querySelector('.topbar .credit-btn');
      const lang = document.querySelector('.top-in [data-lang-toggle]');
      const brand = document.querySelector('.brand');
      const tabs = document.querySelector('.tabs, .back-link');
      const cr = c.getBoundingClientRect();
      const ar = a.getBoundingClientRect();
      const lr = lang.getBoundingClientRect();
      const br = brand.getBoundingClientRect();
      const tr = tabs.getBoundingClientRect();
      const hs = c.querySelector('.handle');
      const hr = hs.getBoundingClientRect();
      const hit = document.elementFromPoint(ar.left + ar.width / 2, ar.top + ar.height / 2);
      return {
        vw: innerWidth, sw: document.documentElement.scrollWidth,
        fs: parseFloat(getComputedStyle(c).fontSize),
        cl: cr.left, cr: cr.right, ct: cr.top, ch: cr.height,
        al: ar.left, aright: ar.right, aw: ar.width, ah: ar.height,
        href: a.href, target: a.target, rel: a.rel,
        hit: !!(hit && (hit === a || a.contains(hit))),
        hl: hr.left, hr: hr.right, htext: hs.textContent,
        ll: lr.left, lrgt: lr.right, lw: lr.width, lh: lr.height,
        brnd: br.right, tl: tr.left, tb: tr.bottom,
        labels: [...lang.querySelectorAll('button')].map(b => b.textContent),
        cred: c.innerText.replace(/\\s+/g, ' ').trim()
      };
    }""")
def check_header(page, label, mobile=False):
    m = header_box(page)
    check(m['sw'] <= m['vw'] + 1, f'{label} 가로 넘침 없음 (scrollWidth {m["sw"]} / {m["vw"]})')
    inside = (m['cl'] >= -1 and m['cr'] <= m['vw'] + 1 and m['hl'] >= -1 and m['hr'] <= m['vw'] + 1
              and m['al'] >= -1 and m['aright'] <= m['vw'] + 1 and m['ll'] >= -1 and m['lrgt'] <= m['vw'] + 1)
    check(inside and m['htext'] == '@Ty_Tuki0609' and m['aw'] > 8 and m['hit'],
          f'{label} 제작자·프로필 버튼이 화면 안에 다 보임 { {k: round(m[k], 1) if isinstance(m[k], float) else m[k] for k in ["cl", "cr", "hl", "hr", "al", "aright", "vw", "htext", "hit", "aw"]} }')
    check(m['fs'] <= 12.5 and m['lw'] > 80 and m['lh'] >= 20 and m['labels'] == ['한국어', 'English', '日本語'],
          f'{label} 언어 선택기 {m["labels"]} {m["fs"]}px {m["lw"]:.0f}x{m["lh"]:.0f}')
    if mobile:
        check(m['ch'] <= 32 and m['tb'] < 170, f'{label} 모바일 헤더 높이 credit={m["ch"]:.0f} tabsBottom={m["tb"]:.0f}')
    else:
        mid = (m['ll'] + m['lrgt']) / 2
        check(m['ct'] < 30 and m['cr'] > m['vw'] * 0.55, f'{label} 제작자 오른쪽 위 top={m["ct"]:.0f} right={m["cr"]:.0f}')
        check(m['brnd'] <= m['ll'] + 12 and m['lrgt'] <= m['tl'] + 12 and abs(mid - m['vw'] / 2) < 48,
              f'{label} 언어가 로고와 탭 사이·중앙 brandR={m["brnd"]:.0f} lang={m["ll"]:.0f}-{m["lrgt"]:.0f} tabsL={m["tl"]:.0f} mid={mid:.0f}')
    return m
HANGUL = re.compile(r'[가-힣]')
KANA = re.compile(r'[\u3040-\u30ff]')
RAWKEY = re.compile(r'\b(?:ov|sug|diag|kpi|col|cat|hook|th|series|heat|rank|howto|ill|privacy|err|results|reply|unit|metric|colinfo|notice|credit|act|fit|fsrc|rtarget|hub|wx|compass)\.[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*\b')
SITE_FILES = ['index.html', 'privacy.html', 'style.css', 'i18n.js', 'app.js', 'diag.js', 'overview.js', 'samples.js', 'hub.js', 'weather.js']
def open_card(page, cid='compass'):
    page.evaluate('(id)=>XA.openCard(id)', cid)
    page.wait_for_selector('#card-view:not([hidden])')
    page.wait_for_timeout(40)
def open_sec(page, sid):
    hidden = page.locator(f'#sec-{sid}').get_attribute('hidden')
    if hidden is not None:
        page.click(f'#compass-nav button[data-sec="{sid}"]')
    page.wait_for_selector(f'#sec-{sid}:not([hidden])', state='attached')

# ---------- 정적 검사: 실제 데이터 흔적 ----------
scan = SITE_FILES + ['README.md', 'NOTES.md', 'sample.csv', 'sample_overview.csv', 'tools/gen_sample.py', 'tools/gen_sample_overview.py', 'tools/build_samples.py']
OWNER = re.compile(r'툭이|Ty_Tuki|\btuki\b', re.I)
CREDIT_LINE = re.compile(r'credit|제작자|만든 사람|Made by|Creator', re.I)
bad_owner, bad_phr = [], []
PHRASES = [re.compile(p) for p in [r'\d+\s*월\s*(데이터|게시물|분석)', r'게시물\s*\d+\s*개\s*(분석|기준)', r'(?<![\d,])128\s*개', r'(October|Oct\.?)\s+data', r'실제\s*(계정|데이터)\s*기준']]
for f in scan:
    for i, line in enumerate(open(os.path.join(ROOT, f), encoding='utf-8'), 1):
        if OWNER.search(line) and not CREDIT_LINE.search(line): bad_owner.append(f'{f}:{i}: {line.strip()[:90]}')
        for p in PHRASES:
            if p.search(line): bad_phr.append(f'{f}:{i}: {line.strip()[:90]}')
check(not bad_owner, f'소유자 이름은 제작자 표시 줄에만 {bad_owner}')
check(not bad_phr, f'실제 데이터 기준 문구 없음 {bad_phr}')
check(not glob.glob(f'{ROOT}/screenshots/real_*'), '사이트 폴더에 real_* 스크린샷 없음')
check('𝕏' not in ''.join(open(os.path.join(ROOT, f), encoding='utf-8').read() for f in SITE_FILES), 'X 로고 문자(𝕏) 없음')
idx_html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
priv_html = open(os.path.join(ROOT, 'privacy.html'), encoding='utf-8').read()
OG = 'https://tuki0609.github.io/account-compass/og-image.png'
for name, src in (('index', idx_html), ('privacy', priv_html)):
    for s in [f'property="og:image" content="{OG}"', 'name="twitter:card" content="summary_large_image"',
              'name="twitter:creator" content="@Ty_Tuki0609"', 'property="og:locale" content="ko_KR"',
              'property="og:locale:alternate" content="en_US"', 'property="og:locale:alternate" content="ja_JP"',
              'property="og:image:width" content="1200"', 'property="og:image:height" content="630"',
              'property="og:image:alt"', f'name="twitter:image" content="{OG}"', 'name="twitter:image:alt"']:
        check(s in src, f'{name} 메타 {s[:56]}')
check('property="og:url" content="https://tuki0609.github.io/account-compass/"' in idx_html, 'index og:url')
check('property="og:url" content="https://tuki0609.github.io/account-compass/privacy.html"' in priv_html, 'privacy og:url')
og_path = os.path.join(ROOT, 'og-image.png')
og_raw = open(og_path, 'rb').read()
og_w, og_h = struct.unpack('>II', og_raw[16:24])
check(og_raw[:8] == b'\x89PNG\r\n\x1a\n' and og_w == 1200 and og_h == 630 and len(og_raw) < 1_000_000, f'og-image {og_w}x{og_h} {len(og_raw)}B')

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 900}, device_scale_factor=1, accept_downloads=True)
        pg = ctx.new_page()
        errs, ext = [], []
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('request', lambda r: (not r.url.startswith(URL)) and not r.url.startswith('data:') and ext.append(r.url))
        pg.goto(URL); pg.wait_for_timeout(300)

        # ---------- i18n 사전 검사 ----------
        keys = pg.evaluate("(()=>{const I=XA.I18N;const k=Object.keys(I.ko).filter(x=>!x.startsWith('_'));return {ko:k,langs:Object.keys(I),miss:Object.fromEntries(Object.keys(I).map(l=>[l,k.filter(x=>!(x in I[l]))])),meta:Object.keys(I).every(l=>I[l]._name&&I[l]._locale&&I[l]._short)}})()")
        check(set(keys['langs']) >= {'ko', 'en', 'ja'} and keys['meta'], f"언어 목록 {keys['langs']} + _name/_short/_locale")
        for lang in ('en', 'ja'):
            check(not keys['miss'][lang], f"모든 ko 키가 {lang}에 있음 (빠진 키 {keys['miss'][lang][:10]})")
            extra = pg.evaluate(f"Object.keys(XA.I18N.{lang}).filter(k=>!(k in XA.I18N.ko))")
            check(not extra, f'{lang}에만 있는 키 없음 {extra[:10]}')
        empty = pg.evaluate("Object.entries(XA.I18N).flatMap(([l,d])=>Object.entries(d).filter(([k,v])=>typeof v!=='string'||!v.trim()).map(([k])=>l+':'+k))")
        check(not empty, f'빈 번역 없음 {empty[:10]}')
        # 화면·코드에서 쓰는 키가 사전에 있는지 (정적 + 동적 키)
        used = set()
        for f in ['index.html', 'privacy.html']:
            used |= set(re.findall(r'data-i18n(?:-html|-placeholder|-title)?="([^"]+)"', open(os.path.join(ROOT, f), encoding='utf-8').read()))
        for f in ['app.js', 'diag.js', 'overview.js', 'i18n.js', 'hub.js', 'weather.js']:
            src = open(os.path.join(ROOT, f), encoding='utf-8').read()
            used |= set(re.findall(r"\bt\('([\w.]+)'", src)) | set(re.findall(r"XA\.err\('([\w.]+)'", src)) | set(re.findall(r"'(diag\.grade\.[abcd])'", src))
        dyn = pg.evaluate("""(()=>{const k=[];XA.CATS.concat(['reply']).forEach(c=>k.push('cat.'+c));XA.HOOKS.forEach(h=>k.push('hook.'+h[0]));Object.keys(XA.ALIAS).forEach(c=>k.push('col.'+c));
          for(let d=0;d<7;d++){k.push('day.'+d,'dayFull.'+d)};['cat','n','share','medImp','avgLikes','avgBm','er','br','nfr','prof','hook','used','hookImp','hookLikes','hookBr','lift'].forEach(x=>k.push('th.'+x));
          ['dow','days','imp','eng','bm','net','posts','bucket','medImp','ipp','medNet','er'].forEach(x=>k.push('ov.th.'+x));['0','1to3','4plus'].forEach(x=>k.push('ov.bucket.'+x));
          ['take','hook','len','time','media','end'].forEach(x=>k.push('diag.c.'+x));['prompt','list','steps','link'].forEach(x=>k.push('diag.take.'+x));['image','video','gif'].forEach(x=>k.push('diag.media.'+x));
          ['free','beforePay','prompt'].forEach(x=>k.push('serhook.'+x));
          ['handle','replies','rtNf','rtProf','rtImp','rtEach'].forEach(x=>k.push('th.'+x));
          ['ko','en','ja','none'].forEach(x=>k.push('fit.lang.'+x));
          return k})()""")
        used |= set(dyn)
        used = {k for k in used if not k.endswith('.')}  # t('cat.'+id) 같은 동적 접두어는 위 dyn에서 따로 검사
        missing_used = sorted(k for k in used if k not in keys['ko'])
        check(not missing_used, f'화면/코드에서 쓰는 키 {len(used)}개 전부 사전에 있음 (없는 키 {missing_used[:10]})')
        check(pg.evaluate('document.documentElement.lang') == 'ko', '기본 언어 ko, <html lang="ko">')

        # ---------- 제작자 표시 ----------
        hm = check_header(pg, '1280 ko')
        check(hm['href'] == 'https://x.com/Ty_Tuki0609' and hm['target'] == '_blank' and 'noopener' in hm['rel'], f'제작자 링크 새 탭 + noopener')
        check('제작자: tuki(툭이) @Ty_Tuki0609' in hm['cred'], f"제작자 표시 ({hm['cred']})")
        for wh in ((1440, 900), (1024, 800)):
            pg.set_viewport_size({'width': wh[0], 'height': wh[1]}); pg.wait_for_timeout(80)
            check_header(pg, f'{wh[0]} ko')
        pg.set_viewport_size({'width': 1280, 'height': 900}); pg.wait_for_timeout(80)
        check('X(구 트위터)와 무관한 비공식 도구입니다' in pg.inner_text('body'), '비공식 도구 안내 (ko)')

        # ---------- 홈 스크린샷 ----------
        pg.screenshot(path=f'{SHOT}/v2_01_home_ko.png')
        pg.screenshot(path=f'{SHOT}/v2_15_home_ko.png')

        # ---------- 홈 카드 모음 (CSV 올리기 전) ----------
        home0 = pg.evaluate("""() => {
          const mods = XA.modules.map(m => ({id:m.id, order:m.order, cat:m.category, status:m.status, title:m.titleKey, desc:m.descKey, needs:m.needsKey}));
          const dup = XA.registerModule({id:'compass', order:1, category:'analyze', status:'ready', titleKey:'hub.back', descKey:'hub.back', needsKey:'hub.needs.compass'});
          const added = XA.registerModule({id:'zz-test', order:9, category:'soon', status:'soon', titleKey:'hub.card.soonCal.t', descKey:'hub.card.soonCal.d', needsKey:'hub.needs.soonCal', requires:['text']});
          const n = XA.modules.length;
          XA.unregisterModule('zz-test');
          const miss = [];
          XA.modules.forEach(m => ['titleKey','descKey','needsKey'].forEach(k => ['ko','en','ja'].forEach(l => { if (!XA.I18N[l][m[k]]) miss.push(l+':'+m[k]); })));
          XA.hubCategories.forEach(c => ['ko','en','ja'].forEach(l => { if (!XA.I18N[l][c.titleKey]) miss.push(l+':'+c.titleKey); }));
          const cards = [...document.querySelectorAll('#hub-board .hub-card')].map(b => ({id:b.dataset.mod, dis:b.disabled, num:(b.querySelector('.num')||{}).textContent||''}));
          const cats = [...document.querySelectorAll('#hub-board .hub-cat')].map(s => s.dataset.cat);
          return { mods, dup, added, n, back: XA.modules.length, miss, cards, cats,
            lang: !!document.querySelector('header [data-lang-toggle]'),
            home: !document.getElementById('home').hidden,
            cardHidden: document.getElementById('card-view').hidden };
        }""")
        ids = [m['id'] for m in home0['mods']]
        check(ids == ['compass', 'weather', 'soon-calendar', 'soon-hooks', 'soon-quote'], f'카드 등록 순서 {ids}')
        check([m['order'] for m in home0['mods']] == [1, 2, 3, 4, 5], '카드 번호 1부터')
        check(home0['mods'][0]['status'] == 'ready' and home0['mods'][1]['cat'] == 'fun' and sum(1 for m in home0['mods'] if m['status']=='soon') == 3, '나침반·날씨·준비중 3장')
        check(home0['dup'] is False and home0['added'] is True and home0['back'] == 5, f"등록은 한 번만, 테스트 카드는 지움 {home0['dup']} {home0['n']}→{home0['back']}")
        check(not home0['miss'], f"카드 문구 키가 ko/en/ja에 있음 {home0['miss'][:8]}")
        check(home0['cats'] == ['analyze', 'fun', 'soon'] and home0['lang'] and home0['home'] and home0['cardHidden'], f"홈 분류·언어 버튼 {home0['cats']}")
        check([c['num'] for c in home0['cards']] == ['01', '02', '03', '04', '05'], f"카드 번호 표시 {[c['num'] for c in home0['cards']]}")
        check(all(c['dis'] for c in home0['cards'] if c['id'].startswith('soon')) and not any(c['dis'] for c in home0['cards'] if c['id'] in ('compass', 'weather')), '준비 중 카드만 비활성')
        pg.click('.hub-card[data-mod="soon-calendar"]', force=True)
        check(pg.evaluate("document.getElementById('card-view').hidden === true"), '준비 중 카드는 열리지 않음')
        pg.evaluate("XA.openCard('soon-hooks')")
        check(pg.evaluate("document.getElementById('card-view').hidden === true"), '준비 중은 함수로 열어도 들어가지 않음')
        open_card(pg, 'weather')
        w0 = pg.inner_text('#card-dynamic')
        check('예보를 만들지 않았' not in w0 and '°C' not in w0 and ('CSV' in w0 or '올려' in w0), f'파일 없을 때 날씨는 숫자를 만들지 않음 {w0[:80]}')
        pg.click('#back-home')
        check(pg.evaluate("!document.getElementById('home').hidden && document.getElementById('card-view').hidden"), '홈으로 돌아옴')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(200)
        en_home = pg.inner_text('#home')
        check(pg.evaluate("document.documentElement.lang")=='en' and not HANGUL.search(en_home) and 'Tone weather' in en_home and 'Coming soon' in en_home and 'Try with the example' in en_home, f'홈 EN 즉시 반영 {HANGUL.findall(en_home)[:6]}')
        check(pg.locator('header [data-lang-toggle]').is_visible(), '홈에서 언어 버튼이 보임')
        pg.screenshot(path=f'{SHOT}/v2_16_home_en.png')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(200)
        ja_home = pg.inner_text('#home')
        check(pg.evaluate("document.documentElement.lang")=='ja' and not HANGUL.search(ja_home) and KANA.search(ja_home) and '口調の天気予報' in ja_home and '準備中' in ja_home and '例で試す' in ja_home, f'홈 JA 즉시 반영 {HANGUL.findall(ja_home)[:6]}')
        pg.screenshot(path=f'{SHOT}/v2_17_home_ja.png')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(150)
        check(pg.evaluate("XA.last==null && document.documentElement.lang=='ko'"), '언어를 바꿔도 CSV는 그대로 없음, 한국어로 복귀')

        # ---------- 샘플 (내장 samples.js) ----------
        pg.click('#btn-sample'); pg.wait_for_selector('#results:not([hidden])', state='attached'); pg.wait_for_timeout(800)
        check(pg.evaluate("document.getElementById('home') && !document.getElementById('home').hidden"), '예시를 넣어도 홈에 머무름')
        check('EXAMPLE' in pg.inner_text('#home-status'), '홈에 예시라고 표시')
        kept_n = pg.evaluate('XA.last.posts.length')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(200)
        home_en = pg.inner_text('#home')
        check(pg.evaluate('XA.last.posts.length') == kept_n and pg.evaluate("localStorage.getItem('xa-lang')")=='en', '홈에서 언어를 바꿔도 CSV를 다시 읽지 않음')
        check('Tone weather' in home_en and 'Coming soon' in home_en and 'Try with the example' in home_en and 'Drag & drop your CSV here' in home_en and 'Analysis & direction' in home_en and 'Not available yet' in home_en and not HANGUL.search(home_en), f'올린 뒤 홈 EN 즉시 반영 {HANGUL.findall(home_en)[:6]}')
        open_card(pg, 'weather')
        check('← Home' in pg.inner_text('#back-home') and pg.evaluate("document.documentElement.lang")=='en' and 'For fun' in pg.inner_text('#card-dynamic') and pg.evaluate('XA.last.posts.length')==kept_n, '홈에서 고른 언어가 카드·뒤로가기에도 유지')
        pg.click('#back-home')
        check(pg.evaluate("document.documentElement.lang")=='en' and 'Tone weather' in pg.inner_text('#home') and pg.evaluate('XA.last.posts.length')==kept_n, '카드에서 홈으로 돌아와도 언어·CSV 유지')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(200)
        home_ja = pg.inner_text('#home')
        check(pg.evaluate('XA.last.posts.length')==kept_n and '口調の天気予報' in home_ja and '準備中' in home_ja and '例で試す' in home_ja and 'CSVファイルをここにドロップするか' in home_ja and not HANGUL.search(home_ja), f'올린 뒤 홈 JA 즉시 반영 {HANGUL.findall(home_ja)[:6]}')
        open_card(pg, 'compass')
        check('← ホームへ' in pg.inner_text('#back-home') and pg.evaluate("document.documentElement.lang")=='ja' and pg.evaluate('XA.last.posts.length')==kept_n, '홈에서 고른 일본어가 나침반 카드에 유지')
        pg.click('#back-home')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(150)
        check(pg.evaluate("document.documentElement.lang")=='ko' and pg.evaluate('XA.last.posts.length')==kept_n, '한국어로 돌아와도 같은 CSV')
        open_card(pg, 'compass')
        n = pg.evaluate('XA.last.posts.length'); check(n == 94, f'샘플 게시물 수 {n}')
        cats = pg.evaluate('Object.entries(XA.last.posts.reduce((a,p)=>(a[p.cat]=(a[p.cat]||0)+1,a),{}))'); print('  카테고리 분포', cats)
        check(pg.evaluate("XA.last.timeSrc.id") == 94, 'ID→시각 복원 94개')
        check(pg.evaluate('XA.last.nReply') == 14, '샘플 가상 답글 14개')
        check(pg.locator('#cat-table tbody tr').count() >= 6, '카테고리 표 6행 이상')
        check(pg.locator('#top5 li').count() == 5 and pg.locator('#bottom5 li').count() == 5, 'TOP/BOTTOM 5')
        check(pg.locator('#suggest .sug').count() >= 3, f"제안 {pg.locator('#suggest .sug').count()}개")
        check(pg.locator('#series .ser').count() == 3, '시리즈 3개')
        acts = pg.evaluate('XA.weeklyActions(XA.last).map(a=>a.id)')
        check(len(acts) == 3 and 'more' in acts and 'reply' in acts and 'time' in acts, f'이번 주 할 일 {acts}')
        check(pg.locator('#actions .action').count() == 3, '이번 주 할 일 카드 3장')
        check(pg.locator('#sec-follow').is_hidden() and pg.locator('#sec-fit').is_hidden() and pg.locator('#sec-replies').is_hidden(), '나침반은 할 일 외에는 접혀 있음')
        pg.screenshot(path=f'{SHOT}/v2_18_compass_ko.png')
        rt = pg.evaluate("""()=>{const R=XA.replyTargets(XA.last.posts.filter(p=>p.isReply));return {order:R.rows.map(r=>r.key),keep:R.keep.map(r=>r.key),drop:R.drop.map(r=>r.key),watch:R.watch.map(r=>r.key)}}""")
        check(rt['order'][0] == 'example_alpha' and rt['order'][-1] == 'example_gamma', f"답글 순위 {rt['order']}")
        check('example_alpha' in rt['keep'] and 'example_gamma' in rt['drop'] and 'example_delta' in rt['watch'] and 'example_echo' not in rt['drop'] and 'example_delta' not in rt['drop'], f'계속/없음/표본 {rt}')
        open_sec(pg, 'replies')
        rtxt = pg.inner_text('#rtarget')
        check('상관' in rtxt and 'example_alpha' in rtxt and 'example_gamma' in rtxt and '표본 적음' in rtxt, '답글 순위 문구·핸들·표본 주의')
        links = pg.evaluate("""()=>[...document.querySelectorAll('#fit a, #rtarget a')].map(a=>({h:a.getAttribute('href'),t:a.target,r:a.rel}))""")
        check(links and all(x['t'] == '_blank' and 'noopener' in (x['r'] or '') for x in links), f'검색·프로필 링크 새 탭+noopener ({len(links)}개)')
        check(all(x['h'].startswith('https://x.com/') and not x['h'].startswith('http://') for x in links), '링크는 https://x.com 만')
        qs = pg.evaluate("""()=>[...document.querySelectorAll('#fit a')].map(a=>({q:new URL(a.href).searchParams.get('q'),f:new URL(a.href).searchParams.get('f')}))""")
        check(qs and all('lang:ko' in x['q'] and '-filter:replies' in x['q'] and 'min_faves:' in x['q'] for x in qs), f"검색 연산자 {qs[:1]}")
        check(any(x['f'] == 'live' for x in qs) and any(x['f'] == 'user' for x in qs) and set(x['f'] for x in qs) <= {'live', 'user'}, f"최신/사람 탭 {[x['f'] for x in qs]}")
        share = pg.evaluate("""()=>{const p=XA.pairForContent(true);const s=XA.followShare(XA.lastContent.posts,p.ov);return {kind:p.kind,status:s.status,share:s.share,post:s.postNf,ov:s.ovNf}}""")
        check(share['kind'] == 'sample' and share['status'] == 'ok' and 0 <= share['share'] < 1 and share['ov'] > share['post'], f'예시 팔로우 비율 {share}')
        open_sec(pg, 'follow')
        check('예시' in pg.inner_text('#follow-src') and 'EXAMPLE' in pg.inner_text('#follow-src'), '팔로우 비율에 EXAMPLE 안내')
        logic = pg.evaluate("""()=>{
          const R = XA.replyTargets([
            {text:'@AbC hi', replyTo:'AbC', nf:1, prof:1, imp:10, likes:0},
            {text:'@abc yo', replyTo:'abc', nf:2, prof:1, imp:10, likes:0},
            {text:'@zero a', replyTo:'zero', nf:0, prof:0, imp:5, likes:0},
            {text:'@zero b', replyTo:'zero', nf:0, prof:0, imp:5, likes:0},
            {text:'@zero c', replyTo:'zero', nf:0, prof:0, imp:5, likes:0},
            {text:'@once z', replyTo:'once', nf:5, prof:1, imp:3, likes:0}
          ]);
          const abc = R.rows.find(r => r.key === 'abc');
          const lang = [XA.detectPostLang([{text:'한글 글입니다'}]), XA.detectPostLang([{text:'English post about tools'}]), XA.detectPostLang([{text:'日本語の投稿です'}])];
          const floor = [XA.favesFloor([{likes:3},{likes:3}]), XA.favesFloor([{likes:40}]), XA.favesFloor([{likes:500}])];
          const no = XA.followShare([{ms:Date.UTC(2020,0,1), nf:3}], {map:{nf:1}, days:[{key:Date.UTC(2024,0,1), nf:10}]});
          const ok = XA.followShare([{ms:Date.UTC(2024,0,2,3), nf:4},{ms:Date.UTC(2024,0,3,3), nf:6}], {map:{nf:1}, days:[{key:Date.UTC(2024,0,2), nf:20},{key:Date.UTC(2024,0,5), nf:50}]});
          const over = XA.followShare([{ms:Date.UTC(2024,0,2,3), nf:30}], {map:{nf:1}, days:[{key:Date.UTC(2024,0,2), nf:10}]});
          const savedOv = XA.lastOverview, savedFlag = XA.lastOverviewSample;
          XA.lastOverview = {mode:'overview', map:{nf:1}, days:[{key:1, nf:9}]};
          XA.lastOverviewSample = false;
          const mismatch = XA.pairForContent(true).kind;
          XA.lastOverview = savedOv; XA.lastOverviewSample = savedFlag;
          const cleaned = [XA.cleanTerm('lang:en'), XA.cleanTerm('min_faves:10'), XA.cleanTerm('AI 이미지')];
          const q = XA.fittingQueries([
            {isReply:false, text:'무료 AI 이미지 툴 정리\\n1. a\\n2. b', cat:'guide', likes:12, bm:4, imp:100},
            {isReply:false, text:'AI 이미지 프롬프트 정리\\n1. a\\n2. b', cat:'guide', likes:10, bm:3, imp:80},
            {isReply:false, text:'AI 이미지 업스케일 방법\\n1. a\\n2. b', cat:'guide', likes:9, bm:2, imp:70}
          ], [], [{c:'guide', n:3, br:0.03, er:0.05}], true);
          const urlsOk = q.queries.length > 0 && q.queries.every(x => x.postsUrl.startsWith('https://x.com/search?') && x.peopleUrl.startsWith('https://x.com/search?') && x.q.includes('lang:ko') && x.q.includes('-filter:replies') && /min_faves:\\d+/.test(x.q));
          return {abcN: abc && abc.n, abcNf: abc && abc.nf, drop: R.drop.map(r=>r.key), watch: R.watch.map(r=>r.key), keep: R.keep.map(r=>r.key), lang, floor, no: no.status, ok: ok.status, share: ok.share, over: over.status, mismatch, cleaned, urlsOk, nq: q.queries.length};
        }""")
        check(logic['abcN'] == 2 and logic['abcNf'] == 3 and logic['drop'] == ['zero'] and logic['watch'] == ['once'] and 'abc' in logic['keep'] and 'once' not in logic['keep'], f"핸들 묶기 {logic}")
        check(logic['lang'] == ['ko', 'en', 'ja'] and logic['floor'] == [5, 40, 100], f"언어·min_faves {logic['lang']} {logic['floor']}")
        check(logic['no'] == 'noOverlap' and logic['ok'] == 'ok' and abs(logic['share'] - 0.5) < 1e-9 and logic['over'] == 'over' and logic['mismatch'] == 'mismatch', f"팔로우 비율 로직 {logic}")
        check(logic['cleaned'][0] == '' and logic['cleaned'][1] == '' and logic['cleaned'][2] == 'AI 이미지' and logic['urlsOk'], f"검색어 정리 {logic['cleaned']} nq={logic['nq']}")
        for sel, name, sec in [('#actions-block', 'v2_11_actions_ko', None), ('#follow-block', 'v2_12_follow_ko', 'follow'), ('#fit-block', 'v2_13_fit_ko', 'fit'), ('#rtarget-block', 'v2_14_replies_ko', 'replies')]:
            if sec: open_sec(pg, sec)
            pg.locator(sel).scroll_into_view_if_needed(); pg.wait_for_timeout(150)
            pg.locator(sel).screenshot(path=f'{SHOT}/{name}.png')
        check(pg.locator('.heat .c').count() == 168, '히트맵 168칸')
        ci = pg.inner_text('#col-info'); check('인식한 칸(17개)' in ci and '없는 칸: 없음' in ci, f'인식한 칸 표시 유지: {ci[:80]}')
        print('  제안:', pg.eval_on_selector_all('#suggest .t', 'els=>els.map(e=>e.textContent)'))
        print('  시리즈:', pg.eval_on_selector_all('#series .t', 'els=>els.map(e=>e.textContent)'))
        open_sec(pg, 'rank')
        for m in ['likes', 'bm', 'er', 'nf', 'prof']: pg.select_option('#rank-metric', m)
        open_sec(pg, 'heat')
        for m in ['imp', 'n']: pg.select_option('#heat-metric', m)
        open_sec(pg, 'rank'); pg.select_option('#rank-metric', 'imp')
        open_sec(pg, 'heat'); pg.select_option('#heat-metric', 'likes')
        pg.evaluate("document.querySelector('#results').scrollIntoView();window.scrollBy(0,-100)"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SHOT}/v2_03_results_ko.png')
        pg.screenshot(path=f'{SHOT}/v2_03b_results_ko_full.png', full_page=True)

        # ---------- 말투 날씨 + 엣지 ----------
        kept = pg.evaluate('XA.last.posts.length')
        pg.click('#back-home')
        check(pg.evaluate('XA.last.posts.length') == kept, '홈으로 돌아가도 같은 CSV')
        pg.click('.hub-card[data-mod="weather"]'); pg.wait_for_selector('#card-dynamic .wx-metrics')
        wx = pg.evaluate("""() => {
          const model = XA.toneModel(XA.last.posts);
          const text = document.querySelector('#card-dynamic').innerText;
          const f = model.forecast;
          const nums = [String(f.humidity), String(f.precip), String(f.tempC), String(f.wind), String(f.vis), String(f.medLen)];
          return { sky: f.sky, h: f.humidity, p: f.precip, t: f.tempC, w: f.wind, n: model.stats.n, basis: model.stats.basis,
            shown: nums.every(n => text.includes(n)), honest: text.includes('심리') || text.includes('놀이'), sample: text.includes('EXAMPLE') };
        }""")
        check(wx['shown'] and wx['honest'] and wx['sample'] and wx['n'] >= 3 and wx['basis'] == 'original', f'날씨 숫자는 계산값과 같음 {wx}')
        pg.screenshot(path=f'{SHOT}/v2_19_weather_ko.png')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(250)
        enw = pg.inner_text('#card-dynamic')
        check(not HANGUL.search(enw) and 'For fun' in enw and pg.evaluate('XA.last.posts.length') == kept, f'날씨 EN, CSV 유지 {HANGUL.findall(enw)[:4]}')
        pg.screenshot(path=f'{SHOT}/v2_20_weather_en.png')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(250)
        jaw = pg.inner_text('#card-dynamic')
        check(not HANGUL.search(jaw) and '遊び' in jaw and pg.evaluate("localStorage.getItem('xa-lang')")=='ja', f'날씨 JA {HANGUL.findall(jaw)[:4]}')
        pg.screenshot(path=f'{SHOT}/v2_21_weather_ja.png')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(200)
        with pg.expect_download() as di:
            pg.click('#wx-share')
        png = open(di.value.path(), 'rb').read()
        check(png[:8] == b'\x89PNG\r\n\x1a\n' and len(png) > 5000, f'날씨 PNG {len(png)}B')
        open(f'{SHOT}/v2_19b_weather_png.png', 'wb').write(png)
        edge = pg.evaluate(r"""() => {
          const posts = (arr) => arr.map(text => ({text, isReply:false, hour:null}));
          const sky = (arr) => { const s = XA.toneStats(posts(arr)); const f = XA.toneForecast(s); return f && f.sky; };
          const storm = sky(['와!! 😂','대박!! 🔥','최고!! ✨','우와!! 🎉']);
          const fog = sky(['글쎄... ㅋㅋ','몰라... ㅎㅎ','그냥... ㅋㅋㅋ','음... ㅋㅋ']);
          const rain = sky(['이거 어때?','괜찮아?','진짜야?','해볼까?']);
          const snow = sky(['오늘 정리했습니다.','감사합니다.','도움이 됐습니다.','정리해 두었습니다.']);
          const long = 'This is a long neutral sentence about making videos and tools for creators every single day without any marks. ';
          const cloudy = sky([long+long, long+long, long+long, long+long]);
          const clear = sky(['Shipped a small update today','Drafted the next outline','Cut one repeated line','Kept the ending short']);
          const emoji = sky(['😊😊','🌸🌸','✨✨','🎉🎉']);
          const one = XA.toneStats([{text:'안녕!', isReply:false}]);
          const none = XA.toneStats([{text:'   '},{text:''}]);
          const s = XA.toneStats(posts(['와!! 😂','대박!! 🔥','최고!! ✨','우와!! 🎉']));
          const f = XA.toneForecast(s);
          const politePart = s.politeRate == null ? 0.35 : s.politeRate;
          const warmth = Math.max(0, Math.min(1, 0.16 + s.em*0.30 + s.ex*0.14 + s.laugh*0.18 + s.fp*0.16 + politePart*0.12 - Math.min(0.16, Math.max(0, (s.medLen-180)/900))));
          const timed = [];
          for (let i=0;i<3;i++) timed.push({text:'낮에 ㅋㅋ', hour:10, isReply:false});
          for (let i=0;i<3;i++) timed.push({text:'밤에 안녕하세요.', hour:23, isReply:false});
          const tm = XA.toneStats(timed).time;
          const longS = XA.toneStats([{text:'가'.repeat(8000), isReply:false}]);
          const longF = XA.toneForecast(longS);
          const run = (csv) => { try { const A = XA.analyze(XA.parseCSV(csv)); const st = XA.cardStatus(XA.moduleById('weather'), A); return {ok:true, state:st.state, key:st.key, mode:A.mode||'content', text:A.posts&&A.posts[0]&&A.posts[0].text, n:A.posts.length}; } catch(e) { return {ok:false, key:e.key}; } };
          const bom = '\ufeff게시물 ID,날짜,게시물 본문,노출수\n1,2026-01-01,안녕하세요. 오늘 정리했습니다.,10\n';
          const en = 'Post id,Date,Post text,Impressions\n1,2026-01-01,Hello there,10\n';
          const ja = 'ポストID,日付,ポスト本文,インプレッション数\n1,2026-01-01,こんにちは。今日は晴れです。,10\n';
          const ko = '게시물 ID,날짜,게시물 본문,노출수\n1,2026-01-01,한 줄만 있습니다!,10\n';
          const notext = 'Post id,Date,Impressions,Likes\n1979000000000000001,2026-01-02,10,1\n';
          const emptyText = 'Post id,Post text,Impressions\n1,,10\n';
          const emojiCsv = 'Post id,Post text,Impressions\n1,😂🔥✨!!,10\n2,🎉✨!!,9\n3,😊!!,8\n';
          return { storm, fog, rain, snow, cloudy, clear, emoji, oneN: one&&one.n, oneSky: one&&XA.toneForecast(one).sky, none: none===null, empty: XA.toneStats([])===null,
            warm: Math.abs(f.warmth-warmth)<1e-9, temp: f.tempC===Math.round(5+warmth*29), hum: f.humidity===Math.round(s.express*100),
            pre: f.precip===Math.round(s.precipShare*100), wind: f.wind===Math.max(3,Math.min(48,Math.round(1400/Math.max(s.medLen,12)))),
            tm, longSky: longF.sky, longLen: longF.medLen,
            bom: run(bom), en: run(en), ja: run(ja), ko: run(ko), notext: run(notext), emptyText: run(emptyText), emojiCsv: run(emojiCsv),
            noRows: run(''), headerOnly: run('Post id,Impressions\n') };
        }""")
        check(edge['storm']=='storm' and edge['fog']=='fog' and edge['rain']=='rain' and edge['snow']=='snow', f"하늘 규칙 {edge['storm']} {edge['fog']} {edge['rain']} {edge['snow']}")
        check(edge['cloudy']=='cloudy' and edge['clear']=='clear' and edge['emoji']=='clear', f"흐림/맑음/이모지 {edge['cloudy']} {edge['clear']} {edge['emoji']}")
        check(edge['oneN']==1 and edge['oneSky']=='storm' and edge['none'] and edge['empty'], f"한 줄·빈 본문 {edge['oneN']} {edge['oneSky']}")
        check(edge['warm'] and edge['temp'] and edge['hum'] and edge['pre'] and edge['wind'], '기온·습도·강수·바람 공식이 화면 숫자와 같음')
        check(edge['tm']['kind']=='shift' and edge['tm']['dayN']==3 and edge['tm']['nightN']==3 and edge['tm']['dayPct']==100 and edge['tm']['nightPct']==0, f"낮/밤 {edge['tm']}")
        check(edge['longSky']=='cloudy' and edge['longLen']==8000, f"긴 글 {edge['longSky']} {edge['longLen']}")
        check(edge['noRows'].get('key')=='err.noRows' and edge['headerOnly'].get('key')=='err.noRows', f"빈 CSV {edge['noRows']} {edge['headerOnly']}")
        check(edge['bom']['ok'] and edge['bom']['text'].startswith('안녕') and edge['en']['ok'] and edge['en']['text']=='Hello there' and edge['ja']['ok'] and 'こんにちは' in edge['ja']['text'] and edge['ko']['n']==1, f"헤더 BOM/ko/en/ja {edge['bom']} {edge['en']} {edge['ja']} {edge['ko']}")
        check(edge['notext']['state']=='blocked' and edge['notext']['key']=='hub.why.noTextCol' and edge['emptyText']['key']=='hub.why.emptyText', f"본문 없음 {edge['notext']} {edge['emptyText']}")
        check(edge['emojiCsv']['state']=='ready', f"이모지 CSV {edge['emojiCsv']}")
        pg.evaluate("XA.handleText('Post id,Date,Impressions\\n1979000000000000001,2026-01-02,10\\n', false)")
        pg.evaluate('XA.closeCard()')
        why = pg.inner_text('.hub-card[data-mod="weather"]')
        check('본문' in why and '예보를 만들지 않았' in why, f'카드에 본문 없음 이유 {why[:120]}')
        n_blocked = pg.evaluate('XA.last.posts.length')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(200)
        why_en = pg.inner_text('.hub-card[data-mod="weather"]')
        check(pg.evaluate('XA.last.posts.length')==n_blocked and 'no post-text column' in why_en and 'Not available yet' in pg.inner_text('#home') and not HANGUL.search(pg.inner_text('#home')), f'이유 EN, CSV 유지 {why_en[:140]}')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(200)
        why_ja = pg.inner_text('.hub-card[data-mod="weather"]')
        check('本文の列がありません' in why_ja and not HANGUL.search(why_ja) and pg.evaluate('XA.last.posts.length')==n_blocked, f'이유 JA {why_ja[:140]}')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(150)
        open_card(pg, 'weather')
        blocked = pg.inner_text('#card-dynamic')
        check('°C' not in blocked and '예보를 만들지 않았' in blocked and pg.locator('.wx-metrics').count()==0, '본문 없는 CSV는 예보 숫자를 만들지 않음')
        pg.click('#back-home')
        pg.click('#btn-sample'); pg.wait_for_selector('#results:not([hidden])', state='attached')
        open_card(pg, 'compass')

        # ---------- 파서 변형 ----------
        variants = {
          '한글 헤더': ('게시물 ID,날짜,게시물 텍스트,게시물 링크,노출수,좋아요,참여수,북마크,공유,새 팔로워,답글,재게시물,프로필 방문수\n"1849000000000000000","2024-08-26","무료 툴 5곳 정리\n1. a\n2. b",https://x.com/a/status/1849000000000000000,"1,200",30,60,20,1,2,3,4,5\n', 'guide'),
          '구 tweet activity': ('Tweet id,Tweet permalink,Tweet text,time,impressions,engagements,engagement rate,retweets,replies,likes,user profile clicks,url clicks,hashtag clicks,detail expands\n1100000000000000000,https://twitter.com/a/status/1100000000000000000,오늘 점심 맛있다,2019-02-25 14:05 +0000,500,10,0.02,1,1,5,1,0,0,2\n', 'daily'),
          '세미콜론+BOM, 본문 없음': ('\ufeffPost id;Date;Impressions;Likes;Engagements;Bookmarks\n1979000000000000000;Sat, Oct 18, 2025;900;12;40;3\n', None),
          '일본어 헤더': ('ポストID,日付,インプレッション数,いいね,エンゲージメント,ブックマーク\n1979000000000000000,2025-10-18,900,12,40,3\n', None),
          '영어 소문자·공백 변형': ('  post ID ,DATE,post text,POST LINK,impressions ,likes,engagements,bookmarks,shares,new follows,replies,reposts,profile visits,detail expands,url clicks,hashtag clicks,permalink clicks\n2106242921259557181,"Sat, Oct 3, 2026","5 free AI tools for thumbnails\n1. a\n2. b",https://x.com/a/status/2106242921259557181,1000,20,50,10,1,3,1,2,9,4,2,0,1\n', 'guide'),
        }
        for name, (csv, cat) in variants.items():
            r = pg.evaluate('(t)=>{try{const A=XA.analyze(XA.parseCSV(t));return {ok:true,n:A.posts.length,map:Object.keys(A.map),un:A.unmapped,imp:A.posts[0].imp,hour:A.posts[0].hour,cat:A.posts[0].cat,hasText:A.hasText}}catch(e){return {ok:false,e:e.message}}}', csv)
            check(r.get('ok') and r['n'] == 1 and r['imp'] > 0 and (cat is None or r['cat'] == cat), f'파서 {name}: {r}')
        # 영어 콘텐츠 헤더 17칸 (요청 표기 그대로)
        en = 'Post id,Date,Post text,Post Link,Impressions,Likes,Engagements,Bookmarks,Shares,New follows,Replies,Reposts,Profile visits,Detail expands,URL Clicks,Hashtag clicks,Permalink clicks\n2106242921259557181,"Sat, Oct 3, 2026",hi,https://x.com/a/status/2106242921259557181,10,1,2,7,8,9,11,12,13,3,4,5,6\n'
        r = pg.evaluate("(t)=>{const A=XA.analyze(XA.parseCSV(t));const p=A.posts[0];return {mode:A.mode||'content',un:A.unmapped,keys:Object.keys(A.map).length,v:[p.imp,p.likes,p.eng,p.bm,p.shares,p.nf,p.rep,p.rt,p.prof,p.det,p.url,p.tag,p.plink]}}", en)
        check(r['mode'] == 'content' and r['un'] == [] and r['keys'] == 17 and r['v'] == [10, 1, 2, 7, 8, 9, 11, 12, 13, 3, 4, 5, 6], f'영문 콘텐츠 헤더 17칸 전부 정확히 매칭 {r}')
        # 영어 개요 헤더 14칸
        ov = 'Date,Impressions,Likes,Engagements,Bookmarks,Shares,New follows,Unfollows,Replies,Reposts,Profile visits,Create Post,Video views,Media views\n' + \
             ''.join(f'"Thu, Oct {d}, 2026",{1000+d},{10+d},{20+d},{d},1,{5+d},2,3,4,{30+d},{d%3},70,80\n' for d in range(1, 16))
        r = pg.evaluate("(t)=>{const A=XA.analyze(XA.parseCSV(t));const d=A.days[3];return {mode:A.mode,un:A.unmapped,keys:Object.keys(A.map).sort(),n:A.days.length,d:[d.imp,d.likes,d.eng,d.bm,d.shares,d.nf,d.unf,d.rep,d.rt,d.prof,d.posts,d.vid,d.media]}}", ov)
        check(r['mode'] == 'overview' and r['un'] == [] and len(r['keys']) == 14 and r['n'] == 15 and r['d'] == [1004, 14, 24, 4, 1, 9, 2, 3, 4, 34, 1, 70, 80], f'영문 개요 헤더 14칸 매칭 {r}')
        r = pg.evaluate("(t)=>{try{return XA.analyze(XA.parseCSV(t)).mode||'content'}catch(e){return e.message}}", 'DATE , IMPRESSIONS,likes,ENGAGEMENTS,new follows,unfollows\n"Wed, Oct 1, 2025",1000,10,20,3,1\n')
        check(r == 'overview', f'영문 개요 대소문자 변형 → 개요 모드 ({r})')
        # 실제 한국어 콘텐츠 헤더 + 답글 분리
        rcsv = '게시물 ID,날짜,게시물 본문,게시물 링크,노출수,마음에 들어요,참여수,북마크,공유 수,새로운 팔로우,답글,재게시,프로필 조회수,세부정보 펼치기,URL 클릭수,해시태그 클릭수,고유 링크 클릭수\n' + \
            '2106242921259557181,"Sat, Oct 3, 2026","무료 AI 툴 3곳 정리\n1. 가\n2. 나",https://x.com/a/status/2106242921259557181,1000,20,50,10,1,3,1,2,9,4,2,0,1\n' + \
            '2106242921259557182,"Sat, Oct 3, 2026",@someone ㅋㅋ 맞아요,https://x.com/a/status/2106242921259557182,30,1,2,0,0,0,0,0,1,0,0,0,0\n'
        r = pg.evaluate("(t)=>{const A=XA.analyze(XA.parseCSV(t));return {n:A.posts.length,rep:A.nReply,cats:A.posts.map(p=>p.cat),un:A.unmapped,keys:Object.keys(A.map).length,det:A.posts[0].det,plink:A.posts[0].plink,url:A.posts[0].url,text:A.posts[0].text}}", rcsv)
        check(r['n'] == 2 and r['rep'] == 1 and r['cats'] == ['guide', 'reply'], f'답글 감지·분리 {r["cats"]}')
        check(r['un'] == [] and r['keys'] == 17 and r['det'] == 4 and r['url'] == 2 and r['plink'] == 1 and '\n' in r['text'], '한국어 콘텐츠 헤더 17칸 + 여러 줄 본문')
        # 영어 게시물 카테고리·훅
        en_posts = {
            '5 free AI tools for thumbnails\n1. Tool A\n2. Tool B\n3. Tool C\nSave this 👇': 'guide',
            'How to write a blog post in 10 minutes, step by step guide': 'guide',
            'Day 7 of building my AI side project in public. I tried a new prompt workflow today.': 'exp',
            'Just released: new image model from a big lab rolls out to free users': 'news',
            'Good morning! Coffee first, then work. Tired today': 'daily',
            'lol this is insane 😂': 'quote',
            'Made this short film with AI, sound on 🎬': 'video',
        }
        got = pg.evaluate("(arr)=>arr.map(s=>XA.categorize(s))", list(en_posts))
        check(got == list(en_posts.values()), f'영어 카테고리 규칙 {got}')
        hk = pg.evaluate("(s)=>XA.HOOKS.filter(h=>h[1](s)).map(h=>h[0])", 'Before you pay, try these 5 free tools\n1. a\n2. b\nPrompt below 👇')
        check(set(hk) >= {'free', 'beforePay', 'prompt', 'list', 'nItems', 'cta'}, f'영어 훅 키워드 {hk}')
        ja_posts = {
            '課金する前にこれだけ。\n無料AI画像ツール5選\n\n1. A\n2. B\n3. C\n保存してね': 'guide',
            'AI動画の作り方をまとめました': 'guide',
            '副業7日目。新しいプロンプトを試してみた': 'exp',
            '新モデルがリリース。無料ユーザーにも公開': 'news',
            'おはよう。コーヒー飲んでから仕事。疲れた': 'daily',
            'やばい、これすごい😂': 'quote',
            'AIでショート動画を作りました。音あり🎬': 'video',
        }
        got = pg.evaluate("(arr)=>arr.map(s=>XA.categorize(s))", list(ja_posts))
        check(got == list(ja_posts.values()), f'일본어 카테고리 규칙 {got}')
        hk = pg.evaluate("(s)=>XA.HOOKS.filter(h=>h[1](s)).map(h=>h[0])", '課金する前に、無料ツールを5つ\n1. a\n2. b\nプロンプトは下に👇')
        check(set(hk) >= {'free', 'beforePay', 'prompt', 'list', 'nItems', 'cta'}, f'일본어 훅 키워드 {hk}')
        ja_c = 'ポストID,日付,インプレッション数,いいね,エンゲージメント,ブックマーク,共有,新しいフォロー,返信,リポスト,プロフィールへのアクセス数,詳細のクリック数,URLのクリック数,ハッシュタグのクリック数,固定リンクのクリック数\n2106242921259557181,2026-10-03,10,1,2,7,8,9,11,12,13,3,4,5,6\n'
        r = pg.evaluate("(t)=>{const A=XA.analyze(XA.parseCSV(t));const p=A.posts[0];return {mode:A.mode||'content',un:A.unmapped,n:Object.keys(A.map).length,v:[p.imp,p.likes,p.eng,p.bm,p.shares,p.nf,p.rep,p.rt,p.prof,p.det,p.url,p.tag,p.plink]}}", ja_c)
        check(r['mode'] == 'content' and r['un'] == [] and r['n'] == 15 and r['v'] == [10, 1, 2, 7, 8, 9, 11, 12, 13, 3, 4, 5, 6], f'일본어 콘텐츠 헤더 15칸 {r}')
        ja_ov = '日付,インプレッション数,いいね,エンゲージメント,ブックマーク,共有,新しいフォロー,フォロー解除,返信,リポスト,プロフィールへのアクセス数,ポスト,動画再生数,メディアの再生数\n2026年10月1日,1000,10,20,1,1,5,2,3,4,30,2,70,80\n'
        r = pg.evaluate("(t)=>{const A=XA.analyze(XA.parseCSV(t));const d=A.days[0];return {mode:A.mode,un:A.unmapped,n:Object.keys(A.map).length,d:[d.imp,d.likes,d.eng,d.bm,d.shares,d.nf,d.unf,d.rep,d.rt,d.prof,d.posts,d.vid,d.media]}}", ja_ov)
        check(r['mode'] == 'overview' and r['un'] == [] and r['n'] == 14 and r['d'] == [1000, 10, 20, 1, 1, 5, 2, 3, 4, 30, 2, 70, 80], f'일본어 개요 헤더·年月日 {r}')
        ja_loose = '投稿ID,投稿日時,ポスト本文,ポストのリンク,表示回数,いいね数,エンゲージメント数,ブックマーク数,シェア,新規フォロー,リプライ,リツイート,プロフィールアクセス\n2106242921259557181,2026-10-03 09:00,まとめ,https://x.com/a/status/2106242921259557181,10,1,2,7,8,9,11,12,13\n'
        r = pg.evaluate("(t)=>{const A=XA.analyze(XA.parseCSV(t));const p=A.posts[0];return {un:A.unmapped,n:Object.keys(A.map).length,v:[p.imp,p.likes,p.eng,p.bm,p.shares,p.nf,p.rep,p.rt,p.prof],text:p.text}}", ja_loose)
        check(r['un'] == [] and r['n'] == 13 and r['v'] == [10, 1, 2, 7, 8, 9, 11, 12, 13] and r['text'] == 'まとめ', f'일본어 헤더 느슨한 별칭 {r}')
        ja_old = 'ツイートID,ツイートの固定リンク,ツイート本文,時間,インプレッション,エンゲージメント,エンゲージメント率,リツイート,返信,いいね,ユーザープロフィールクリック,URLクリック数,ハッシュタグクリック,詳細クリック,固定リンクのクリック数,メディアの再生数,プロモのインプレッション\n1100000000000000000,https://twitter.com/a/status/1100000000000000000,今日のランチ,2019-02-25 14:05 +0000,500,10,0.02,1,1,5,1,0,0,2,3,4,999\n'
        r = pg.evaluate("(t)=>{const rows=XA.parseCSV(t);const A=XA.analyze(rows);const p=A.posts[0];const mi=A.map.media;return {un:A.unmapped,cat:p.cat,imp:p.imp,eng:p.eng,likes:p.likes,rt:p.rt,rep:p.rep,prof:p.prof,url:p.url,det:p.det,plink:p.plink,media:mi!=null?rows[1][mi]:null}}", ja_old)
        check(r['imp'] == 500 and r['eng'] == 10 and r['likes'] == 5 and r['rt'] == 1 and r['rep'] == 1 and r['prof'] == 1 and r['det'] == 2 and r['plink'] == 3 and r['media'] == '4' and r['cat'] == 'daily' and all('プロモ' in u or '率' in u for u in r['un']), f'일본어 구 트윗 액티비티(프로모·率 제외) {r}')

        # ---------- 개요 샘플 ----------
        pg.evaluate('XA.closeCard()')
        pg.click('#btn-sample-ov'); pg.wait_for_selector('#overview:not([hidden])', state='attached'); pg.wait_for_timeout(300)
        open_card(pg, 'compass')
        check(pg.is_hidden('#results') and pg.locator('#overview .kpi').count() == 8, '개요 샘플: 결과 영역 전환 + KPI 8개')
        check(pg.evaluate('XA.last.pre.length') == 5, '개요 샘플: 준비 기간 5일 제외')
        check('인식한 칸' in pg.inner_text('#ov-col-info'), '개요에도 인식한 칸 표시')
        pg.evaluate("document.querySelector('#overview').scrollIntoView();window.scrollBy(0,-100)"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SHOT}/v2_08_overview_ko.png')
        pg.evaluate('XA.closeCard()')
        pg.click('#btn-sample'); pg.wait_for_selector('#results:not([hidden])', state='attached')
        open_card(pg, 'compass')
        check(pg.is_hidden('#overview'), '콘텐츠 샘플로 돌아오면 개요 숨김')
        pg.evaluate('XA.closeCard()')
        pg.set_input_files('#file', f'{ROOT}/sample.csv'); pg.wait_for_timeout(500)
        open_card(pg, 'compass')
        check(pg.is_hidden('#sample-banner'), '파일 업로드 시 샘플 배너 숨김')
        pg.evaluate('XA.closeCard()')
        pg.click('#btn-sample'); pg.wait_for_timeout(400)

        # ---------- 복붙 진단 (ko) ----------
        pg.click('.tab[data-tab=diag]')
        pg.fill('#d-text', '오늘 점심 맛있었다 ㅎㅎ'); pg.click('#d-run'); low = int(pg.text_content('.ring text'))
        pg.click('#d-ex'); pg.click('details.opt summary'); pg.fill('#d-views', '1500'); pg.fill('#d-likes', '30'); pg.fill('#d-bm', '25'); pg.click('#d-run')
        high = int(pg.text_content('.ring text')); check(high >= 80 and low < 40, f'진단 점수 예시글 {high} / 일상글 {low}')
        dtxt = pg.inner_text('#d-result'); check('일반적인 경험칙' in dtxt or '내 CSV' in dtxt, '진단 기준 = 일반 경험칙/내 데이터')
        pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(200)
        pg.screenshot(path=f'{SHOT}/v2_07_diag_ko.png', full_page=True)
        pg.fill('#d-text', '와 이거 미쳤다 ㅋㅋㅋ'); pg.select_option('#d-hour', '3'); pg.select_option('#d-media', 'none'); pg.select_option('#d-kind', 'quote'); pg.fill('#d-views', ''); pg.click('#d-run')
        check(int(pg.text_content('.ring text')) < 40, '인용 리액션 짧은 글 낮은 점수')

        # ---------- 사용법 ----------
        pg.evaluate('XA.closeCard()')
        pg.click('.tab[data-tab=csv]')
        pg.click('.beginner-cta'); pg.wait_for_timeout(150)
        check('active' in (pg.get_attribute('#tab-help', 'class') or ''), '처음이에요 링크가 사용법을 연다')
        pg.click('.tab[data-tab=csv]')
        pg.click('.beginner-cta.alt'); pg.wait_for_timeout(150)
        check('active' in (pg.get_attribute('#tab-diag', 'class') or ''), '무료 복붙 진단 바로가기')
        pg.click('.tab[data-tab=csv]')
        home = pg.inner_text('#tab-csv')
        check('처음이에요' in home and '복붙 진단' in pg.inner_text('.beginner') and 'PC 웹' in home, '첫 화면에 사용법·복붙 진단·PC 안내')
        pg.click('.tab[data-tab=help]'); pg.wait_for_timeout(200)
        htxt = pg.inner_text('#tab-help')
        check(pg.locator('#tab-help svg.ill').count() == 7, f"사용법 그림 7개 ({pg.locator('#tab-help svg.ill').count()})")
        check(pg.locator('#tab-help .dl-ico').count() >= 1 and pg.locator('#tab-help .note.warn').count() == 1, '본문 다운로드 아이콘 + 모바일 안내')
        for s in ['Premium', 'Premium+', 'Basic', '인증 조직', '2026년 10월', '예시 그림', 'PC 웹이 가장 쉬워요', '인식한 칸', '복붙 진단',
                  '7D', '4W', '다운로드 아이콘', '콘텐츠', '요약', '모바일 앱', 'account_analytics', '프로필 메뉴']:
            check(s in htxt, f'사용법에 "{s}"')
        pg.screenshot(path=f'{SHOT}/v2_02_howto.png', full_page=True)

        # ---------- 언어 전환 ----------
        pg.click('.tab[data-tab=csv]'); pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(500)
        check(pg.evaluate('document.documentElement.lang') == 'en' and pg.evaluate("localStorage.getItem('xa-lang')") == 'en', 'EN 전환: <html lang=en> + localStorage 저장')
        body = pg.inner_text('body')
        check('Unofficial tool, not affiliated with X (formerly Twitter)' in body and 'Made by tuki(툭이) @Ty_Tuki0609' in re.sub(r'\s+', ' ', pg.inner_text('.topbar')), '영어 비공식 안내 + 제작자 표시')
        for sel in ['#summary', '#cat-table', '#hook-table', '#col-info', '.tabs', '#suggest', '#rank-metric', '#heat-metric', '#time-src', '#hour-blocks', '#actions', '#follow-src', '#rtarget']:
            tx = pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}').cloneNode(true);e.querySelectorAll('.from-data').forEach(n=>n.remove());return e.textContent}})()")
            # 제안 카드에는 샘플 본문의 한국어 소재가 따옴표로 들어갈 수 있음 → 카테고리 이름 외 한글 없음
            check(not HANGUL.search(tx), f'EN 모드 {sel} 한글 없음 {HANGUL.findall(tx)[:5]}')
        open_card(pg, 'compass'); open_sec(pg, 'fit')
        fit_en = pg.evaluate("(()=>{const e=document.querySelector('#fit').cloneNode(true);e.querySelectorAll('.from-data').forEach(n=>n.remove());return e.textContent})()")
        check(not HANGUL.search(fit_en) and 'min_faves:' in pg.inner_text('#fit') and 'People' in pg.inner_text('#fit'), f'EN 맞는 사람 찾기 크롬 {HANGUL.findall(fit_en)[:5]}')
        check(not RAWKEY.search(body), f'EN 모드 빠진 번역 키 노출 없음 {RAWKEY.findall(body)[:5]}')
        pg.evaluate("document.querySelector('#results').scrollIntoView();window.scrollBy(0,-100)"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SHOT}/v2_06_results_en.png')
        pg.reload(); pg.wait_for_timeout(400)
        check(pg.evaluate('document.documentElement.lang') == 'en' and 'Account Compass' in pg.inner_text('.brand'), '새로고침 후 EN 유지')
        check('Made by tuki(툭이) @Ty_Tuki0609' in re.sub(r'\s+', ' ', pg.inner_text('.topbar')), 'EN 제작자 표시')
        for wh in ((1280, 900), (1024, 800)):
            pg.set_viewport_size({'width': wh[0], 'height': wh[1]}); pg.wait_for_timeout(60)
            check_header(pg, f'{wh[0]} en')
        pg.set_viewport_size({'width': 1280, 'height': 900}); pg.wait_for_timeout(40)
        pg.screenshot(path=f'{SHOT}/v2_04_home_en.png')
        pg.screenshot(path=f'{SHOT}/v2_16_home_en.png')
        pg.click('.tab[data-tab=help]'); pg.wait_for_timeout(200)
        h_en = pg.inner_text('#tab-help')
        check(not HANGUL.search(h_en), f'EN 사용법 한글 없음 {HANGUL.findall(h_en)[:5]}')
        check(all(s in h_en for s in ['Premium+', 'verified organizations', 'Basic', 'October 2026', 'Illustrative', 'Desktop web is easiest', 'download icon', '7D', '4W', 'mobile app', 'account_analytics', 'Summary']), 'EN 사용법 핵심 안내')
        beg = pg.text_content('.beginner') or ''
        check('New here?' in beg and 'Paste check' in beg and not HANGUL.search(beg), 'EN 첫 화면 사용법·복붙 진단')
        pg.screenshot(path=f'{SHOT}/v2_02b_howto_en.png', full_page=True)
        pg.click('.tab[data-tab=diag]'); pg.click('#d-ex'); pg.click('#d-run'); pg.wait_for_timeout(200)
        sc = int(pg.text_content('.ring text')); dtx = pg.inner_text('#d-result')
        check(sc >= 80 and 'Takeaway' in dtx and not HANGUL.search(dtx), f'EN 진단 (예시 {sc}점, 한글 없음)')
        pg.click('.tab[data-tab=csv]'); pg.click('#btn-sample-ov'); pg.wait_for_selector('#overview:not([hidden])', state='attached'); pg.wait_for_timeout(300)
        open_card(pg, 'compass')
        otx = pg.inner_text('#overview'); check(not HANGUL.search(otx) and not RAWKEY.search(otx) and 'Impressions' in otx, f'EN 개요 한글/키 노출 없음 {HANGUL.findall(otx)[:5]}')
        pg.goto(URL + 'privacy.html'); pg.wait_for_timeout(200)
        ptx = pg.inner_text('body'); check('Privacy & terms' in ptx and 'never uploaded' not in '' and not RAWKEY.search(ptx), 'EN 개인정보 페이지')
        pg.screenshot(path=f'{SHOT}/v2_10_privacy_en.png', full_page=True)
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(200)
        ptx = pg.inner_text('body'); check('브라우저 안에서만' in ptx and '쿠키' in ptx and pg.evaluate('document.documentElement.lang') == 'ko', 'KO 개인정보 페이지 + 다시 ko')
        pg.goto(URL); pg.wait_for_timeout(200)
        check(pg.evaluate('document.documentElement.lang') == 'ko', 'ko 선택도 저장됨')

        # ---------- 일본어 UI ----------
        pg.click('#btn-sample'); pg.wait_for_selector('#results:not([hidden])', state='attached'); pg.wait_for_timeout(400)
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(400)
        check(pg.evaluate('document.documentElement.lang') == 'ja' and pg.evaluate("localStorage.getItem('xa-lang')") == 'ja', 'JA 전환: <html lang=ja> + localStorage')
        check('制作者:' in re.sub(r'\s+', ' ', pg.inner_text('.topbar')) and 'X（旧Twitter）とは無関係の非公式ツールです' in pg.inner_text('body'), '일본어 비공식 안내 + 제작자 표시')
        check(KANA.search(pg.inner_text('h1')) and not HANGUL.search(pg.inner_text('.hero')) and not HANGUL.search(pg.inner_text('.tabs')), 'JA 히어로·탭에 한글 없음, 가나 있음')
        for sel in ['#summary', '#cat-table', '#hook-table', '#col-info', '.tabs', '#suggest', '#rank-metric', '#heat-metric', '#time-src', '#hour-blocks', '#actions', '#follow-src', '#rtarget']:
            tx = pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}').cloneNode(true);e.querySelectorAll('.from-data').forEach(n=>n.remove());return e.textContent}})()")
            check(not HANGUL.search(tx), f'JA 모드 {sel} 한글 없음 {HANGUL.findall(tx)[:5]}')
        fit_ja = pg.evaluate("(()=>{const e=document.querySelector('#fit').cloneNode(true);e.querySelectorAll('.from-data').forEach(n=>n.remove());return e.textContent})()")
        check(not HANGUL.search(fit_ja) and KANA.search(fit_ja), f'JA 맞는 사람 찾기 {HANGUL.findall(fit_ja)[:5]}')
        check(not RAWKEY.search(pg.inner_text('body')), f'JA 모드 빠진 번역 키 노출 없음 {RAWKEY.findall(pg.inner_text("body"))[:5]}')
        open_card(pg, 'weather'); pg.wait_for_timeout(200)
        jaw = pg.inner_text('#card-dynamic')
        check(not HANGUL.search(jaw) and '遊び' in jaw, f'JA 날씨 카드 {HANGUL.findall(jaw)[:4]}')
        pg.screenshot(path=f'{SHOT}/v2_21_weather_ja.png')
        pg.evaluate('XA.closeCard()')
        for wh in ((1280, 900), (1440, 900), (1024, 800)):
            pg.set_viewport_size({'width': wh[0], 'height': wh[1]}); pg.wait_for_timeout(60)
            check_header(pg, f'{wh[0]} ja')
        pg.set_viewport_size({'width': 1280, 'height': 900})
        pg.click('.tab[data-tab=help]'); pg.wait_for_timeout(150)
        h_ja = pg.inner_text('#tab-help')
        check(not HANGUL.search(h_ja) and KANA.search(h_ja) and all(s in h_ja for s in ['Premium+', 'Basic', '2026年10月', '認証済み組織', 'ダウンロード', '7D', '4W', 'モバイル', 'account_analytics', '要約', 'コンテンツ']), f'JA 사용법 {HANGUL.findall(h_ja)[:5]}')
        beg = pg.text_content('.beginner') or ''
        check(not HANGUL.search(beg) and '初めて' in beg, 'JA 첫 화면 사용법 링크')
        pg.click('.tab[data-tab=diag]'); pg.click('#d-ex'); pg.click('#d-run'); pg.wait_for_timeout(200)
        sc = int(pg.text_content('.ring text')); dtx = pg.inner_text('#d-result')
        check(sc >= 80 and not HANGUL.search(dtx) and KANA.search(dtx), f'JA 진단 (예시 {sc}점)')
        pg.goto(URL + 'privacy.html'); pg.wait_for_timeout(200)
        ptx = pg.inner_text('.prose'); check('プライバシー' in ptx and not HANGUL.search(ptx) and not RAWKEY.search(ptx) and pg.evaluate('document.documentElement.lang') == 'ja', 'JA 개인정보 페이지')
        check_header(pg, '1280 ja privacy')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(150)
        check(pg.evaluate('document.documentElement.lang') == 'ko', 'JA 다음 다시 ko')
        pg.goto(URL); pg.wait_for_timeout(200)
        check(not errs, f'콘솔 에러 없음 {errs}')
        check(not ext, f'외부 요청 없음 {ext}')

        # ---------- file:// (더블클릭으로 열기) ----------
        fp = b.new_page(); ferr, freq = [], []
        fp.on('pageerror', lambda e: ferr.append(str(e))); fp.on('console', lambda m: m.type == 'error' and ferr.append(m.text))
        fp.on('request', lambda r: (not r.url.startswith('file://')) and not r.url.startswith('data:') and freq.append(r.url))
        fp.goto(FILE_URL); fp.click('#btn-sample'); fp.wait_for_selector('#results:not([hidden])', state='attached', timeout=5000); fp.wait_for_timeout(500)
        ok1 = fp.evaluate('XA.last.posts.length') == 94
        fp.click('#btn-sample-ov'); fp.wait_for_selector('#overview:not([hidden])', state='attached', timeout=5000)
        fp.set_input_files('#file', f'{ROOT}/sample.csv'); fp.wait_for_selector('#results:not([hidden])', state='attached', timeout=5000)
        fp.click('.tab[data-tab=help]'); fp.click('[data-lang-toggle] button[data-lang=en]')
        check(ok1 and not ferr and not freq and fp.evaluate('document.documentElement.lang') == 'en', f'file:// 로 열어도 샘플·업로드·언어 전환 동작 (에러 {ferr}, 외부요청 {freq})')
        fp.close()

        # ---------- 실제 개요 CSV (스크린샷 없음) ----------
        REAL = os.environ.get('REAL_OVERVIEW')
        real_strings = set()
        if REAL and os.path.exists(REAL):
            pg.set_input_files('#file', REAL); pg.wait_for_selector('#overview:not([hidden])'); pg.wait_for_timeout(600)
            info = pg.evaluate("""()=>{const A=XA.last;const s=(l,k)=>l.reduce((a,d)=>a+d[k],0);return {mode:A.mode,days:A.days.length,act:A.act.length,pre:A.pre.length,un:A.unmapped,keys:Object.keys(A.map).length}}""")
            print('  REAL_OVERVIEW 구조', {k: info[k] for k in ['mode', 'un', 'keys']})
            check(info['mode'] == 'overview' and info['un'] == [] and info['keys'] == 14, '실제 개요 파일: 14칸 전부 인식')
            for k, v in json.loads(os.environ.get('REAL_EXPECT', '{}')).items(): check(info.get(k) == v, f'실제 파일 {k}')
            check(not errs, f'실제 개요 후 콘솔 에러 없음 {errs}')
            pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(300)
            check(not RAWKEY.search(pg.inner_text('#overview')), '실제 개요 EN 렌더 OK'); pg.click('[data-lang-toggle] button[data-lang=ko]')
            real_strings |= set(re.findall(r'\d+\.\d\d%', pg.inner_text('#overview')))
        else:
            print('SKIP 실제 개요 CSV 없음 (REAL_OVERVIEW 환경변수)')

        # ---------- 실제 콘텐츠 CSV (스크린샷 없음) ----------
        RC = os.environ.get('REAL_CONTENT')
        if RC and os.path.exists(RC):
            import csv as _csv
            pyrows = list(_csv.DictReader(open(RC, encoding='utf-8-sig')))
            pyrep = sum(1 for x in pyrows if x[list(x.keys())[2]].lstrip().startswith('@'))
            pg.set_input_files('#file', RC); pg.wait_for_selector('#results:not([hidden])', state='attached'); pg.wait_for_timeout(900)
            open_card(pg, 'compass')
            info = pg.evaluate("()=>{const A=XA.last;return {n:A.posts.length,rep:A.nReply,un:A.unmapped,keys:Object.keys(A.map).length,ids:A.timeSrc.id}}")
            check(info['n'] == len(pyrows), '실제 파일 행 수 = Python csv')
            check(info['rep'] == pyrep, '답글 수 = Python')
            check(info['un'] == [] and info['keys'] == 17, '실제 헤더 17칸 전부 인식, 못 알아본 칸 없음')
            check('없는 칸: 없음' in pg.inner_text('#col-info'), '인식 줄에 없는 칸 없음')
            check(info['ids'] == len(pyrows), 'ID→시각 복원 전부')
            check(pg.locator('#reply-box').is_visible(), '답글 요약 박스 표시')
            norig = len(pyrows) - pyrep
            check(pg.evaluate("XA.last.posts.filter(p=>!p.isReply).length") == norig, '요약은 원글 기준')
            heat_n = pg.evaluate("[...document.querySelectorAll('.heat .c[data-n]')].reduce((a,c)=>a+ +c.dataset.n,0)")
            check(heat_n == norig, '히트맵 = 원글만')
            check('답글' not in pg.inner_text('#cat-table'), '카테고리 표에 답글 없음(기본)')
            tops = pg.eval_on_selector_all('#top5 li .txt', 'els=>els.map(e=>e.textContent)')
            check(all(not x.lstrip().startswith('@') for x in tops), 'TOP5에 답글 없음')
            pg.check('#inc-replies'); pg.wait_for_timeout(500)
            heat_n2 = pg.evaluate("[...document.querySelectorAll('.heat .c[data-n]')].reduce((a,c)=>a+ +c.dataset.n,0)")
            check(heat_n2 == len(pyrows) and '답글' in pg.inner_text('#cat-table'), '토글 ON: 전체 포함 + 답글 줄')
            pg.uncheck('#inc-replies'); pg.wait_for_timeout(300)
            real_strings |= set(re.findall(r'\d+\.\d\d%', pg.inner_text('#results')))
            # 실제 파일로 진단 탭: 내 데이터 기준 비교로 바뀌는지
            pg.click('.tab[data-tab=diag]'); pg.click('#d-ex'); pg.click('#d-run'); pg.wait_for_timeout(200)
            check('내 CSV' in pg.inner_text('#d-result') or '내 데이터' in pg.inner_text('#d-result'), '실제 파일 업로드 후 진단 = 내 데이터 기준')
            pg.click('.tab[data-tab=csv]')
            pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(400)
            check(not RAWKEY.search(pg.inner_text('#results')), '실제 콘텐츠 EN 렌더 OK'); pg.click('[data-lang-toggle] button[data-lang=ko]')
            check(not errs, f'실제 콘텐츠 후 콘솔 에러 없음 {errs}')
            mr = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            merr = []; mr.on('pageerror', lambda e: merr.append(str(e)))
            mr.goto(URL); mr.set_input_files('#file', RC); mr.wait_for_selector('#results:not([hidden])', state='attached'); mr.wait_for_timeout(700)
            open_card(mr, 'compass')
            ow = mr.evaluate('document.documentElement.scrollWidth'); check(ow <= 392 and not merr, f'실제 콘텐츠 모바일 가로 넘침/에러 없음 ({ow})')
            mr.close()
        else:
            print('SKIP 실제 콘텐츠 CSV 없음 (REAL_CONTENT 환경변수)')
        # 실제 파일에서 나온 비율 수치(x.xx%)가 사이트 코드에 박혀 있지 않은지 (값은 출력하지 않음)
        if real_strings:
            code = ''.join(open(os.path.join(ROOT, f), encoding='utf-8').read() for f in ['index.html', 'privacy.html', 'i18n.js', 'app.js', 'diag.js', 'overview.js', 'README.md', 'NOTES.md'])
            leaked = [s for s in real_strings if s in code and s not in ('0.00%', '100.00%')]
            check(not leaked, f'실제 파일 비율 {len(real_strings)}개 중 사이트 코드·문서에 박힌 값 없음 (발견 {len(leaked)}개)')

        # ---------- 모바일 ----------
        m = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        merr = []; m.on('pageerror', lambda e: merr.append(str(e)))
        m.goto(URL); m.wait_for_timeout(300)
        check_header(m, '390 ko', mobile=True)
        m.screenshot(path=f'{SHOT}/v2_05_mobile.png')
        m.click('#btn-sample'); m.wait_for_selector('#results:not([hidden])', state='attached'); m.wait_for_timeout(800)
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 홈 가로 넘침 없음 (scrollWidth {ow})')
        open_card(m, 'compass')
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 나침반 가로 넘침 없음 (scrollWidth {ow})')
        m.evaluate("document.querySelector('#results').scrollIntoView();window.scrollBy(0,-130)"); m.wait_for_timeout(300)
        m.screenshot(path=f'{SHOT}/v2_05b_mobile_results.png')
        m.click('#back-home'); open_card(m, 'weather'); m.wait_for_timeout(200)
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 날씨 가로 넘침 없음 (scrollWidth {ow})')
        m.screenshot(path=f'{SHOT}/v2_23_weather_mobile.png')
        m.click('#back-home')
        m.click('.tab[data-tab=help]'); m.wait_for_timeout(200)
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 사용법 가로 넘침 없음 ({ow})')
        m.screenshot(path=f'{SHOT}/v2_05c_mobile_howto.png', full_page=True)
        m.click('[data-lang-toggle] button[data-lang=en]'); m.wait_for_timeout(200); m.evaluate('window.scrollTo(0,0)')
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 EN 가로 넘침 없음 ({ow})')
        check_header(m, '390 en', mobile=True)
        m.screenshot(path=f'{SHOT}/v2_05d_mobile_en.png')
        m.click('[data-lang-toggle] button[data-lang=ja]'); m.wait_for_timeout(200); m.evaluate('window.scrollTo(0,0)')
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 JA 가로 넘침 없음 ({ow})')
        check_header(m, '390 ja', mobile=True)
        check(KANA.search(m.inner_text('body')) and m.evaluate('document.documentElement.lang') == 'ja', '모바일 JA 언어')
        m.click('.tab[data-tab=diag]'); m.click('#d-ex'); m.click('#d-run'); m.wait_for_timeout(200)
        check(not merr, f'모바일 에러 없음 {merr}')
        m.close()
        s = b.new_page(viewport={'width': 360, 'height': 740}, device_scale_factor=2, is_mobile=True, has_touch=True)
        serr = []; s.on('pageerror', lambda e: serr.append(str(e)))
        s.goto(URL); s.wait_for_timeout(300)
        s.click('[data-lang-toggle] button[data-lang=ko]'); s.wait_for_timeout(150)
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360 and not serr, f'360 홈 가로 넘침 없음 ({ow}) {serr}')
        check(s.locator('header [data-lang-toggle]').is_visible() and s.locator('.hub-card').count()==5, '360 홈에 언어 버튼과 카드 5장')
        s.screenshot(path=f'{SHOT}/v2_22_home_360.png')
        s.click('#btn-sample'); s.wait_for_selector('#results:not([hidden])', state='attached'); s.wait_for_timeout(400)
        open_card(s, 'weather'); s.wait_for_timeout(200)
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360, f'360 날씨 가로 넘침 없음 ({ow})')
        s.screenshot(path=f'{SHOT}/v2_23b_weather_360.png')
        s.click('#back-home'); open_card(s, 'compass'); s.wait_for_timeout(200)
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360, f'360 나침반 가로 넘침 없음 ({ow})')
        s.screenshot(path=f'{SHOT}/v2_24_compass_360.png')
        check(not serr, f'360 에러 없음 {serr}')
        b.close()
finally:
    srv.terminate()
print('\n총 실패:', len(fails))
sys.exit(1 if fails else 0)
