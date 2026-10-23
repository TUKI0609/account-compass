# 계정 나침반 · Account Compass (v2)

X(구 트위터) 애널리틱스 CSV를 **브라우저 안에서만** 분석하는 무료 정적 웹 도구입니다. 서버·DB·AI·X API·CDN·쿠키·분석 도구가 없습니다.
X(구 트위터)와 무관한 비공식 도구입니다. / Unofficial tool, not affiliated with X (formerly Twitter).

제작자(credit): tuki(툭이) @Ty_Tuki0609 — https://x.com/Ty_Tuki0609

## 기능
- **CSV 분석**: 게시물별(콘텐츠) CSV → 요약, 방향 제안, 카테고리 표, 훅 키워드, 시리즈 아이디어, TOP/BOTTOM 5, 요일×시간 히트맵. 일별 개요(Overview) CSV를 올리면 자동으로 개요 모드.
  모든 비교는 **올린 사람 자신의 평균** 기준입니다 (특정 계정의 수치를 기준으로 쓰지 않음).
- **복붙 진단**: 글을 붙여 넣으면 100점 체크리스트 (프리미엄 없이 누구나). CSV를 먼저 올렸다면 그 데이터의 시간대·평균과 비교, 아니면 일반적인 경험칙.
- **사용법**: 인라인 SVG 예시 그림으로 단계별 안내 (X 화면·로고를 복제하지 않은 일반적인 그림).
- **한국어 / English / 日本語** 전환 (헤더 한가운데 分段 버튼, localStorage `xa-lang`에 저장, `<html lang>` 변경). 기본 한국어.
- **개인정보·이용 안내**: `privacy.html`.

