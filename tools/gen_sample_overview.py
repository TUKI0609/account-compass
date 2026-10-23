"""EXAMPLE 일별 개요 샘플 — 가상 계정 숫자(실제 데이터 아님). X 개요 CSV(한국어 헤더) 형식 흉내."""
import csv, random, datetime as dt
random.seed(7)
H = ["Date","노출수","마음에 들어요","참여수","북마크","공유 수","새로운 팔로우","언팔로우","답글","재게시","프로필 조회수","게시물 작성하기","동영상 조회수","미디어 조회수"]
end = dt.date(2026, 10, 22); rows = []
for i in range(35):
    d = end - dt.timedelta(days=i)
    if i >= 30:  # 활동 시작 전 준비 기간
        imp = random.randint(40, 150); rows.append([d, imp, 0, random.randint(0, 2), 0, 0, random.randint(0, 1), random.randint(0, 1), 0, 0, random.randint(0, 1), 0, 0, 0]); continue
    posts = random.choice([1, 2, 2, 3, 3, 4, 5, 6])
    imp = int(posts * random.uniform(1200, 3200) * (4 if random.random() < 0.12 else 1))
    likes = int(imp * random.uniform(0.008, 0.02)); eng = int(likes * random.uniform(2, 2.6))
    bm = int(imp * random.uniform(0.0005, 0.006)); nf = int(imp * random.uniform(0.0008, 0.004)) + (30 if i == 29 else 0)
    rows.append([d, imp, likes, eng, bm, int(bm * 0.1), nf, random.randint(0, max(1, nf // 4)), int(likes * 0.3), int(likes * 0.15), int(imp * 0.004), posts, random.randint(0, 300), random.randint(0, 600)])
import os
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sample_overview.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, quoting=csv.QUOTE_MINIMAL); w.writerow(H)
    for r in rows: w.writerow([f"{r[0]:%a, %b} {r[0].day}, {r[0].year}"] + r[1:])
print(len(rows), 'rows')
