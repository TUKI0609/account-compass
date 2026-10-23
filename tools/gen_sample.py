"""EXAMPLE 샘플 데이터 생성기 — 가상의 계정(@example_creator), 가상의 게시물 80개.
X 콘텐츠 분석 CSV(영문 헤더) 형식을 흉내냄. 실제 사람/계정 데이터 아님."""
import csv, random, datetime as dt
random.seed(20261023)
KST = dt.timezone(dt.timedelta(hours=9))
EPOCH = 1288834974657

def snowflake(t):
    ms = int(t.timestamp()*1000)
    return str(((ms-EPOCH) << 22) | random.randint(0, (1<<22)-1))

T = {
 'guide': [
  "돈 쓰기 전에 이거부터 해보세요.\n무료 AI 이미지 툴 5곳 정리\n\n1. 툴A — 하루 크레딧 무료\n2. 툴B — 고해상도 업스케일\n3. 툴C — 배경 제거\n4. 툴D — 스타일 참조\n5. 툴E — 한글 텍스트 OK\n\n프롬프트는 답글에 👇",
  "유튜브 썸네일 3단계로 끝내는 법\n\n1) 레퍼런스 3장 모으기\n2) 아래 프롬프트에 넣기\n3) 글자만 직접 올리기\n\n프롬프트:\n\"bold thumbnail, high contrast, Korean creator style\"",
  "무료로 쓸 수 있는 AI 음악 툴 4곳 정리했어요\n저작권 표기 조건까지 같이 적어둠\n\n1. ...\n2. ...\n3. ...\n4. ...\n\n원문 링크 https://example.com/music-tools",
  "프롬프트 하나로 제품 사진 퀄 올리는 법\n\n복붙용 👇\n\"studio lighting, soft shadow, 85mm, product on marble\"\n\n저장해두고 쓰세요",
  "GPT로 블로그 글 초안 10분 컷 하는 순서\n\n1. 키워드 3개\n2. 목차 먼저 뽑기\n3. 섹션별로 나눠 쓰기\n4. 마지막에 말투 통일\n\n템플릿 링크 https://example.com/blog-template",
  "AI 영상 툴 무료 크레딧 비교 정리 (10월 기준)\n\n툴별 하루 무료량, 워터마크 여부, 상업 이용 가능 여부 표로 만들었어요\n\n👉 https://example.com/video-credit",
  "노션 + AI로 콘텐츠 캘린더 만드는 법 5단계\n\n1. 데이터베이스 생성\n2. 상태 태그\n3. AI 버튼으로 초안\n4. 주간 뷰\n5. 회고 칸\n\n템플릿 공유 https://example.com/notion",
  "초보가 이미지 생성할 때 제일 많이 틀리는 3가지\n\n1. 프롬프트가 너무 짧음\n2. 비율 지정 안 함\n3. 네거티브 프롬프트 안 씀\n\n고친 프롬프트 예시 👇",
  "돈 안 드는 자막 자동 생성 방법 정리\n\n1. 무료 툴 업로드\n2. 자동 자막\n3. 맞춤법만 수정\n\n10분 영상 기준 5분이면 끝",
  "무료 폰트 사이트 6곳 정리 (상업용 OK만)\n\n1. ...\n2. ...\n3. ...\n4. ...\n5. ...\n6. ...\n\n링크 모음 https://example.com/fonts",
  "AI로 로고 시안 뽑을 때 쓰는 프롬프트 공식\n\n[스타일] + [업종] + [색상] + minimal vector logo\n\n예시 3개 답글에 달아둠",
  "돈 쓰기 전에 이거부터: 유료 플랜 결제 전 체크리스트\n\n1. 무료 크레딧으로 테스트\n2. 상업 이용 조건\n3. 해지 방법\n4. 결과물 해상도\n\n저장 추천",
 ],
 'exp': [
  "직접 해본 AI 쇼츠 자동화 7일차\n오늘은 썸네일까지 자동으로 붙여봄\n조회수는 아직 그대로 ㅎㅎ",
  "직접 해본 N잡 실험 14일차\n이번 주 수익 0원 → 3,200원\n뭐가 달라졌는지 정리해볼게요",
  "AI로 동화책 한 권 만들어봤어요\n그림 24장, 걸린 시간 6시간\n제작기 스레드 🧵",
  "이미지 생성만으로 굿즈 만들기 도전 3일차\n시안 40개 뽑고 2개 남김",
  "AI 캐릭터로 인스타 계정 키우기 실험 21일차\n팔로워 12 → 87",
  "음성 클로닝으로 팟캐스트 만들어봤는데 생각보다 자연스러움\n후기 남겨요",
  "직접 해본 프롬프트 A/B 테스트 결과\n같은 주제 10개 뽑아서 비교함",
  "AI로 웹툰 4컷 만들어보기 2일차\n캐릭터 일관성이 제일 어렵다",
 ],
 'video': [
  "AI로 만든 15초 광고 영상 🎬\n소리 켜고 보세요",
  "이 영상 전부 AI로 만들었어요\n제작 시간 2시간",
  "뮤비 느낌으로 만들어본 AI 영상 클립",
  "AI 영상 툴로 만든 고양이 단편 🐱",
  "새벽에 만든 AI 시네마틱 영상",
  "AI로 만든 여행 브이로그 영상 (실제로 안 감)",
 ],
 'daily': [
  "오늘 점심은 김치찌개\n오후도 힘내봅시다",
  "주말인데 결국 작업함 ㅎㅎ",
  "커피 세 잔째... 오늘 밤샘 각",
  "퇴근하고 산책했는데 날씨 너무 좋다",
  "요즘 잠을 너무 못 잤다 오늘은 일찍 자야지",
  "비 오는 날엔 작업이 잘 됨",
 ],
 'news': [
  "· 이미지 모델 신버전 출시\n· 한글 텍스트 렌더링 개선\n· 무료 사용자도 일부 사용 가능",
  "속보) 영상 생성 툴 업데이트 공개\n최대 길이 늘어남",
  "AI 업계 이번 주 소식 3줄 요약\n· 모델 발표\n· 가격 변경\n· 신기능 공개",
  "음악 생성 AI 새 버전 발표됐네요",
  "검색 AI 기능 업데이트 소식\n· 출처 표시 강화",
 ],
 'quote': [
  "ㅋㅋㅋㅋ 이건 진짜 미쳤다",
  "와 이거 대박이네요",
  "ㄷㄷ 퀄리티 실화냐",
  "이게 AI라고?",
  "ㅋㅋ 공감 100%",
  "와 미쳤다 이거",
 ],
 'other': [
  "여러분은 요즘 어떤 AI 툴 제일 많이 쓰세요?",
  "팔로워 1,000명 감사합니다 🙏",
  "다음 주에 뭐 다뤄볼까요?",
 ],
}
# 목표 수치: 실제 계정과 무관한, 손으로 정한 가상값 (카테고리 간 차이가 보이도록만 설정)
P = {  # n, median imp, bookmark rate, like rate, engagement rate
 'guide': (22, 1500, 0.0120, 0.020, 0.045),
 'exp':   (14, 1000, 0.0050, 0.018, 0.035),
 'video': (10, 1400, 0.0015, 0.012, 0.022),
 'daily': (10, 800,  0.0010, 0.015, 0.025),
 'news':  (10, 1200, 0.0020, 0.008, 0.018),
 'quote': (10, 4000, 0.0003, 0.0015, 0.003),
 'other': (4,  600,  0.0012, 0.014, 0.030),
}
rows = []
start = dt.datetime(2026, 9, 24, tzinfo=KST)
for cat, (n, med, br, lr, er) in P.items():
    for i in range(n):
        day = random.randint(0, 29)
        hr = random.choices(range(24), weights=[2,1,1,1,1,1,1,2,3,4,4,4,5,6,6,6,6,5,4,5,6,6,5,3])[0]
        t = start + dt.timedelta(days=day, hours=hr, minutes=random.randint(0, 59))
        imp = med * random.lognormvariate(0, 0.55)
        if 0 <= hr < 6: imp *= 0.45
        lmul = 1.5 if 19 <= hr <= 22 else 1.0  # 가상: 저녁 시간대가 반응이 좋은 계정으로 설정
        imp = int(imp)
        b = max(0, round(imp * br * random.uniform(0.6, 1.4)))
        likes = max(0, round(imp * lr * lmul * random.uniform(0.6, 1.4)))
        rep = max(0, round(likes * random.uniform(0.05, 0.25)))
        rt = max(0, round(likes * random.uniform(0.03, 0.15)))
        sh = max(0, round(b * random.uniform(0.0, 0.2)))
        det = max(0, round(imp * er * 0.35 * random.uniform(0.5, 1.5)))
        prof = max(0, round(imp * er * 0.12 * random.uniform(0.5, 1.5)))
        url = max(0, round(imp * 0.004 * random.uniform(0, 2))) if 'http' in T[cat][i % len(T[cat])] else 0
        eng = likes + rep + rt + b + sh + det + prof + url
        if cat == 'quote':
            eng = max(likes + rep + rt + b, round(imp * er * random.uniform(0.7, 1.3)))
        nf = max(0, round(prof * random.uniform(0.05, 0.3)))
        pid = snowflake(t)
        rows.append((t, [pid, t.strftime('%a, %b %d, %Y'), T[cat][i % len(T[cat])],
                         f"https://x.com/example_creator/status/{pid}", imp, likes, eng, b, sh, nf,
                         rep, rt, prof, det, url, 0, 0]))
rows.sort(key=lambda r: r[0], reverse=True)
H = ["Post id","Date","Post text","Post Link","Impressions","Likes","Engagements","Bookmarks","Shares",
     "New follows","Replies","Reposts","Profile visits","Detail Expands","URL Clicks","Hashtag Clicks","Permalink Clicks"]
import os
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sample.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(H)
    for _, r in rows: w.writerow(r)
print(len(rows), 'rows')
