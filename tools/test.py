"""자동 테스트 (Playwright + 로컬 서버 + file://).
- 샘플 로드 / 파서 변형(한국어·영어·일본어·구 Tweet activity) / 영어 헤더 / 영어 카테고리 규칙
- i18n: ko 키가 전부 en·ja에 있음, 화면에 쓰는 키가 전부 사전에 있음, 언어 토글·저장·<html lang>
- 헤더: 언어 선택기(한국어/English/日本語)가 로고와 탭 사이, 제작자 표시가 1280·1440·1024·390에서 잘리지 않음
- 실제 데이터 흔적 없음(소유자 이름은 제작자 표시에만), file:// 동작, 외부 요청 없음
- v2 스크린샷(가상 샘플 데이터만) → screenshots/v2_*.png
실제 파일 회귀 테스트(선택): REAL_CONTENT=/path REAL_OVERVIEW=/path  — 실제 파일은 스크린샷을 찍지 않음.
실행: .venv/bin/python tools/test.py   (x-analyzer 폴더 또는 그 상위 폴더에서)"""
import subprocess, time, sys, json, os, re, glob, struct, csv, math, io
from datetime import date, datetime, timedelta, timezone
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
RAWKEY = re.compile(r'\b(?:ov|sug|diag|kpi|col|cat|hook|th|series|heat|rank|howto|ill|privacy|err|results|reply|unit|metric|colinfo|notice|credit|act|fit|fsrc|rtarget|hub|wx|compass|rc|ps|share)\.[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*\b')
SITE_FILES = ['index.html', 'privacy.html', 'style.css', 'i18n.js', 'app.js', 'diag.js', 'overview.js', 'samples.js', 'hub.js', 'weather.js', 'receipt.js', 'share.js', 'persona.js']
def open_card(page, cid='compass'):
    page.evaluate('(id)=>XA.openCard(id)', cid)
    page.wait_for_selector('#card-view:not([hidden])')
    page.wait_for_timeout(40)
def open_sec(page, sid):
    hidden = page.locator(f'#sec-{sid}').get_attribute('hidden')
    if hidden is not None:
        page.click(f'#compass-nav button[data-sec="{sid}"]')
    page.wait_for_selector(f'#sec-{sid}:not([hidden])', state='attached')

def home_fold(page, vw, vh, label):
    page.set_viewport_size({'width': vw, 'height': vh})
    page.evaluate('window.scrollTo(0,0)')
    page.wait_for_timeout(80)
    box = page.evaluate("""() => {
      const r = (sel) => document.querySelector(sel).getBoundingClientRect();
      const cards = [...document.querySelectorAll('#hub-board .hub-card')];
      return {
        n: cards.length,
        dropTop: r('#drop').top,
        boardTop: r('#hub-board').top,
        pickBottom: r('#csv-pick').bottom,
        sampleBottom: r('#btn-sample').bottom,
        howBottom: r('#csv-how').bottom,
        noteBottom: r('.csv-note').bottom,
        vh: window.innerHeight,
        funN: document.querySelectorAll('.hub-cat[data-cat="fun"] .hub-card').length,
        soonN: document.querySelectorAll('.hub-cat[data-cat="soon"] .hub-card').length,
        soonLine: !!document.getElementById('soon-line'),
        overflow: document.documentElement.scrollWidth > window.innerWidth + 1
      };
    }""")
    check(box['n'] == 4 and box['dropTop'] < box['boardTop'] and box['funN'] == 3 and box['soonN'] == 0 and box['soonLine'], f'{label} 올리기가 카드보다 위, 재미 3장, 준비 중은 한 줄 {box}')
    check(box['pickBottom'] <= box['vh'] + 1 and box['sampleBottom'] <= box['vh'] + 1 and box['howBottom'] <= box['vh'] + 1 and box['noteBottom'] <= box['vh'] + 1, f'{label} CSV 버튼·예시·30초·안내가 첫 화면 안 {box}')
    check(not box['overflow'], f'{label} 가로로 넘치지 않음')
    return box

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

MONTHS = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}
def parse_csv_date(s):
    m = re.search(r'([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})', s or '')
    if m and MONTHS.get(m.group(1)[:3].title()):
        return date(int(m.group(3)), MONTHS[m.group(1)[:3].title()], int(m.group(2)))
    m = re.search(r'(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})', s or '')
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None
def read_rows(path):
    with open(os.path.join(ROOT, path), encoding='utf-8', newline='') as f:
        return list(csv.reader(f))
def num_cell(raw):
    raw = (raw or '').strip().replace(',', '')
    if raw in ('', '-', '—'):
        return 0.0
    return float(raw)
def content_expected(path):
    rows = read_rows(path)
    head = [h.strip() for h in rows[0]]
    ix = {h: i for i, h in enumerate(head)}
    cols = {'Impressions': 'imp', 'Likes': 'likes', 'Reposts': 'rt', 'Replies': 'rep', 'Bookmarks': 'bm', 'Profile visits': 'prof', 'New follows': 'nf'}
    sums = {k: 0.0 for k in cols.values()}
    by = {}
    handles = {}
    best = None
    n = 0
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        imp = num_cell(r[ix['Impressions']])
        likes = num_cell(r[ix['Likes']])
        text = r[ix['Post text']] if 'Post text' in ix else ''
        if not (imp > 0 or likes > 0 or text.strip()):
            continue
        n += 1
        for name, key in cols.items():
            if name in ix:
                sums[key] += num_cell(r[ix[name]])
        d = parse_csv_date(r[ix['Date']]) if 'Date' in ix else None
        if d:
            by[d] = by.get(d, 0.0) + imp
        link = r[ix['Post Link']] if 'Post Link' in ix else ''
        hm = re.search(r'https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)/status/', link, re.I)
        if hm and hm.group(1).lower() not in ('i', 'intent', 'share', 'home', 'search'):
            handles[hm.group(1)] = handles.get(hm.group(1), 0) + 1
        if best is None or imp > best[0] or (imp == best[0] and n < best[2]):
            best = (imp, text, n)
    handle, best_n = '', 0
    for h, c in handles.items():
        if c > best_n:
            handle, best_n = h, c
    snippet = ''
    if best:
        line = next((s.strip() for s in best[1].splitlines() if s.strip()), '')
        line = re.sub(r'https?://\S+', '', line)
        line = re.sub(r'\s+', ' ', line).strip()
        chars = list(line)
        snippet = line if len(chars) <= 32 else ''.join(chars[:32]) + '…'
    best_day = min((d for d, q in by.items() if q == max(by.values()))) if by else None
    return {
        'sums': sums, 'n': n, 'handle': handle, 'snippet': snippet, 'by': by,
        'best_day': best_day, 'best_qty': by.get(best_day) if best_day else None,
        'period': (min(by), max(by)) if by else None,
    }
def overview_expected(path):
    rows = read_rows(path)
    head = [h.strip() for h in rows[0]]
    ix = {h: i for i, h in enumerate(head)}
    cols = {'노출수': 'imp', '마음에 들어요': 'likes', '재게시': 'rt', '답글': 'rep', '북마크': 'bm', '프로필 조회수': 'prof', '새로운 팔로우': 'nf'}
    parsed = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        d = parse_csv_date(r[ix['Date']])
        if not d:
            continue
        rec = {'date': d, 'posts': num_cell(r[ix['게시물 작성하기']])}
        for name, key in cols.items():
            rec[key] = num_cell(r[ix[name]])
        parsed.append(rec)
    parsed.sort(key=lambda x: x['date'])
    start = next(i for i, x in enumerate(parsed) if x['posts'] > 0) if any(x['posts'] > 0 for x in parsed) else 0
    sums = {k: sum(x[k] for x in parsed) for k in cols.values()}
    act = {k: sum(x[k] for x in parsed[start:]) for k in cols.values()}
    return {'sums': sums, 'act': act, 'n': len(parsed), 'start': start, 'period': (parsed[0]['date'], parsed[-1]['date'])}
def ymd_py(d):
    return f'{d.year}.{d.month:02d}.{d.day:02d}'
def grouped(n):
    return f'{int(round(n)):,}'
SAMPLE_RC = content_expected('sample.csv')
OV_RC = overview_expected('sample_overview.csv')
REPLY_RE = re.compile(r'^\s*[@＠]([A-Za-z0-9_]{1,15})\b')
SNOW_EPOCH = 1288834974657
KST = timezone(timedelta(hours=9))
MONS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
DOWS = 'Mon Tue Wed Thu Fri Sat Sun'.split()

def js_round(x):
    return int(math.floor(float(x) + 0.5))

def snow_id(y, m, d, h, seq):
    ms = int(datetime(y, m, d, h, 0, tzinfo=KST).timestamp() * 1000)
    return str(((ms - SNOW_EPOCH) << 22) + seq)

def time_from_id_py(id_):
    if not re.fullmatch(r'\d{15,20}', str(id_ or '')):
        return None
    ms = (int(id_) >> 22) + SNOW_EPOCH
    if ms <= datetime(2010, 11, 1, tzinfo=timezone.utc).timestamp() * 1000:
        return None
    if ms >= datetime.now(timezone.utc).timestamp() * 1000 + 864e5 * 2:
        return None
    return ms

def kst_hour_py(ms):
    return datetime.fromtimestamp((ms + 9 * 3600e3) / 1000, timezone.utc).hour

def date_label(d):
    return f'{DOWS[d.weekday()]}, {MONS[d.month - 1]} {d.day}, {d.year}'

