"""자동 테스트 (Playwright + 로컬 서버 + file://).
- 샘플 로드 / 파서 변형(한국어·영어·일본어·구 Tweet activity) / 영어 헤더 / 영어 카테고리 규칙
- i18n: ko 키가 전부 en에 있음, 화면에 쓰는 키가 전부 사전에 있음, 언어 토글·저장·<html lang>
- 실제 데이터 흔적 없음(소유자 이름은 제작자 표시에만), file:// 동작, 외부 요청 없음
- v2 스크린샷(가상 샘플 데이터만) → screenshots/v2_*.png
실제 파일 회귀 테스트(선택): REAL_CONTENT=/path REAL_OVERVIEW=/path  — 실제 파일은 스크린샷을 찍지 않음.
실행: .venv/bin/python tools/test.py   (x-analyzer 폴더 또는 그 상위 폴더에서)"""
import subprocess, time, sys, json, os, re, glob
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
HANGUL = re.compile(r'[가-힣]')
RAWKEY = re.compile(r'\b(?:ov|sug|diag|kpi|col|cat|hook|th|series|heat|rank|howto|ill|privacy|err|results|reply|unit|metric|colinfo|notice|credit)\.[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*\b')
SITE_FILES = ['index.html', 'privacy.html', 'style.css', 'i18n.js', 'app.js', 'diag.js', 'overview.js', 'samples.js']

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

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
        pg = ctx.new_page()
        errs, ext = [], []
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('request', lambda r: (not r.url.startswith(URL)) and not r.url.startswith('data:') and ext.append(r.url))
        pg.goto(URL); pg.wait_for_timeout(300)

        # ---------- i18n 사전 검사 ----------
        keys = pg.evaluate("(()=>{const I=XA.I18N;const k=Object.keys(I.ko).filter(x=>!x.startsWith('_'));return {ko:k,langs:Object.keys(I),miss:Object.fromEntries(Object.keys(I).map(l=>[l,k.filter(x=>!(x in I[l]))])),meta:Object.keys(I).every(l=>I[l]._name&&I[l]._locale&&I[l]._short)}})()")
        check(set(keys['langs']) >= {'ko', 'en'} and keys['meta'], f"언어 목록 {keys['langs']} + _name/_short/_locale")
        check(not keys['miss']['en'], f"모든 ko 키가 en에 있음 (빠진 키 {keys['miss']['en'][:10]})")
        en_extra = pg.evaluate("Object.keys(XA.I18N.en).filter(k=>!(k in XA.I18N.ko))")
        check(not en_extra, f'en에만 있는 키 없음 {en_extra[:10]}')
        empty = pg.evaluate("Object.entries(XA.I18N).flatMap(([l,d])=>Object.entries(d).filter(([k,v])=>typeof v!=='string'||!v.trim()).map(([k])=>l+':'+k))")
        check(not empty, f'빈 번역 없음 {empty[:10]}')
        # 화면·코드에서 쓰는 키가 사전에 있는지 (정적 + 동적 키)
        used = set()
        for f in ['index.html', 'privacy.html']:
            used |= set(re.findall(r'data-i18n(?:-html|-placeholder|-title)?="([^"]+)"', open(os.path.join(ROOT, f), encoding='utf-8').read()))
        for f in ['app.js', 'diag.js', 'overview.js', 'i18n.js']:
            src = open(os.path.join(ROOT, f), encoding='utf-8').read()
            used |= set(re.findall(r"\bt\('([\w.]+)'", src)) | set(re.findall(r"XA\.err\('([\w.]+)'", src)) | set(re.findall(r"'(diag\.grade\.[abcd])'", src))
        dyn = pg.evaluate("""(()=>{const k=[];XA.CATS.concat(['reply']).forEach(c=>k.push('cat.'+c));XA.HOOKS.forEach(h=>k.push('hook.'+h[0]));Object.keys(XA.ALIAS).forEach(c=>k.push('col.'+c));
          for(let d=0;d<7;d++){k.push('day.'+d,'dayFull.'+d)};['cat','n','share','medImp','avgLikes','avgBm','er','br','nfr','prof','hook','used','hookImp','hookLikes','hookBr','lift'].forEach(x=>k.push('th.'+x));
          ['dow','days','imp','eng','bm','net','posts','bucket','medImp','ipp','medNet','er'].forEach(x=>k.push('ov.th.'+x));['0','1to3','4plus'].forEach(x=>k.push('ov.bucket.'+x));
          ['take','hook','len','time','media','end'].forEach(x=>k.push('diag.c.'+x));['prompt','list','steps','link'].forEach(x=>k.push('diag.take.'+x));['image','video','gif'].forEach(x=>k.push('diag.media.'+x));
          ['free','beforePay','prompt'].forEach(x=>k.push('serhook.'+x));return k})()""")
        used |= set(dyn)
        used = {k for k in used if not k.endswith('.')}  # t('cat.'+id) 같은 동적 접두어는 위 dyn에서 따로 검사
        missing_used = sorted(k for k in used if k not in keys['ko'])
        check(not missing_used, f'화면/코드에서 쓰는 키 {len(used)}개 전부 사전에 있음 (없는 키 {missing_used[:10]})')
        check(pg.evaluate('document.documentElement.lang') == 'ko', '기본 언어 ko, <html lang="ko">')

        # ---------- 제작자 표시 ----------
        cr = pg.evaluate("""(()=>{const a=document.querySelector('.topbar .credit-btn');const c=document.querySelector('.topbar .credit');const r=c.getBoundingClientRect();
          return {href:a.href,target:a.target,rel:a.rel,text:c.innerText.replace(/\\s+/g,' ').trim(),fs:parseFloat(getComputedStyle(c).fontSize),right:r.right,top:r.top,h:r.height,vw:innerWidth}})()""")
        check(cr['href'] == 'https://x.com/Ty_Tuki0609' and cr['target'] == '_blank' and 'noopener' in cr['rel'], f'제작자 링크 새 탭 + noopener {cr}')
        check('제작자: tuki(툭이) @Ty_Tuki0609' in cr['text'] and cr['fs'] <= 12.5 and cr['right'] > cr['vw'] * 0.6 and cr['top'] < 30, f"제작자 표시 작게 오른쪽 위 ({cr['text']}, {cr['fs']}px)")
        check('X(구 트위터)와 무관한 비공식 도구입니다' in pg.inner_text('body'), '비공식 도구 안내 (ko)')

        # ---------- 홈 스크린샷 ----------
        pg.screenshot(path=f'{SHOT}/v2_01_home_ko.png')

        # ---------- 샘플 (내장 samples.js) ----------
        pg.click('#btn-sample'); pg.wait_for_selector('#results:not([hidden])'); pg.wait_for_timeout(800)
        n = pg.evaluate('XA.last.posts.length'); check(n == 80, f'샘플 게시물 수 {n}')
        cats = pg.evaluate('Object.entries(XA.last.posts.reduce((a,p)=>(a[p.cat]=(a[p.cat]||0)+1,a),{}))'); print('  카테고리 분포', cats)
        check(pg.evaluate("XA.last.timeSrc.id") == 80, 'ID→시각 복원 80개')
        check(pg.locator('#cat-table tbody tr').count() >= 6, '카테고리 표 6행 이상')
        check(pg.locator('#top5 li').count() == 5 and pg.locator('#bottom5 li').count() == 5, 'TOP/BOTTOM 5')
        check(pg.locator('#suggest .sug').count() >= 3, f"제안 {pg.locator('#suggest .sug').count()}개")
        check(pg.locator('#series .ser').count() == 3, '시리즈 3개')
        check(pg.locator('.heat .c').count() == 168, '히트맵 168칸')
        ci = pg.inner_text('#col-info'); check('인식한 칸(17개)' in ci and '없는 칸: 없음' in ci, f'인식한 칸 표시 유지: {ci[:80]}')
        print('  제안:', pg.eval_on_selector_all('#suggest .t', 'els=>els.map(e=>e.textContent)'))
        print('  시리즈:', pg.eval_on_selector_all('#series .t', 'els=>els.map(e=>e.textContent)'))
        for m in ['likes', 'bm', 'er', 'nf', 'prof']: pg.select_option('#rank-metric', m)
        for m in ['imp', 'n']: pg.select_option('#heat-metric', m)
        pg.select_option('#rank-metric', 'imp'); pg.select_option('#heat-metric', 'likes')
        pg.evaluate("document.querySelector('#results').scrollIntoView();window.scrollBy(0,-100)"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SHOT}/v2_03_results_ko.png')
        pg.screenshot(path=f'{SHOT}/v2_03b_results_ko_full.png', full_page=True)

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

        # ---------- 개요 샘플 ----------
        pg.click('#btn-sample-ov'); pg.wait_for_selector('#overview:not([hidden])'); pg.wait_for_timeout(300)
        check(pg.is_hidden('#results') and pg.locator('#overview .kpi').count() == 8, '개요 샘플: 결과 영역 전환 + KPI 8개')
        check(pg.evaluate('XA.last.pre.length') == 5, '개요 샘플: 준비 기간 5일 제외')
        check('인식한 칸' in pg.inner_text('#ov-col-info'), '개요에도 인식한 칸 표시')
        pg.evaluate("document.querySelector('#overview').scrollIntoView();window.scrollBy(0,-100)"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SHOT}/v2_08_overview_ko.png')
        pg.click('#btn-sample'); pg.wait_for_selector('#results:not([hidden])'); check(pg.is_hidden('#overview'), '콘텐츠 샘플로 돌아오면 개요 숨김')
        pg.set_input_files('#file', f'{ROOT}/sample.csv'); pg.wait_for_timeout(500)
        check(pg.is_hidden('#sample-banner'), '파일 업로드 시 샘플 배너 숨김')
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
        pg.click('.tab[data-tab=help]'); pg.wait_for_timeout(200)
        htxt = pg.inner_text('#tab-help')
        check(pg.locator('#tab-help svg.ill').count() == 7, f"사용법 그림 7개 ({pg.locator('#tab-help svg.ill').count()})")
        for s in ['Premium', 'Premium+', 'Basic', '인증 조직', '2026년 10월', '예시 그림', 'PC 웹이 가장 쉬워요', '인식한 칸', '복붙 진단']:
            check(s in htxt, f'사용법에 "{s}"')
        pg.screenshot(path=f'{SHOT}/v2_02_howto.png', full_page=True)

        # ---------- 언어 전환 ----------
        pg.click('.tab[data-tab=csv]'); pg.click('[data-lang-toggle] button[data-lang=en]'); pg.wait_for_timeout(500)
        check(pg.evaluate('document.documentElement.lang') == 'en' and pg.evaluate("localStorage.getItem('xa-lang')") == 'en', 'EN 전환: <html lang=en> + localStorage 저장')
        body = pg.inner_text('body')
        check('Unofficial tool, not affiliated with X (formerly Twitter)' in body and 'Made by tuki(툭이) @Ty_Tuki0609' in re.sub(r'\s+', ' ', pg.inner_text('.topbar')), '영어 비공식 안내 + 제작자 표시')
        for sel in ['#summary', '#cat-table', '#hook-table', '#col-info', '.tabs', '#suggest', '#rank-metric', '#heat-metric', '#time-src', '#hour-blocks']:
            tx = pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}').cloneNode(true);return e.textContent}})()")
            # 제안 카드에는 샘플 본문의 한국어 소재가 따옴표로 들어갈 수 있음 → 카테고리 이름 외 한글 없음
            check(not HANGUL.search(tx), f'EN 모드 {sel} 한글 없음 {HANGUL.findall(tx)[:5]}')
        check(not RAWKEY.search(body), f'EN 모드 빠진 번역 키 노출 없음 {RAWKEY.findall(body)[:5]}')
        pg.evaluate("document.querySelector('#results').scrollIntoView();window.scrollBy(0,-100)"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{SHOT}/v2_06_results_en.png')
        pg.reload(); pg.wait_for_timeout(400)
        check(pg.evaluate('document.documentElement.lang') == 'en' and 'Account Compass' in pg.inner_text('.brand'), '새로고침 후 EN 유지')
        pg.screenshot(path=f'{SHOT}/v2_04_home_en.png')
        pg.click('.tab[data-tab=help]'); pg.wait_for_timeout(200)
        h_en = pg.inner_text('#tab-help')
        check(not HANGUL.search(h_en), f'EN 사용법 한글 없음 {HANGUL.findall(h_en)[:5]}')
        check(all(s in h_en for s in ['Premium+', 'verified organizations', 'Basic', 'October 2026', 'Illustrative', 'Desktop web is easiest']), 'EN 사용법 핵심 안내')
        pg.screenshot(path=f'{SHOT}/v2_02b_howto_en.png', full_page=True)
        pg.click('.tab[data-tab=diag]'); pg.click('#d-ex'); pg.click('#d-run'); pg.wait_for_timeout(200)
        sc = int(pg.text_content('.ring text')); dtx = pg.inner_text('#d-result')
        check(sc >= 80 and 'Takeaway' in dtx and not HANGUL.search(dtx), f'EN 진단 (예시 {sc}점, 한글 없음)')
        pg.click('.tab[data-tab=csv]'); pg.click('#btn-sample-ov'); pg.wait_for_selector('#overview:not([hidden])'); pg.wait_for_timeout(300)
        otx = pg.inner_text('#overview'); check(not HANGUL.search(otx) and not RAWKEY.search(otx), f'EN 개요 한글/키 노출 없음 {HANGUL.findall(otx)[:5]}')
        pg.goto(URL + 'privacy.html'); pg.wait_for_timeout(200)
        ptx = pg.inner_text('body'); check('Privacy & terms' in ptx and 'never uploaded' not in '' and not RAWKEY.search(ptx), 'EN 개인정보 페이지')
        pg.screenshot(path=f'{SHOT}/v2_10_privacy_en.png', full_page=True)
        pg.click('[data-lang-toggle] button[data-lang=ko]'); pg.wait_for_timeout(200)
        ptx = pg.inner_text('body'); check('브라우저 안에서만' in ptx and '쿠키' in ptx and pg.evaluate('document.documentElement.lang') == 'ko', 'KO 개인정보 페이지 + 다시 ko')
        pg.goto(URL); pg.wait_for_timeout(200)
        check(pg.evaluate('document.documentElement.lang') == 'ko', 'ko 선택도 저장됨')
        check(not errs, f'콘솔 에러 없음 {errs}')
        check(not ext, f'외부 요청 없음 {ext}')

        # ---------- file:// (더블클릭으로 열기) ----------
        fp = b.new_page(); ferr, freq = [], []
        fp.on('pageerror', lambda e: ferr.append(str(e))); fp.on('console', lambda m: m.type == 'error' and ferr.append(m.text))
        fp.on('request', lambda r: (not r.url.startswith('file://')) and not r.url.startswith('data:') and freq.append(r.url))
        fp.goto(FILE_URL); fp.click('#btn-sample'); fp.wait_for_selector('#results:not([hidden])', timeout=5000); fp.wait_for_timeout(500)
        ok1 = fp.evaluate('XA.last.posts.length') == 80
        fp.click('#btn-sample-ov'); fp.wait_for_selector('#overview:not([hidden])', timeout=5000)
        fp.set_input_files('#file', f'{ROOT}/sample.csv'); fp.wait_for_selector('#results:not([hidden])', timeout=5000)
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
            pg.set_input_files('#file', RC); pg.wait_for_selector('#results:not([hidden])'); pg.wait_for_timeout(900)
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
            mr.goto(URL); mr.set_input_files('#file', RC); mr.wait_for_selector('#results:not([hidden])'); mr.wait_for_timeout(700)
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
        mc = m.evaluate("(()=>{const c=document.querySelector('.topbar .credit').getBoundingClientRect();const t=document.querySelector('.tabs').getBoundingClientRect();return {cr:c.right,ct:c.top,ch:c.height,tb:t.bottom,vw:innerWidth}})()")
        check(mc['cr'] <= mc['vw'] and mc['ch'] <= 32 and mc['tb'] < 160, f'모바일 헤더: 제작자 한두 줄 + 탭 ({mc})')
        m.screenshot(path=f'{SHOT}/v2_05_mobile.png')
        m.click('#btn-sample'); m.wait_for_selector('#results:not([hidden])'); m.wait_for_timeout(800)
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 가로 넘침 없음 (scrollWidth {ow})')
        m.evaluate("document.querySelector('#results').scrollIntoView();window.scrollBy(0,-130)"); m.wait_for_timeout(300)
        m.screenshot(path=f'{SHOT}/v2_05b_mobile_results.png')
        m.click('.tab[data-tab=help]'); m.wait_for_timeout(200)
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 사용법 가로 넘침 없음 ({ow})')
        m.screenshot(path=f'{SHOT}/v2_05c_mobile_howto.png', full_page=True)
        m.click('[data-lang-toggle] button[data-lang=en]'); m.wait_for_timeout(200); m.evaluate('window.scrollTo(0,0)')
        ow = m.evaluate('document.documentElement.scrollWidth'); check(ow <= 392, f'모바일 EN 가로 넘침 없음 ({ow})')
        m.screenshot(path=f'{SHOT}/v2_05d_mobile_en.png')
        m.click('.tab[data-tab=diag]'); m.click('#d-ex'); m.click('#d-run'); m.wait_for_timeout(200)
        check(not merr, f'모바일 에러 없음 {merr}')
        b.close()
finally:
    srv.terminate()
print('\n총 실패:', len(fails))
sys.exit(1 if fails else 0)
