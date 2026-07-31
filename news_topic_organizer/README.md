# News Topic Organizer (뉴스 기사 주제별 정리기)

뉴스 기사를 넣으면 **주제별로 자동 분류·정리**해주는 파이썬 도구입니다.
외부 라이브러리 없이 표준 라이브러리만으로 동작합니다.

## 기본 제공 주제

정치 · 경제 · 사회 · IT/과학 · 스포츠 · 문화 · 국제 · 건강 (매칭 실패 시 `기타`)

한국어/영어 키워드 사전을 기반으로 분류하며, 제목에 등장한 키워드는
본문보다 3배 가중치를 받습니다. 주제 사전은 JSON 파일로 자유롭게
교체할 수 있습니다.

## 설치 없이 바로 실행

```bash
cd news_topic_organizer

# 샘플 기사를 주제별로 정리해 Markdown으로 출력
python -m news_topic_organizer examples/articles

# JSON 형식으로 파일에 저장
python -m news_topic_organizer examples/articles --format json -o result.json

# 표준입력으로 기사 전달 (여러 기사는 '---' 줄로 구분)
cat my_news.txt | python -m news_topic_organizer -

# 사용자 정의 주제 사전 사용
python -m news_topic_organizer articles/ --topics my_topics.json
```

## 입력 형식

**텍스트(.txt)** — 첫 줄이 제목, 나머지가 본문. `---` 구분선으로 한
파일에 여러 기사를 담을 수 있습니다.

```
코스피 2,800선 회복
국내 증시가 상승 마감했다. ...
---
손흥민 시즌 20호 골
손흥민이 리그 경기에서 ...
```

**JSON(.json)** — 기사 객체 하나 또는 배열.

```json
[
  {
    "title": "한국은행 기준금리 동결",
    "body": "금융통화위원회가 ...",
    "source": "연합경제",
    "date": "2026-07-30"
  }
]
```

디렉터리를 넘기면 내부의 `.txt`/`.json` 파일을 재귀적으로 모두 읽습니다.

## 사용자 정의 주제 사전

`{"주제이름": ["키워드", ...]}` 형태의 JSON 파일을 `--topics`로 넘기면
기본 사전 대신 사용됩니다.

```json
{
  "날씨": ["폭염", "장마", "태풍", "미세먼지"],
  "부동산": ["아파트", "전세", "청약", "재건축"]
}
```

## 파이썬 API

```python
from news_topic_organizer import Article, NewsOrganizer

articles = [
    Article(title="코스피 상승 마감", body="증시가 금리 기대감에 올랐다."),
    Article(title="야구 결승전 승리", body="홈런으로 우승을 확정했다."),
]

organizer = NewsOrganizer()
groups = organizer.organize(articles)          # 주제 -> 기사 목록 (OrderedDict)
print(organizer.to_markdown(groups))           # Markdown 리포트
print(organizer.to_json(groups))               # JSON 리포트
```

## 테스트

```bash
cd news_topic_organizer
python -m unittest discover tests -v
```

## 프로젝트 구조

```
news_topic_organizer/
├── news_topic_organizer/
│   ├── models.py        # Article, ClassifiedArticle 데이터 모델
│   ├── classifier.py    # 키워드 기반 주제 분류기 (기본 주제 사전 포함)
│   ├── loader.py        # .txt/.json/디렉터리 입력 로더
│   ├── organizer.py     # 주제별 그룹화 + Markdown/JSON 리포트
│   └── cli.py           # 커맨드라인 인터페이스
├── examples/articles/   # 샘플 뉴스 기사
└── tests/               # 단위 테스트
```