def median_py(nums):
    if not nums:
        return None
    a = sorted(nums)
    m = len(a) >> 1
    return a[m] if len(a) % 2 else (a[m - 1] + a[m]) / 2

def ramp_up(v, lo, hi):
    if v is None or v <= lo:
        return 0
    if v >= hi:
        return 100
    return (v - lo) / (hi - lo) * 100

def ramp_down(v, full, zero):
    if v is None or v >= zero:
        return 0
    if v <= full:
        return 100
    return (zero - v) / (zero - full) * 100

def to_bar(v, pair):
    if v is None:
        return None
    lo, hi = pair
    x = (1 if v >= hi else 0) if hi == lo else max(0, min(1, (v - lo) / (hi - lo)))
    return max(1, min(99, js_round(1 + x * 98)))

def hit_show_py(raw):
    if raw is None:
        return None
    rounded = js_round(raw) if raw >= 10 else js_round(raw * 10) / 10
    if isinstance(rounded, float) and rounded == int(rounded):
        return str(int(rounded))
    return str(rounded)

def first_line_py(text):
    line = next((s.strip() for s in str(text or '').splitlines() if s.strip()), '')
    line = re.sub(r'https?://\S+', '', line)
    line = re.sub(r'\s+', ' ', line).strip()
    chars = list(line)
    return line if len(chars) <= 32 else ''.join(chars[:32]) + '…'

def parse_post_csv(text):
    rows = list(csv.reader(io.StringIO(text.lstrip('\ufeff'))))
    head = [h.strip() for h in rows[0]]
    ix = {h: i for i, h in enumerate(head)}
    alias = {
        'Post id': 'id', '게시물 ID': 'id', 'ポストID': 'id',
        'Date': 'date', '날짜': 'date', '日付': 'date',
        'Post text': 'text', '게시물 본문': 'text', 'ポスト本文': 'text',
        'Post Link': 'link',
        'Impressions': 'imp', '노출수': 'imp', 'インプレッション': 'imp',
        'Likes': 'likes', '마음에 들어요': 'likes', 'いいね': 'likes',
        'Reposts': 'rt', '재게시': 'rt', 'リポスト': 'rt',
        'Replies': 'rep', '답글': 'rep',
        'Bookmarks': 'bm', '북마크': 'bm',
        'Profile visits': 'prof', '프로필 조회수': 'prof',
        'New follows': 'nf', '새로운 팔로우': 'nf',
        'URL Clicks': 'url',
    }
    present = set()
    col = {}
    for name, key in alias.items():
        if name in ix and key not in col:
            col[key] = ix[name]
            present.add(key)
    posts = []
    for i, r in enumerate(rows[1:]):
        if not any(c.strip() for c in r):
            continue
        def cell(key):
            j = col.get(key)
            return r[j] if j is not None and j < len(r) else ''
        imp = num_cell(cell('imp')) if 'imp' in present else 0.0
        likes = num_cell(cell('likes')) if 'likes' in present else 0.0
        text = cell('text') if 'text' in present else ''
        if not (imp > 0 or likes > 0 or text.strip()):
            continue
        pid = cell('id').strip().lstrip("'")
        d = parse_csv_date(cell('date')) if 'date' in present else None
        ms = time_from_id_py(pid)
        posts.append({
            'i': i, 'id': pid, 'text': text, 'link': cell('link'), 'date': d,
            'reply': bool(REPLY_RE.match(text or '')),
            'imp': imp,
            'likes': num_cell(cell('likes')) if 'likes' in present else None,
            'rt': num_cell(cell('rt')) if 'rt' in present else None,
            'rep': num_cell(cell('rep')) if 'rep' in present else None,
            'bm': num_cell(cell('bm')) if 'bm' in present else None,
            'prof': num_cell(cell('prof')) if 'prof' in present else None,
            'nf': num_cell(cell('nf')) if 'nf' in present else None,
            'url': num_cell(cell('url')) if 'url' in present else None,
            'hour': kst_hour_py(ms) if ms is not None else None,
        })
    return posts, present

def sum_key(posts, key):
    return sum((p[key] or 0) for p in posts)

def persona_expect(posts, present, C, include_replies=False):
    rows = posts if include_replies else [p for p in posts if not p['reply']]
    def has(k):
        return k in present
    imp_sum = sum_key(rows, 'imp')
    likes_sum = sum_key(rows, 'likes') if has('likes') else None
    bm_sum = sum_key(rows, 'bm') if has('bm') else None
    rep_sum = sum_key(rows, 'rep') if has('rep') else None
    rt_sum = sum_key(rows, 'rt') if has('rt') else None
    nf_sum = sum_key(rows, 'nf') if has('nf') else None
    prof_sum = sum_key(rows, 'prof') if has('prof') else None
    imps = [p['imp'] for p in rows]
    max_imp = max(imps) if imps else 0
    med_imp = median_py(imps)
    hit = (max_imp / med_imp) if med_imp else None
    days = [p['date'] for p in rows if p['date']]
    active = None
    if days:
        span = (max(days) - min(days)).days + 1
        active = len(set(days)) / span if span else None
    hours = [p['hour'] for p in rows if p['hour'] is not None]
    dawn = (sum(1 for h in hours if 0 <= h <= 5) / len(hours)) if hours else None
    save = (bm_sum / likes_sum) if likes_sum and bm_sum is not None else None
    chat = (rep_sum / likes_sum) if likes_sum and rep_sum is not None else None
    repost = (rt_sum / likes_sum) if likes_sum and rt_sum is not None else None
    per1k = (nf_sum / imp_sum * 1000) if nf_sum is not None and imp_sum else None
    visits = (prof_sum / imp_sum * 1000) if prof_sum is not None and imp_sum else None
    conv = (nf_sum / prof_sum) if prof_sum and nf_sum is not None else None
    link = None
    if has('text') or has('url'):
        n_link = sum(1 for p in rows if (has('text') and re.search(r'https?://', p['text'] or '', re.I)) or (has('url') and (p['url'] or 0) > 0))
        link = n_link / len(rows) if rows else None
    med_len = None
    if has('text'):
        lens = [len(list(str(p['text'] or '').strip())) for p in rows]
        lens = [n for n in lens if n > 0]
        med_len = median_py(lens)
    thin = len(rows) < C['MIN_POSTS'] or imp_sum < C['MIN_IMP']
    scores = {
        'save': ramp_up(save, C['SAVE_LO'], C['SAVE_HI']),
        'chat': ramp_up(chat, C['CHAT_LO'], C['CHAT_HI']),
        'hit': ramp_up(hit, C['HIT_LO'], C['HIT_HI']),
        'ant': ramp_up(active, C['ANT_ACTIVE_LO'], C['ANT_ACTIVE_HI']) if active is not None and (hit is None or hit <= C['ANT_HIT_MAX']) else 0,
        'dawn': ramp_up(dawn, C['DAWN_LO'], C['DAWN_HI']),
        'magnet': ramp_up(per1k, C['MAGNET_LO'], C['MAGNET_HI']),
        'window': ramp_up(visits, C['WINDOW_VISIT_LO'], C['WINDOW_VISIT_HI']) if conv is not None and conv < C['WINDOW_CONV_MAX'] else 0,
        'repost': ramp_up(repost, C['REPOST_LO'], C['REPOST_HI']),
        'link': ramp_up(link, C['LINK_LO'], C['LINK_HI']),
        'short': ramp_down(med_len, C['SHORT_FULL'], C['SHORT_ZERO']),
        'long': ramp_up(med_len, C['LONG_ZERO'], C['LONG_FULL']),
    }
    cid, best = 'sprout', 0
    if not thin:
        for k in C['TIE']:
            if scores[k] > best:
                best, cid = scores[k], k
        if not (best > 0):
            cid = 'sprout'
    bars = {
        'save': None if (not has('bm') or not has('likes')) else to_bar(save, C['BAR_SAVE']),
        'chat': None if (not has('rep') or not has('likes')) else to_bar(chat, C['BAR_CHAT']),
        'hit': to_bar(hit, C['BAR_HIT']),
        'steady': None if active is None else to_bar(active, C['BAR_STEADY']),
        'magnet': None if not has('nf') else to_bar(per1k, C['BAR_MAGNET']),
    }
    return {'id': cid, 'n': len(rows), 'imp': imp_sum, 'hit': hit, 'hitShow': hit_show_py(hit), 'scores': scores, 'bars': bars, 'save': save, 'active': active, 'per1k': per1k, 'dawn': dawn}

def pick_grade(n, prices, conv, P):
    if n < P['MIN_POSTS']:
        return 'first'
    fp = prices.get('nf')
    if fp is not None and fp >= P['LUXURY']:
        return 'luxury'
    if fp is not None and fp <= P['VALUE']:
        return 'value'
    vp = prices.get('prof')
    if vp is not None and vp <= P['WINDOW_VISIT'] and conv is not None and conv < P['WINDOW_CONV']:
        return 'window'
    bp, lp = prices.get('bm'), prices.get('likes')
    if bp is not None and lp is not None and bp < lp * P['SAVE_MULT']:
        return 'save'
    rp = prices.get('rep')
    if rp is not None and rp <= P['TASTE']:
        return 'taste'
    return 'gap'

