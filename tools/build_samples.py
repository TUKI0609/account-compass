"""sample.csv / sample_overview.csv(가상 @example_creator 데이터)를 samples.js에 문자열로 내장.
→ index.html을 더블클릭(file://)으로 열어도 '샘플 데이터로 보기'가 동작 (fetch 없음).
CSV를 바꾸면 이 스크립트를 다시 실행하세요: python3 tools/build_samples.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = {}
for name in ['sample.csv', 'sample_overview.csv']:
    with open(os.path.join(ROOT, name), encoding='utf-8-sig') as f:
        out[name] = f.read()
js = ('/* 자동 생성 파일 (tools/build_samples.py). 가상 계정 @example_creator의 EXAMPLE 데이터 — 실제 계정 데이터 아님. */\n'
      'window.XA = window.XA || {};\nXA.SAMPLES = ' + json.dumps(out, ensure_ascii=False, indent=0) + ';\n')
with open(os.path.join(ROOT, 'samples.js'), 'w', encoding='utf-8') as f:
    f.write(js)
print('samples.js', len(js), 'bytes')