## 파일
| 파일 | 설명 |
|---|---|
| index.html | 화면 (탭 3개: CSV 분석 / 복붙 진단 / 사용법) |
| privacy.html | 개인정보·이용 안내 (ko/en) |
| style.css | 디자인 (모바일 대응) |
| i18n.js | 번역 사전 `XA.I18N` + `XA.t()` / `XA.setLang()` |
| app.js | CSV 파서·헤더 매칭·분류·통계·히트맵·제안 |
| overview.js | 일별 개요 CSV 분석 |
| diag.js | 복붙 진단 |
| samples.js | 샘플 CSV 2개를 문자열로 내장 (file:// 에서도 동작하도록, fetch 없음) |
| sample.csv / sample_overview.csv | **가상(EXAMPLE) 데이터** — 가상 계정 @example_creator |
| tools/ | 샘플 생성·내장 스크립트, Playwright 테스트 (배포엔 불필요) |

## 로컬에서 보기
`index.html`을 더블클릭(file://)해도 샘플·업로드·언어 전환이 모두 동작합니다. 또는:
```bash
cd x-analyzer && python3 -m http.server 8000   # http://localhost:8000
```

## 언어 추가 (예: 일본어)
`i18n.js`에 `ja: { _name:'日本語', _short:'JA', _locale:'ja-JP', ... }` 블록을 추가하고 `ko`와 같은 키를 모두 채우면 토글 버튼이 자동으로 생깁니다. 빠진 키는 한국어로 대체되고, `tools/test.py`가 ko↔en 키 일치를 검사합니다(ja도 같은 방식으로 검사 추가 가능).
카테고리/훅 판별 키워드는 `app.js`의 `RULES`, `HOOKS`, `TOPIC_DICT`에 있습니다 (한국어 + 영어).

## 지원하는 CSV 헤더 (대소문자·공백·기호 무시, 정확 일치 우선 → 부분 일치)
- 콘텐츠(영문): Post id, Date, Post text, Post Link, Impressions, Likes, Engagements, Bookmarks, Shares, New follows, Replies, Reposts, Profile visits, Detail expands, URL Clicks, Hashtag clicks, Permalink clicks
- 콘텐츠(한국어): 게시물 ID, 날짜, 게시물 본문, 게시물 링크, 노출수, 마음에 들어요, 참여수, 북마크, 공유 수, 새로운 팔로우, 답글, 재게시, 프로필 조회수, 세부정보 펼치기, URL 클릭수, 해시태그 클릭수, 고유 링크 클릭수
- 개요(영문/한국어): Date, Impressions, Likes, Engagements, Bookmarks, Shares, New follows, Unfollows, Replies, Reposts, Profile visits, Create Post, Video views, Media views / 노출수, 마음에 들어요, … 언팔로우, 게시물 작성하기, 동영상 조회수, 미디어 조회수
- 구 Tweet activity, 일본어 헤더(インプレッション, いいね, エンゲージメント, ブックマーク, 共有, 新しいフォロー, 返信, リポスト, プロフィールへのアクセス数 등, 느슨한 일치)도 지원. 구분자(, ; 탭), UTF-8 BOM, EUC-KR 자동 처리.
- 날짜 칸에 시각이 없으면 게시물 ID(snowflake)로 작성 시각을 복원해 KST로 표시.
- 결과 위의 **"인식한 칸"** 줄에 어떤 칸을 읽었는지 / 없는 칸 / 못 알아본 칸이 표시됩니다. X가 CSV 형식을 바꾸면 여기서 바로 드러납니다.

## CSV 내보내기 조건 (2026-10 기준, 반드시 본인 계정에서 확인)
- 애널리틱스 CSV 내보내기는 X **Premium / Premium+** 구독자(또는 인증 조직)만 가능, Basic·무료 계정은 불가 → 복붙 진단 사용.
- X가 2026년 10월에 요금제 이름을 바꿨기 때문에 표기·조건이 다를 수 있습니다.
- PC 웹(x.com/i/account_analytics)이 가장 쉽습니다.

## 배포 (빌드 없음 — 폴더 그대로 올리기)
배포에 필요한 파일: `index.html privacy.html style.css i18n.js app.js overview.js diag.js samples.js sample.csv sample_overview.csv` (tools/·screenshots/ 불필요)

**GitHub Pages**
1. 새 저장소에 위 파일을 올림 → Settings → Pages → Source: Deploy from a branch → `main` / `(root)`.
2. 주의: GitHub **Free** 계정은 Pages를 **공개(public) 저장소**에서만 쓸 수 있습니다 (비공개 저장소는 Pro/Team 등 유료 플랜 필요).
3. 주의: GitHub 이용 약관상 Pages는 **주로 상업적 사업(온라인 비즈니스·전자상거래·SaaS 등)을 위한 무료 호스팅으로 쓰는 것이 허용되지 않습니다.** 무료 개인 도구로는 괜찮지만, 유료화·광고 중심 운영을 계획하면 다른 호스팅을 쓰세요.

**Cloudflare Pages**
1. 대시보드 → Workers & Pages → Create → Pages → **Upload assets(Direct Upload)** → 폴더 드래그 앤 드롭 (또는 Git 저장소 연결, Build command 없음, output directory `/`).
2. 무료 플랜으로 충분하며 저장소를 공개할 필요가 없습니다. 메뉴 이름은 바뀔 수 있으니 최신 문서를 확인하세요.

(Netlify 드래그 앤 드롭도 가능. Vercel Hobby 플랜은 비상업·개인용만 허용.)
배포 후에도 이 도구는 쿠키·분석 스크립트를 넣지 않습니다. 호스팅 업체가 자체적으로 접속 로그를 남길 수는 있습니다(개인정보 안내에 명시).

## 테스트
```bash
python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/python -m playwright install chromium
.venv/bin/python tools/test.py
# 선택: 실제 내 파일로 회귀 테스트 (스크린샷은 찍지 않음, 파일은 복사하지 않음)
REAL_CONTENT=/path/content.csv REAL_OVERVIEW=/path/overview.csv .venv/bin/python tools/test.py
```
샘플을 바꾸면: `python3 tools/gen_sample.py && python3 tools/gen_sample_overview.py && python3 tools/build_samples.py`