def price_expect(posts, present, P):
    imp = sum_key(posts, 'imp')
    lines = {}
    prices = {}
    for key in ('nf', 'likes', 'bm', 'rep', 'prof'):
        if key not in present:
            continue
        qty = sum_key(posts, key)
        if not qty:
            lines[key] = {'sold': True, 'num': qty, 'imp': imp}
            prices[key] = None
        else:
            raw = imp / qty
            lines[key] = {'sold': False, 'raw': raw, 'qty': js_round(raw), 'num': qty, 'imp': imp}
            prices[key] = raw
    conv = (sum_key(posts, 'nf') / sum_key(posts, 'prof')) if 'prof' in present and 'nf' in present and sum_key(posts, 'prof') else None
    days = [p['date'] for p in posts if p['date']]
    exp = cheap = None
    if 'nf' in present:
        for p in posts:
            nf, pimp = p['nf'] or 0, p['imp'] or 0
            if nf < P['EXP_MIN_NF'] or pimp < P['EXP_MIN_IMP'] or not p['date']:
                continue
            raw = pimp / nf
            item = {'date': p['date'], 'raw': raw, 'qty': js_round(raw), 'i': p['i']}
            if exp is None or raw > exp['raw'] or (raw == exp['raw'] and (item['date'] < exp['date'] or (item['date'] == exp['date'] and item['i'] < exp['i']))):
                exp = item
            if cheap is None or raw < cheap['raw'] or (raw == cheap['raw'] and (item['date'] < cheap['date'] or (item['date'] == cheap['date'] and item['i'] < cheap['i']))):
                cheap = item
    coupon = None
    if posts and imp > 0:
        by = {}
        for p in posts:
            if p['hour'] is None:
                continue
            cur = by.setdefault(p['hour'], {'n': 0, 'imp': 0})
            cur['n'] += 1
            cur['imp'] += p['imp']
        overall = imp / len(posts)
        for h, cur in by.items():
            if cur['n'] < P['COUPON_MIN']:
                continue
            pct = js_round((cur['imp'] / cur['n'] / overall - 1) * 100) if overall else 0
            if pct <= 0:
                continue
            if coupon is None or pct > coupon['pct'] or (pct == coupon['pct'] and h < coupon['hour']):
                coupon = {'hour': h, 'pct': pct}
    return {
        'lines': lines, 'grade': pick_grade(len(posts), prices, conv, P), 'imp': imp, 'n': len(posts),
        'nf': sum_key(posts, 'nf') if 'nf' in present else None,
        'exp': None if exp is None else {'date': f'{exp["date"].year}.{exp["date"].month:02d}.{exp["date"].day:02d}', 'qty': exp['qty'], 'raw': exp['raw']},
        'cheap': None if cheap is None else {'date': f'{cheap["date"].year}.{cheap["date"].month:02d}.{cheap["date"].day:02d}', 'qty': cheap['qty'], 'raw': cheap['raw']},
        'coupon': coupon,
        'headline': None if prices.get('nf') is None else js_round(prices['nf']),
        'kind': 'miss' if 'nf' not in present else ('sold' if prices.get('nf') is None else 'price'),
    }

def build_posts(n, **kw):
    start = kw.get('start', date(2026, 9, 1))
    gap = kw.get('gap', 0)
    per_day = kw.get('per_day', 1)
    rows = []
    for i in range(n):
        day_i = (i // per_day) * (gap + 1) if gap or per_day != 1 else i
        if kw.get('spread'):
            day_i = 0 if i < n // 2 else 39
        d = start + timedelta(days=day_i)
        hour = kw.get('hour', 12)
        imp = kw.get('imp', 100)
        if kw.get('spike') is not None and i == 0:
            imp = kw['spike']
        text = kw.get('text', '가' * kw.get('length', 60))
        if kw.get('reply') and i >= kw.get('reply_from', n // 2):
            text = '@alpha ' + text
        rows.append({
            'id': snow_id(d.year, d.month, d.day, hour, i + 1),
            'date': date_label(d),
            'text': text,
            'imp': imp, 'likes': kw.get('likes', 10), 'rt': kw.get('rt', 1), 'rep': kw.get('rep', 1),
            'bm': kw.get('bm', 1), 'prof': kw.get('prof', 1), 'nf': kw.get('nf', 0), 'url': kw.get('url', 0),
        })
    return rows

def posts_csv(rows, cols=None):
    cols = cols or ['Post id', 'Date', 'Post text', 'Post Link', 'Impressions', 'Likes', 'Reposts', 'Replies', 'Bookmarks', 'Profile visits', 'New follows', 'URL Clicks']
    key = {'Post id': 'id', 'Date': 'date', 'Post text': 'text', 'Post Link': 'link', 'Impressions': 'imp', 'Likes': 'likes', 'Reposts': 'rt', 'Replies': 'rep', 'Bookmarks': 'bm', 'Profile visits': 'prof', 'New follows': 'nf', 'URL Clicks': 'url'}
    lines = [','.join(cols)]
    for r in rows:
        vals = []
        for c in cols:
            k = key[c]
            if k == 'link':
                vals.append(r.get('link') or f"https://x.com/example_creator/status/{r['id']}")
            elif k == 'text':
                vals.append('"' + str(r.get('text', '')).replace('"', '""') + '"')
            elif k == 'date':
                vals.append('"' + str(r.get('date', '')) + '"')
            else:
                vals.append(str(r.get(k, '')))
        lines.append(','.join(vals))
    return '\n'.join(lines) + '\n'

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
        for f in ['app.js', 'diag.js', 'overview.js', 'i18n.js', 'hub.js', 'weather.js', 'receipt.js', 'share.js', 'persona.js']:
            src = open(os.path.join(ROOT, f), encoding='utf-8').read()
            used |= set(re.findall(r"\bt\('([\w.]+)'", src)) | set(re.findall(r"XA\.err\('([\w.]+)'", src)) | set(re.findall(r"'(diag\.grade\.[abcd])'", src))
            if f in ('receipt.js', 'persona.js', 'share.js'):
                used |= set(re.findall(r"'((?:rc|ps|share|hub)\.[A-Za-z0-9_.]+)'", src))
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

        # ---------- 홈 스크린샷 (1280x800 첫 화면) ----------
        home_fold(pg, 1280, 800, '1280x800 ko')
        pg.screenshot(path=f'{SHOT}/v2_01_home_ko.png')
        pg.screenshot(path=f'{SHOT}/v2_15_home_ko.png')
        pg.set_viewport_size({'width': 1280, 'height': 900}); pg.wait_for_timeout(40)

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
        check(ids == ['compass', 'persona', 'weather', 'receipt', 'soon-calendar', 'soon-hooks'], f'카드 등록 순서 {ids}')
        check([m['order'] for m in home0['mods']] == [1, 2, 3, 4, 5, 6], '카드 번호 1부터')
        check(home0['mods'][0]['id'] == 'compass' and home0['mods'][1]['id'] == 'persona' and home0['mods'][1]['cat'] == 'fun' and home0['mods'][3]['id'] == 'receipt' and sum(1 for m in home0['mods'] if m['status']=='soon') == 2, '나침반·부캐·날씨·영수증·준비중 2장')
        check(home0['dup'] is False and home0['added'] is True and home0['back'] == 6, f"등록은 한 번만, 테스트 카드는 지움 {home0['dup']} {home0['n']}→{home0['back']}")
        check(not home0['miss'], f"카드 문구 키가 ko/en/ja에 있음 {home0['miss'][:8]}")
        check(home0['cats'] == ['analyze', 'fun'] and home0['lang'] and home0['home'] and home0['cardHidden'], f"홈 분류·언어 버튼 {home0['cats']}")
        check([c['num'] for c in home0['cards']] == ['01', '02', '03', '04'], f"카드 번호 표시 {[c['num'] for c in home0['cards']]}")
        check(not any(c['id'].startswith('soon') for c in home0['cards']) and '준비 중' in pg.inner_text('#soon-line') and '이번 주 달력' in pg.inner_text('#soon-line'), '준비 중은 큰 카드가 아니라 한 줄')
        rc_need = pg.inner_text('.hub-card[data-mod="receipt"]')
        check('내 X 영수증' in rc_need and '노출' in rc_need and '없는 칸' in rc_need, f'영수증 카드에 필요한 칸을 적어 둠 {rc_need[:160]}')
        check('X 부캐 카드' in pg.inner_text('.hub-card[data-mod="persona"]') and '02' == home0['cards'][1]['num'], '부캐가 재미 묶음의 앞 카드')
        pg.click('.hub-card[data-mod="weather"]')
        ask = pg.inner_text('#hub-ask')
        check(pg.evaluate("document.getElementById('card-view').hidden === true") and not pg.locator('#hub-ask').is_hidden() and 'CSV' in ask and '말투 날씨 예보' in ask, f'CSV 없으면 들어가지 않고 다음 단계를 안내 {ask[:80]}')
        check(pg.evaluate("XA.openCard('soon-hooks')") is False and pg.evaluate("document.getElementById('card-view').hidden === true"), '준비 중은 함수로 열어도 들어가지 않음')
        open_card(pg, 'weather')
        w0 = pg.inner_text('#card-dynamic')
        check('예보를 만들지 않았' not in w0 and '°C' not in w0 and ('CSV' in w0 or '올려' in w0), f'파일 없을 때 날씨는 숫자를 만들지 않음 {w0[:80]}')
        pg.click('#back-home')
        check(pg.evaluate("!document.getElementById('home').hidden && document.getElementById('card-view').hidden"), '홈으로 돌아옴')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(200)
        en_home = pg.inner_text('#home')
        check(pg.evaluate("document.documentElement.lang")=='en' and not HANGUL.search(en_home) and 'Tone weather' in en_home and 'My X receipt' in en_home and 'My X alter ego' in en_home and 'Coming soon' in en_home and 'Not available yet' in en_home and 'Try the example now' in en_home and 'Load a CSV' in en_home and '30 seconds' in en_home, f'홈 EN 즉시 반영 {HANGUL.findall(en_home)[:6]}')
        check(pg.locator('header [data-lang-toggle]').is_visible(), '홈에서 언어 버튼이 보임')
        home_fold(pg, 1280, 800, '1280x800 en')
        pg.screenshot(path=f'{SHOT}/v2_16_home_en.png')
        pg.set_viewport_size({'width': 1280, 'height': 900}); pg.wait_for_timeout(40)
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(200)
        ja_home = pg.inner_text('#home')
        check(pg.evaluate("document.documentElement.lang")=='ja' and not HANGUL.search(ja_home) and KANA.search(ja_home) and '口調の天気予報' in ja_home and 'レシート' in ja_home and '裏キャラ' in ja_home and '準備中' in ja_home and '例をすぐ見る' in ja_home and 'CSVを読み込む' in ja_home and '30秒' in ja_home, f'홈 JA 즉시 반영 {HANGUL.findall(ja_home)[:6]}')
        home_fold(pg, 1280, 800, '1280x800 ja')
        pg.screenshot(path=f'{SHOT}/v2_17_home_ja.png')
        pg.set_viewport_size({'width': 1280, 'height': 900}); pg.wait_for_timeout(40)
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(150)
        check(pg.evaluate("XA.last==null && document.documentElement.lang=='ko'"), '언어를 바꿔도 CSV는 그대로 없음, 한국어로 복귀')

        # ---------- 샘플: 한 번 올리면 부캐가 먼저 열리고 다른 카드도 같은 파일 ----------
        pg.click('#btn-sample'); pg.wait_for_selector('#ps-card', timeout=5000); pg.wait_for_timeout(400)
        check(pg.evaluate("document.getElementById('home').hidden === true && document.getElementById('ps-card')") , '예시를 넣으면 부캐 카드가 바로 열림')
        kept_n = pg.evaluate('XA.last.posts.length')
        check(kept_n == 94, f'샘플 게시물 수 {kept_n}')
        PC = pg.evaluate('XA.PERSONA')
        sample_posts, sample_present = parse_post_csv(open(os.path.join(ROOT, 'sample.csv'), encoding='utf-8').read())
        pexp = persona_expect(sample_posts, sample_present, PC)
        check(pg.get_attribute('#ps-card', 'data-id') == pexp['id'], f"예시 부캐 {pg.get_attribute('#ps-card', 'data-id')} vs {pexp['id']}")
        check(pg.get_attribute('#ps-card', 'data-n') == str(pexp['n']) and pg.get_attribute('#ps-card', 'data-imp') == str(js_round(pexp['imp'])), f"예시 부캐 글·노출 {pexp['n']} {pexp['imp']}")
        check(pg.get_attribute('#ps-hit', 'data-show') == pexp['hitShow'], f"한 방 지수 {pg.get_attribute('#ps-hit', 'data-show')} vs {pexp['hitShow']}")
        for stat, bar in pexp['bars'].items():
            el = pg.locator(f'#ps-card [data-stat="{stat}"]')
            if bar is None:
                check(el.get_attribute('data-miss') == '1', f'{stat} 없는 칸은 0으로 안 그림')
            else:
                check(el.get_attribute('data-bar') == str(bar), f'{stat} 막대 {el.get_attribute("data-bar")} vs {bar}')
        check(pg.locator('#ps-hide-handle').is_checked() and pg.locator('#ps-hide-line').is_checked() and not pg.locator('#ps-replies').is_checked(), '부캐는 계정·첫 줄을 가리고 답글은 빼 둠')
        check(pg.get_attribute('#ps-why', 'open') is None and '왜 이렇게 나왔나요?' in pg.inner_text('#ps-why'), '왜 이렇게 나왔나나는 카드 아래, 접혀 있음')
        check('내 데이터 기준' in pg.inner_text('#ps-card') and '남과 비교한 순위 아님' in pg.inner_text('#ps-card') and 'tuki0609.github.io/account-compass' in pg.inner_text('#ps-card'), '부캐 하단 문구')
        check('놀이예요' in pg.inner_text('#ps-card'), '놀이 안내')
        pg.screenshot(path=f'{SHOT}/v2_30_persona_ko.png')
        pg.screenshot(path=f'{SHOT}/v2_34_example_ko.png')
        for tab in ('receipt', 'weather', 'compass', 'persona'):
            pg.click(f'[data-tab-card="{tab}"]'); pg.wait_for_timeout(80)
            check(pg.evaluate('XA.last.posts.length') == kept_n, f'{tab} 탭도 같은 파일')
        pg.click('[data-tab-card="receipt"]'); pg.wait_for_selector('#rc-paper')
        check(pg.get_attribute('#rc-paper [data-key="nf"]', 'data-imp') == str(int(SAMPLE_RC['sums']['imp'])), '영수증 탭도 다시 올리지 않음')
        pg.click('[data-tab-card="persona"]'); pg.wait_for_selector('#ps-card')
        pg.evaluate("""() => { window.__opened = []; window.open = (u) => { window.__opened.push(String(u)); return null; }; if (navigator.canShare) navigator.canShare = () => false; }""")
        with pg.expect_download() as psave:
            pg.click('#ps-save')
        ppng = open(psave.value.path(), 'rb').read()
        pw, ph = struct.unpack('>II', ppng[16:24])
        check(ppng[:8] == b'\x89PNG\r\n\x1a\n' and pw == 1080 and ph == 1350, f'부캐 PNG {pw}x{ph}')
        open(f'{SHOT}/v2_30b_persona_png.png', 'wb').write(ppng)
        wide = pg.evaluate("""() => { const c = XA.personaDraw(XA.personaModel(XA.last), {wide:true}); return {w:c.width, h:c.height}; }""")
        check(wide == {'w': 1200, 'h': 675}, f'가로 그림 {wide}')
        pg.evaluate("""() => { const c = navigator.clipboard; if (c) c.write = () => Promise.reject(new Error('no-clipboard')); }""")
        with pg.expect_download() as pcopy:
            pg.click('#ps-copy')
        pg.wait_for_timeout(200)
        check('붙여' in pg.inner_text('#ps-share-note') or '저장' in pg.inner_text('#ps-share-note') or pg.locator('#ps-share-note').is_visible(), '이미지 복사가 안 되면 저장으로 돌아감')
        cap = pg.evaluate("XA.personaCaption(XA.personaModel(XA.last), 'ko')")
        check(cap.startswith('제 X 부캐는 「') and '한 방 지수 ×' in cap and '#X부캐카드' in cap and 'c=persona' in cap and 'lang=ko' in cap, f'한국어 공유 문구 {cap[:80]}')
        with pg.expect_download() as px:
            pg.click('#ps-x')
        pg.wait_for_timeout(250)
        opened = pg.evaluate('window.__opened')
        check(opened and opened[0].startswith('https://x.com/intent/post?text=') and 'X 글쓰기 창에 방금 저장한 이미지' in pg.inner_text('#ps-share-note'), f'X 공유는 주소만 열고 붙이라는 안내 {opened[:1]}')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(200)
        en_ps = pg.inner_text('#ps-card')
        check(not HANGUL.search(en_ps) and 'Hit index' in en_ps and 'not a rank' in en_ps, f'부캐 EN {HANGUL.findall(en_ps)[:4]}')
        encap = pg.evaluate("XA.personaCaption(XA.personaModel(XA.last), 'en')")
        check(encap.startswith('My X alter ego is "') and 'Hit index ×' in encap and 'lang=en' in encap, '영어 공유 문구')
        pg.screenshot(path=f'{SHOT}/v2_31_persona_en.png')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(200)
        ja_ps = pg.inner_text('#ps-card')
        check(not HANGUL.search(ja_ps) and '一発指数' in ja_ps, f'부캐 JA {HANGUL.findall(ja_ps)[:4]}')
        jacap = pg.evaluate("XA.personaCaption(XA.personaModel(XA.last), 'ja')")
        check('私のXの裏キャラは「' in jacap and '#Xの裏キャラ診断' in jacap and 'lang=ja' in jacap, '일본어 공유 문구')
        pg.screenshot(path=f'{SHOT}/v2_32_persona_ja.png')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(150)
        pg.click('#back-home')
        st = pg.inner_text('#home-status')
        check('EXAMPLE' in st and 'sample.csv' in st and '✓' in st, f'홈에 파일 이름과 예시 표시 {st}')
        check('이 파일로 열 수 있어요' in pg.inner_text('.hub-card[data-mod="compass"]') and '이 파일로 열 수 있어요' in pg.inner_text('.hub-card[data-mod="persona"]') and '이 파일로 열 수 있어요' in pg.inner_text('.hub-card[data-mod="receipt"]'), '올린 뒤 카드가 열 수 있다고 표시')
        check('없는 칸은 빼요' in pg.inner_text('.hub-card[data-mod="receipt"]'), '영수증은 없는 칸을 빼라고 카드에 적음')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(200)
        home_en = pg.inner_text('#home')
        check(pg.evaluate('XA.last.posts.length') == kept_n and pg.evaluate("localStorage.getItem('xa-lang')")=='en', '홈에서 언어를 바꿔도 CSV를 다시 읽지 않음')
        check('Tone weather' in home_en and 'Coming soon' in home_en and 'Try the example now' in home_en and 'Load a CSV' in home_en and 'Analysis & direction' in home_en and 'Not available yet' in home_en and 'CSV loaded' in home_en and 'sample.csv' in home_en and 'My X alter ego' in home_en and not HANGUL.search(home_en), f'올린 뒤 홈 EN 즉시 반영 {HANGUL.findall(home_en)[:6]}')
        open_card(pg, 'weather')
        check('← Home' in pg.inner_text('#back-home') and pg.evaluate("document.documentElement.lang")=='en' and 'For fun' in pg.inner_text('#card-dynamic') and pg.evaluate('XA.last.posts.length')==kept_n, '홈에서 고른 언어가 카드·뒤로가기에도 유지')
        pg.click('#back-home')
        check(pg.evaluate("document.documentElement.lang")=='en' and 'Tone weather' in pg.inner_text('#home') and pg.evaluate('XA.last.posts.length')==kept_n, '카드에서 홈으로 돌아와도 언어·CSV 유지')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(200)
        home_ja = pg.inner_text('#home')
        check(pg.evaluate('XA.last.posts.length')==kept_n and '口調の天気予報' in home_ja and '準備中' in home_ja and '例をすぐ見る' in home_ja and 'CSVを読み込む' in home_ja and 'sample.csv' in home_ja and not HANGUL.search(home_ja), f'올린 뒤 홈 JA 즉시 반영 {HANGUL.findall(home_ja)[:6]}')
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

        # ---------- 내 X 영수증: 단가는 CSV에서 따로 계산 ----------
        pg.set_viewport_size({'width': 1280, 'height': 900})
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(120)
        open_card(pg, 'receipt')
        pg.wait_for_selector('#rc-paper')
        PR = pg.evaluate('XA.PRICE')
        rex = price_expect(sample_posts, sample_present, PR)
        print('  예시 부캐', pexp['id'], '한 방', pexp['hitShow'], '영수증 등급', rex['grade'], '팔로워 가격', rex['headline'])
        rc = pg.evaluate("""() => {
          const paper = document.getElementById('rc-paper');
          const lines = {};
          paper.querySelectorAll('[data-key]').forEach((el) => { lines[el.dataset.key] = { qty: el.dataset.qty || '', sold: el.dataset.sold || '', num: el.dataset.num || '', imp: el.dataset.imp || '', raw: el.dataset.raw || '' }; });
          const head = document.getElementById('rc-headline');
          const sum = document.getElementById('rc-sum');
          const coupon = document.getElementById('rc-coupon');
          const exp = document.getElementById('rc-exp');
          const cheap = document.getElementById('rc-cheap');
          const refund = document.getElementById('rc-refund');
          const period = document.getElementById('rc-period');
          return { lines, grade: paper.dataset.grade, kind: head.dataset.kind, price: head.dataset.price || '',
            sum: sum ? { nf: sum.dataset.nf, imp: sum.dataset.imp } : null,
            coupon: coupon ? { hour: Number(coupon.dataset.hour), pct: Number(coupon.dataset.pct) } : null,
            exp: exp ? { date: exp.dataset.date, qty: Number(exp.dataset.qty) } : null,
            cheap: cheap ? { date: cheap.dataset.date, qty: Number(cheap.dataset.qty) } : null,
            refund: refund ? refund.dataset.qty : null,
            paper: paper.innerText, handle: document.getElementById('rc-handle').textContent,
            from: (period && period.dataset.from) || '', to: (period && period.dataset.to) || '',
            hideLine: document.getElementById('rc-hide-line').checked, hideHandle: document.getElementById('rc-hide-handle').checked,
            sample: !!paper.querySelector('.rc-flag') };
        }""")
        check(rc['grade'] == rex['grade'] and rc['kind'] == 'price' and int(rc['price']) == rex['headline'], f"예시 등급 {rc['grade']} {rex['grade']} 가격 {rc['price']} {rex['headline']}")
        check('total' not in rc['lines'] and 'imp' not in rc['lines'] and rc['refund'] is None, f"단위가 다른 합계·환불 줄 없음 {list(rc['lines'])}")
        for key, line in rex['lines'].items():
            got = rc['lines'].get(key)
            check(got and got.get('sold') != '1' and int(got['qty']) == line['qty'] and abs(float(got['raw']) - line['raw']) < 1e-4 and int(got['imp']) == int(rex['imp']), f"예시 {key} {got} vs {line}")
        check(rc['sum'] and int(rc['sum']['nf']) == int(rex['nf']) and int(rc['sum']['imp']) == int(rex['imp']), f"합계 {rc['sum']}")
        check((rc['coupon'] is None and rex['coupon'] is None) or (rc['coupon'] and rex['coupon'] and rc['coupon']['hour'] == rex['coupon']['hour'] and rc['coupon']['pct'] == rex['coupon']['pct']), f"쿠폰 {rc['coupon']} {rex['coupon']}")
        check((rc['exp'] is None and rex['exp'] is None) or (rc['exp'] and rex['exp'] and rc['exp']['date'] == rex['exp']['date'] and rc['exp']['qty'] == rex['exp']['qty']), f"비싼 팔로워 {rc['exp']} {rex['exp']}")
        check((rc['cheap'] is None and rex['cheap'] is None) or (rc['cheap'] and rex['cheap'] and rc['cheap']['date'] == rex['cheap']['date'] and rc['cheap']['qty'] == rex['cheap']['qty']), f"싼 팔로워 {rc['cheap']} {rex['cheap']}")
        check(rc['from'] == ymd_py(SAMPLE_RC['period'][0]) and rc['to'] == ymd_py(SAMPLE_RC['period'][1]), f"예시 기간 {rc['from']} {rc['to']}")
        check('@' + SAMPLE_RC['handle'] in rc['handle'] and rc['hideLine'] and not rc['hideHandle'] and rc['sample'], '계정은 보이고 첫 줄은 가림, 예시 표시')
        check('합계: 팔로워' in rc['paper'] and '품절' not in rc['paper'] and '번 스침' not in rc['paper'], '같은 단위 합계, 예시에는 품절 없음')
        if rex['exp']:
            exp_post = None
            for p in sample_posts:
                nf = p['nf'] or 0
                if nf < 1 or p['imp'] < 500 or not p['date']:
                    continue
                raw = p['imp'] / nf
                if exp_post is None or raw > exp_post[0]:
                    exp_post = (raw, p)
            snip = first_line_py(exp_post[1]['text']) if exp_post else ''
            if snip:
                check(snip not in rc['paper'], '비싼 글의 첫 줄은 기본으로 안 보임')
        else:
            snip = ''
        pg.screenshot(path=f'{SHOT}/v2_25_receipt_ko.png')
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(200)
        enp = pg.inner_text('#rc-paper')
        check(not HANGUL.search(enp) and 'MY X RECEIPT' in enp and 'THANK YOU FOR POSTING' in enp and 'glances' not in enp and pg.get_attribute('#rc-paper [data-key="likes"]', 'data-qty') == str(rex['lines']['likes']['qty']), f'영수증 EN {HANGUL.findall(enp)[:4]}')
        pg.screenshot(path=f'{SHOT}/v2_26_receipt_en.png')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(200)
        jap = pg.inner_text('#rc-paper')
        check(not HANGUL.search(jap) and 'レシート' in jap and 'すれ違い' not in jap and pg.get_attribute('#rc-paper [data-key="nf"]', 'data-qty') == str(rex['lines']['nf']['qty']), f'영수증 JA {HANGUL.findall(jap)[:4]}')
        pg.screenshot(path=f'{SHOT}/v2_27_receipt_ja.png')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(150)
        caps = pg.evaluate("""() => { const m = XA.receiptModel(XA.last); return { ko: XA.priceCaption(m,'ko'), en: XA.priceCaption(m,'en'), ja: XA.priceCaption(m,'ja') }; }""")
        check(caps['ko'].startswith('제 팔로워 1명 값은 노출 ') and '당신은 얼마?' in caps['ko'] and 'c=price' in caps['ko'] and 'lang=ko' in caps['ko'], '영수증 한국어 공유 문구')
        check(caps['en'].startswith('One follower cost me ') and "What's yours?" in caps['en'] and 'lang=en' in caps['en'], '영수증 영어 공유 문구')
        check(caps['ja'].startswith('フォロワー1人の値段は表示') and 'あなたはいくら？' in caps['ja'] and 'lang=ja' in caps['ja'], '영수증 일본어 공유 문구')
        pg.evaluate("""() => { window.__rcTexts = []; const proto = CanvasRenderingContext2D.prototype; if (!proto.__rcOld) proto.__rcOld = proto.fillText; proto.fillText = function(text){ window.__rcTexts.push(String(text)); return proto.__rcOld.apply(this, arguments); }; window.__opened = []; }""")
        with pg.expect_download() as di:
            pg.click('#rc-save')
        png = open(di.value.path(), 'rb').read()
        rw, rh = struct.unpack('>II', png[16:24])
        drawn = '\n'.join(pg.evaluate('window.__rcTexts'))
        check(png[:8] == b'\x89PNG\r\n\x1a\n' and rw == 1080 and rh == 1350, f'영수증 PNG {rw}x{rh}')
        check('@' + SAMPLE_RC['handle'] in drawn and (not snip or snip not in drawn) and '번 스침' not in drawn, '그림에 계정은 있고 가린 첫 줄·옛 합계 단위는 없음')
        open(f'{SHOT}/v2_25b_receipt_png.png', 'wb').write(png)
        pg.evaluate('window.__rcTexts = []')
        pg.check('#rc-hide-handle'); pg.wait_for_timeout(40)
        check(SAMPLE_RC['handle'] not in pg.inner_text('#rc-paper'), '계정 가리기')
        with pg.expect_download() as di2:
            pg.click('#rc-save')
        drawn2 = '\n'.join(pg.evaluate('window.__rcTexts'))
        check(SAMPLE_RC['handle'] not in drawn2, '그림에서도 계정이 빠짐')
        pg.uncheck('#rc-hide-handle'); pg.wait_for_timeout(40)
        with pg.expect_download() as di3:
            pg.click('#rc-x')
        pg.wait_for_timeout(200)
        opened = pg.evaluate('window.__opened')
        check(opened and opened[-1].startswith('https://x.com/intent/post?text=') and '붙여 넣어' in pg.inner_text('#rc-share-note'), f'영수증 X 공유 {opened[-1][:80]}')
        pg.evaluate("""() => { const p = CanvasRenderingContext2D.prototype; if (p.__rcOld) { p.fillText = p.__rcOld; delete p.__rcOld; } }""")
        pg.evaluate("""() => {
          window.__readReceipt = () => {
            const paper = document.getElementById('rc-paper');
            if (!paper) return { blocked: (document.getElementById('card-dynamic') || {}).innerText || '' };
            const lines = {};
            paper.querySelectorAll('[data-key]').forEach((el) => { lines[el.dataset.key] = { qty: el.dataset.qty || '', sold: el.dataset.sold || '', num: el.dataset.num || '', imp: el.dataset.imp || '', raw: el.dataset.raw || '' }; });
            const head = document.getElementById('rc-headline');
            const sum = document.getElementById('rc-sum');
            const coupon = document.getElementById('rc-coupon');
            const exp = document.getElementById('rc-exp');
            const cheap = document.getElementById('rc-cheap');
            const refund = document.getElementById('rc-refund');
            return { lines, grade: paper.dataset.grade, kind: head ? head.dataset.kind : '', price: head && head.dataset.price || '',
              sum: sum ? { nf: sum.dataset.nf, imp: sum.dataset.imp } : null,
              coupon: coupon ? { hour: Number(coupon.dataset.hour), pct: Number(coupon.dataset.pct) } : null,
              exp: exp ? { date: exp.dataset.date, qty: Number(exp.dataset.qty) } : null,
              cheap: cheap ? { date: cheap.dataset.date, qty: Number(cheap.dataset.qty) } : null,
              refund: refund ? Number(refund.dataset.qty) : null,
              miss: (document.getElementById('rc-miss') || { textContent: '' }).textContent,
              paper: paper.innerText, handle: (document.getElementById('rc-handle') || {}).textContent || '',
              n: XA.last.mode === 'overview' ? XA.last.days.length : XA.last.posts.length, mode: XA.last.mode || 'content' };
          };
          window.__loadReceipt = (csv) => {
            XA.lastOverview = null;
            XA._rcHideSnippet = true;
            XA._rcHideHandle = false;
            if (XA.lang !== 'ko') XA.setLang('ko');
            XA.handleText(csv, false);
            const err = document.getElementById('csv-error');
            if (err && !err.hidden) return { error: err.textContent };
            XA.openCard('receipt');
            return window.__readReceipt();
          };
          window.__loadPersona = (csv) => {
            XA.lastOverview = null;
            XA._psIncludeReplies = false;
            XA._psHideHandle = true;
            XA._psHideSnippet = true;
            if (XA.lang !== 'ko') XA.setLang('ko');
            XA.handleText(csv, false);
            const err = document.getElementById('csv-error');
            if (err && !err.hidden) return { error: err.textContent };
            XA.openCard('persona');
            const card = document.getElementById('ps-card');
            if (!card) return { blocked: (document.getElementById('card-dynamic') || {}).innerText || '' };
            const bars = {};
            card.querySelectorAll('[data-stat]').forEach((el) => { bars[el.dataset.stat] = { bar: el.dataset.bar || '', miss: el.dataset.miss || '' }; });
            const hit = document.getElementById('ps-hit');
            return { id: card.dataset.id, roast: card.dataset.roast, n: Number(card.dataset.n), imp: Number(card.dataset.imp), hit: hit ? (hit.dataset.show || '') : '', bars };
          };
        }""")
        def load_rc(csv):
            return pg.evaluate('(csv) => window.__loadReceipt(csv)', csv)
        def assert_price(label, csv, grade):
            posts, present = parse_post_csv(csv)
            exp = price_expect(posts, present, PR)
            got = load_rc(csv)
            check(not got.get('error') and got.get('grade') == exp['grade'] == grade, f'{label} 등급 화면 {got.get("grade")} 계산 {exp["grade"]} 기대 {grade} {got.get("error","")}')
            check(got.get('kind') == exp['kind'], f'{label} 머리 {got.get("kind")} {exp["kind"]}')
            if exp['headline'] is None:
                check(not got.get('price'), f'{label} 가격 숫자 없음')
            else:
                check(int(got.get('price') or -1) == exp['headline'], f'{label} 가격 {got.get("price")} {exp["headline"]}')
            for key, line in exp['lines'].items():
                g = (got.get('lines') or {}).get(key)
                check(g, f'{label} {key} 줄 없음')
                if not g:
                    continue
                if line['sold']:
                    check(g.get('sold') == '1', f'{label} {key} 품절')
                else:
                    check(int(g['qty']) == line['qty'] and abs(float(g['raw']) - line['raw']) < 1e-4, f'{label} {key} {g} {line}')
            check('total' not in (got.get('lines') or {}) and 'imp' not in (got.get('lines') or {}), f'{label} 옛 합계 키')
            if exp['kind'] == 'price':
                check(got.get('sum') and int(got['sum']['nf']) == int(exp['nf']) and int(got['sum']['imp']) == int(exp['imp']), f'{label} 합계 {got.get("sum")}')
            elif exp['kind'] == 'sold':
                check(got.get('sum') and int(got['sum']['nf']) == 0, f'{label} 팔로워 0 합계')
            else:
                check(got.get('sum') is None, f'{label} 새 팔로우 칸이 없으면 합계 줄 없음')
            if exp['coupon']:
                check(got.get('coupon') and got['coupon']['hour'] == exp['coupon']['hour'] and got['coupon']['pct'] == exp['coupon']['pct'], f'{label} 쿠폰 {got.get("coupon")} {exp["coupon"]}')
            else:
                check(not got.get('coupon'), f'{label} 쿠폰 없음 {got.get("coupon")}')
            if exp['exp']:
                check(got.get('exp') and got['exp']['date'] == exp['exp']['date'] and got['exp']['qty'] == exp['exp']['qty'], f'{label} 비싼 팔로워 {got.get("exp")} {exp["exp"]}')
            return got
        common = dict(spread=True, length=100, likes=10, bm=1, rep=1, rt=1, prof=1, nf=1, imp=100)
        assert_price('첫 손님', posts_csv(build_posts(8, imp=9000, nf=1, likes=10, bm=1, rep=1, prof=1, length=100, spread=True)), 'first')
        assert_price('명품', posts_csv(build_posts(12, **{**common, 'imp': 5000})), 'luxury')
        assert_price('가성비', posts_csv(build_posts(12, **{**common, 'imp': 800})), 'value')
        assert_price('구경꾼', posts_csv(build_posts(12, **{**common, 'imp': 2000, 'prof': 21, 'likes': 100})), 'window')
        assert_price('저장창고', posts_csv(build_posts(12, **{**common, 'imp': 2000, 'prof': 2, 'likes': 100, 'bm': 200})), 'save')
        assert_price('시식', posts_csv(build_posts(12, **{**common, 'imp': 2000, 'prof': 2, 'bm': 4, 'rep': 100})), 'taste')
        assert_price('등급 사이', posts_csv(build_posts(12, **{**common, 'imp': 2000, 'prof': 2, 'bm': 4, 'rep': 4})), 'gap')
        zero = assert_price('팔로워 0', posts_csv(build_posts(12, spread=True, length=100, imp=100, likes=10, bm=1, rep=0, prof=0, nf=0)), 'gap')
        check(zero['lines']['nf']['sold'] == '1' and '품절' in zero['paper'] and 'Infinity' not in zero['paper'], '0으로 나누지 않고 품절')
        miss_cols = [c for c in ['Post id','Date','Post text','Post Link','Impressions','Likes','Reposts','Replies','Bookmarks','Profile visits','URL Clicks']]
        miss = assert_price('새 팔로우 칸 없음', posts_csv(build_posts(12, **common), miss_cols), 'taste')
        check('새 팔로우' in miss['miss'] and '품절' not in miss['paper'], f"없는 칸 이름 {miss['miss']}")
        one = load_rc('Post id,Date,Post text,Post Link,Impressions,Likes,Reposts,Replies,Bookmarks,Profile visits,New follows\n9,"Sat, Aug 8, 2026",only row,https://x.com/solo_user/status/9,7,6,5,4,3,2,1\n')
        one_posts, one_present = parse_post_csv('Post id,Date,Post text,Post Link,Impressions,Likes,Reposts,Replies,Bookmarks,Profile visits,New follows\n9,"Sat, Aug 8, 2026",only row,https://x.com/solo_user/status/9,7,6,5,4,3,2,1\n')
        one_exp = price_expect(one_posts, one_present, PR)
        check(one.get('grade') == 'first' and one_exp['grade'] == 'first' and int(one['lines']['nf']['qty']) == 7 and int(one['lines']['likes']['qty']) == 1 and int(one['lines']['rep']['qty']) == 2 and int(one['lines']['bm']['qty']) == 2 and int(one['lines']['prof']['qty']) == 4 and 'rt' not in one['lines'], f"한 줄 가격 {one.get('lines')}")
        check('@solo_user' in one.get('handle','') and not one.get('coupon') and not one.get('exp'), '한 줄은 시각 칸의 시계를 쿠폰으로 쓰지 않음')
        huge = load_rc('Post id,Post text,Impressions,Likes\n1,big,1234567890,1000000\n')
        check(huge.get('kind') == 'miss' and int(huge['lines']['likes']['qty']) == 1235 and int(huge['lines']['likes']['imp']) == 1234567890 and huge.get('sum') is None and '1,235' in huge.get('paper',''), f"큰 수 {huge.get('lines')}")
        pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(120)
        huge_en = pg.inner_text('#rc-paper')
        check('1,235' in huge_en and 'glances' not in huge_en and not HANGUL.search(huge_en), f'큰 수 EN {HANGUL.findall(huge_en)[:3]}')
        pg.click('[data-lang-toggle] button[data-lang=ja]'); pg.wait_for_timeout(120)
        huge_ja = pg.inner_text('#rc-paper')
        check('1,235' in huge_ja and 'すれ違い' not in huge_ja and not HANGUL.search(huge_ja), f'큰 수 JA')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(100)
        bom = load_rc('\ufeff게시물 ID,날짜,게시물 본문,노출수,마음에 들어요,재게시\n1,2026-01-03,안녕하세요,10,2,0\n')
        enr = load_rc('Post id,Date,Post text,Impressions,Likes,Reposts\n1,2026-01-03,Hello,10,2,0\n')
        jar = load_rc('ポストID,日付,ポスト本文,インプレッション,いいね,リポスト\n1,2026-01-03,こんにちは,10,2,0\n')
        for name, got in (('bom', bom), ('en', enr), ('ja', jar)):
            check(not got.get('error') and int(got['lines']['likes']['qty']) == 5 and got.get('kind') == 'miss' and 'bm' not in got['lines'] and 'nf' not in got['lines'], f"{name} 헤더 가격 {got.get('lines')} {got.get('error')}")
            check('품절' not in got.get('paper','') and '북마크' in got.get('miss','') , f'{name} 없는 칸을 0·품절로 안 적음')
        emo = '😂🔥✨🎉😊🌸👍💡🚀🎵'
        first = emo * 4 + 'ENDSHOULDNOTSHOW'
        snip32 = ''.join(list(first_line_py(first)) )
        emo_rows = build_posts(12, spread=True, length=40, imp=20, nf=0, likes=2, bm=1, rep=1, prof=1)
        emo_rows[0].update({'imp': 800, 'nf': 1, 'text': first + '\nSECRET-SECOND-LINE'})
        em = load_rc(posts_csv(emo_rows))
        check('SECRET-SECOND-LINE' not in em.get('paper','') and 'ENDSHOULDNOTSHOW' not in em.get('paper',''), '긴 첫 줄·둘째 줄은 기본으로 안 보임')
        pg.uncheck('#rc-hide-line'); pg.wait_for_timeout(40)
        shown = pg.inner_text('#rc-exp')
        check(snip32[:12] in shown and 'SECRET-SECOND-LINE' not in shown and 'ENDSHOULDNOTSHOW' not in shown, f'32글자만 {shown[:40]}')
        pg.check('#rc-hide-handle'); pg.wait_for_timeout(40)
        check('example_creator' not in pg.inner_text('#rc-paper'), '이모지 예에서 계정 가리기')
        coup_rows = []
        for i in range(3):
            d = date(2026, 9, 1) + timedelta(days=i)
            coup_rows.append({'id': snow_id(d.year, d.month, d.day, 10, i+1), 'date': date_label(d), 'text': '가'*100, 'imp': 100, 'likes': 1, 'rt': 0, 'rep': 0, 'bm': 0, 'prof': 1, 'nf': 1, 'url': 0})
        for i in range(9):
            d = date(2026, 9, 10) + timedelta(days=i)
            coup_rows.append({'id': snow_id(d.year, d.month, d.day, 15, i+1), 'date': date_label(d), 'text': '가'*100, 'imp': 10, 'likes': 1, 'rt': 0, 'rep': 0, 'bm': 0, 'prof': 1, 'nf': 0, 'url': 0})
        coup = assert_price('쿠폰', posts_csv(coup_rows), 'value')
        check(coup.get('coupon') and coup['coupon']['hour'] == 10 and coup['coupon']['pct'] == 208, f"쿠폰 시간 {coup.get('coupon')}")
        rows = read_rows('sample_overview.csv')
        head = [h.strip() for h in rows[0]]
        ix = {h: i for i, h in enumerate(head)}
        ov_posts, ov_unf = [], 0.0
        for i, r in enumerate(rows[1:]):
            d = parse_csv_date(r[ix['Date']])
            if not d:
                continue
            ov_unf += num_cell(r[ix['언팔로우']])
            ov_posts.append({'i': i, 'id': '', 'text': '', 'date': d, 'reply': False, 'hour': None, 'url': None,
                'imp': num_cell(r[ix['노출수']]), 'likes': num_cell(r[ix['마음에 들어요']]), 'rt': num_cell(r[ix['재게시']]),
                'rep': num_cell(r[ix['답글']]), 'bm': num_cell(r[ix['북마크']]), 'prof': num_cell(r[ix['프로필 조회수']]), 'nf': num_cell(r[ix['새로운 팔로우']])})
        ov_exp = price_expect(ov_posts, {'imp','likes','rt','rep','bm','prof','nf'}, PR)
        ov = pg.evaluate("window.__loadReceipt(XA.SAMPLES['sample_overview.csv'])")
        check(ov.get('mode') == 'overview' and ov.get('n') == OV_RC['n'] == ov_exp['n'], f"개요 일수 {ov.get('n')}")
        check(ov.get('grade') == ov_exp['grade'], f"개요 등급 {ov.get('grade')} {ov_exp['grade']}")
        for key, line in ov_exp['lines'].items():
            g = ov['lines'][key]
            check(int(g['qty']) == line['qty'] and int(g['imp']) == int(OV_RC['sums']['imp']), f"개요 가격 {key} {g['qty']} {line['qty']}")
        check(int(OV_RC['sums']['imp']) != int(OV_RC['act']['imp']) and int(ov['lines']['nf']['imp']) == int(OV_RC['sums']['imp']), '개요는 앞쪽 준비 기간도 더함')
        check(ov.get('refund') == js_round(ov_unf) and ov.get('exp') is None and not ov.get('coupon'), f"언팔로우를 올렸을 때만 환불 {ov.get('refund')} {ov_unf}")
        content_after = posts_csv(build_posts(12, **common))
        both = pg.evaluate("""(csv) => { XA.handleText(csv, false); XA.openCard('receipt'); return window.__readReceipt(); }""", content_after)
        check(both.get('refund') == js_round(ov_unf), '개요를 올린 뒤 글 CSV에도 환불 줄이 남음')
        gone = pg.evaluate("""() => { XA.lastOverview = null; XA.openCard('receipt'); return window.__readReceipt(); }""")
        check(gone.get('refund') is None, '개요를 지우면 환불 줄이 빠짐')

        # ---------- 부캐: 12종류가 모두 나오고 같은 파일이면 같은 결과 ----------
        def load_ps(csv):
            return pg.evaluate('(csv) => window.__loadPersona(csv)', csv)
        def assert_persona(label, rows, expect_id, include=False):
            csv = posts_csv(rows) if isinstance(rows, list) else rows
            posts, present = parse_post_csv(csv)
            exp = persona_expect(posts, present, PC, include_replies=include)
            got = load_ps(csv)
            check(not got.get('error') and not got.get('blocked') and got.get('id') == exp['id'] == expect_id, f'{label} 부캐 화면 {got.get("id")} 계산 {exp["id"]} 기대 {expect_id} {got.get("error") or got.get("blocked")}')
            if not got.get('id'):
                return got
            check(got['n'] == exp['n'] and got['imp'] == js_round(exp['imp']), f'{label} 글·노출 {got["n"]} {exp["n"]}')
            check((got.get('hit') or '') == (exp['hitShow'] or ''), f'{label} 한 방 {got.get("hit")} {exp["hitShow"]}')
            for stat, bar in exp['bars'].items():
                g = got['bars'].get(stat) or {}
                if bar is None:
                    check(g.get('miss') == '1', f'{label} {stat} 없음')
                else:
                    check(g.get('bar') == str(bar), f'{label} {stat} 막대 {g.get("bar")} {bar}')
            return got
        base = dict(spread=True, length=100, imp=100, likes=10, bm=1, rep=1, rt=1, nf=0, prof=1, hour=12)
        assert_persona('저장', build_posts(12, **{**base, 'bm': 20}), 'save')
        assert_persona('댓글', build_posts(12, **{**base, 'rep': 20}), 'chat')
        assert_persona('한방', build_posts(12, **{**base, 'imp': 10, 'spike': 100000}), 'hit')
        assert_persona('개미', build_posts(12, length=100, imp=100, likes=10, bm=1, rep=1, rt=1, nf=0, prof=1, hour=12), 'ant')
        assert_persona('새벽', build_posts(12, **{**base, 'hour': 2}), 'dawn')
        assert_persona('자석', build_posts(12, **{**base, 'imp': 1000, 'nf': 20, 'prof': 100, 'likes': 100, 'bm': 5, 'rep': 5, 'rt': 5}), 'magnet')
        assert_persona('구경', build_posts(12, **{**base, 'imp': 1000, 'prof': 80, 'likes': 50, 'bm': 2}), 'window')
        assert_persona('리포스트', build_posts(12, **{**base, 'rt': 20}), 'repost')
        assert_persona('링크', build_posts(12, **{**base, 'text': 'https://example.com/a' + '가'*79}), 'link')
        assert_persona('한줄', build_posts(12, **{**base, 'text': '가'*12}), 'short')
        assert_persona('장문', build_posts(12, **{**base, 'text': '가'*400}), 'long')
        assert_persona('새싹 8', build_posts(8, **{**base, 'bm': 20}), 'sprout')
        assert_persona('새싹 노출', build_posts(12, **{**base, 'imp': 5, 'bm': 20}), 'sprout')
        assert_persona('점수 없음', build_posts(12, **{**base, 'imp': 200, 'likes': 100, 'bm': 10, 'rep': 10, 'rt': 10, 'prof': 0}), 'sprout')
        plain = build_posts(12, **base)
        replies = build_posts(12, **{**base, 'bm': 20, 'reply': True, 'reply_from': 0})
        mix = plain + replies
        got = assert_persona('답글 제외', mix, 'sprout')
        pg.check('#ps-replies'); pg.wait_for_timeout(80)
        inc_id = pg.get_attribute('#ps-card', 'data-id')
        inc_exp = persona_expect(parse_post_csv(posts_csv(mix))[0], parse_post_csv(posts_csv(mix))[1], PC, include_replies=True)
        check(inc_id == inc_exp['id'] == 'save', f'답글을 넣으면 {inc_id} 계산 {inc_exp["id"]}')
        no_bm = posts_csv(build_posts(12, **base), ['Post id','Date','Post text','Impressions','Likes','Reposts','Replies','Profile visits','New follows'])
        posts, present = parse_post_csv(no_bm)
        exp = persona_expect(posts, present, PC)
        got = load_ps(no_bm)
        check(got.get('id') == exp['id'] and got['bars']['save']['miss'] == '1', f"북마크 없음 {got.get('id')} {exp['id']}")
        det_csv = posts_csv(build_posts(12, **{**base, 'bm': 20}))
        same = pg.evaluate("""(csv) => {
          const rows = XA.parseCSV(csv);
          const a = XA.personaModel(XA.analyze(rows));
          const b = XA.personaModel(XA.analyze([rows[0]].concat(rows.slice(1).reverse())));
          const h1 = XA.personaHash(a && rows.slice(1).map(r => r[0]));
          const h2 = XA.personaHash(rows.slice(1).map(r => r[0]));
          return { ida: a.id, idb: b.id, ra: a.roastIndex, rb: b.roastIndex, hash: h1 === h2 };
        }""", det_csv)
        check(same['ida'] == same['idb'] == 'save' and same['ra'] == same['rb'] and same['hash'], f"같은 파일이면 같은 부캐 {same}")
        bom_ps = ['\ufeff게시물 ID,날짜,게시물 본문,노출수,마음에 들어요']
        for i in range(12):
            d = date(2026, 9, 1) + timedelta(days=i)
            bom_ps.append(f'{snow_id(d.year, d.month, d.day, 12, i+1)},"{date_label(d)}",안녕하세요 오늘도 짧게,{100},{10}')
        bom_csv = '\n'.join(bom_ps) + '\n'
        posts, present = parse_post_csv(bom_csv)
        exp = persona_expect(posts, present, PC)
        got = load_ps(bom_csv)
        check(not got.get('error') and got.get('id') == exp['id'], f"BOM 한글 헤더 부캐 {got.get('id')} {exp['id']} {got.get('error')}")
        emo_ps = build_posts(12, **base)
        emo_ps[3]['text'] = '😂🔥✨🎉😊🌸👍💡' * 5
        posts, present = parse_post_csv(posts_csv(emo_ps))
        exp = persona_expect(posts, present, PC)
        got = load_ps(posts_csv(emo_ps))
        check(got.get('id') == exp['id'] and not got.get('error'), f"이모지 본문 {got.get('id')} {exp['id']}")
        empty = load_rc('')
        check('데이터 줄' in empty.get('error', ''), f"빈 CSV {empty.get('error','')}")
        blocked = pg.evaluate("""() => {
          const a = XA.receiptModel({ map: { imp: 0 }, posts: [], mode: 'content' });
          const b = XA.receiptModel({ map: {}, posts: [{ imp: 3, text: 'x' }], mode: 'content' });
          const c = XA.personaModel({ mode: 'overview', map: { imp: 0 }, posts: [] });
          return { a: a && a.key, b: b && b.key, c: c && c.key };
        }""")
        check(blocked['a'] == 'rc.why.empty' and blocked['b'] == 'rc.why.noImp' and blocked['c'] == 'ps.why.overview', f'빈 결과·노출 없음·개요 부캐는 숫자를 만들지 않음 {blocked}')
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(80)

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
        check(KANA.search(pg.inner_text('#ps-card')) and not HANGUL.search(pg.inner_text('#ps-card')) and not HANGUL.search(pg.inner_text('.tabs')), 'JA 부캐 카드·탭에 한글 없음, 가나 있음')
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
        fp.goto(FILE_URL); fp.click('#btn-sample'); fp.wait_for_selector('#ps-card', timeout=5000); fp.wait_for_timeout(500)
        ok1 = fp.evaluate('XA.last.posts.length') == 94 and fp.locator('#ps-card').count() == 1
        open_card(fp, 'receipt'); fp.wait_for_selector('#rc-paper')
        ok_rc = fp.get_attribute('#rc-paper [data-key="nf"]', 'data-imp') == str(int(SAMPLE_RC['sums']['imp']))
        fp.click('#back-home')
        fp.click('#btn-sample-ov'); fp.wait_for_selector('#overview:not([hidden])', state='attached', timeout=5000)
        fp.set_input_files('#file', f'{ROOT}/sample.csv'); fp.wait_for_selector('#results:not([hidden])', state='attached', timeout=5000)
        fp.click('.tab[data-tab=help]'); fp.click('[data-lang-toggle] button[data-lang=en]')
        check(ok1 and ok_rc and not ferr and not freq and fp.evaluate('document.documentElement.lang') == 'en', f'file:// 로 열어도 샘플·업로드·언어 전환·영수증 동작 (에러 {ferr}, 외부요청 {freq})')
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
        home_fold(s, 360, 640, '360x640 ko')
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360 and not serr, f'360 홈 가로 넘침 없음 ({ow}) {serr}')
        check(s.locator('header [data-lang-toggle]').is_visible() and s.locator('.hub-card').count()==4 and s.locator('#soon-line').count()==1, '360 홈에 언어 버튼, 카드 4장, 준비 중 한 줄')
        s.screenshot(path=f'{SHOT}/v2_22_home_360.png')
        s.set_viewport_size({'width': 360, 'height': 740}); s.wait_for_timeout(40)
        s.click('#btn-sample'); s.wait_for_selector('#ps-card'); s.wait_for_timeout(400)
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360, f'360 부캐 가로 넘침 없음 ({ow})')
        seen = s.evaluate("""() => { const c = document.getElementById('ps-card').getBoundingClientRect(); return { top: c.top, bottom: c.bottom, vh: window.innerHeight }; }""")
        check(seen['top'] < seen['vh'] - 80, f'360에서 부캐 카드 그림이 바로 보임 {seen}')
        s.screenshot(path=f'{SHOT}/v2_33_persona_360.png')
        open_card(s, 'weather'); s.wait_for_timeout(200)
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360, f'360 날씨 가로 넘침 없음 ({ow})')
        s.screenshot(path=f'{SHOT}/v2_23b_weather_360.png')
        s.click('#back-home'); open_card(s, 'receipt'); s.wait_for_timeout(200)
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360, f'360 영수증 가로 넘침 없음 ({ow})')
        check(s.locator('#rc-hide-line').is_checked() and not s.locator('#rc-hide-handle').is_checked() and s.get_attribute('#rc-paper [data-key="nf"]', 'data-imp') == str(int(SAMPLE_RC['sums']['imp'])), '360 영수증 노출 합이 CSV와 같고 첫 줄은 가려져 있음')
        s.screenshot(path=f'{SHOT}/v2_28_receipt_360.png')
        s.click('#back-home'); open_card(s, 'compass'); s.wait_for_timeout(200)
        ow = s.evaluate('document.documentElement.scrollWidth'); check(ow <= 360, f'360 나침반 가로 넘침 없음 ({ow})')
        s.screenshot(path=f'{SHOT}/v2_24_compass_360.png')
        check(not serr, f'360 에러 없음 {serr}')
        b.close()
finally:
    srv.terminate()
print('\n총 실패:', len(fails))
sys.exit(1 if fails else 0)
