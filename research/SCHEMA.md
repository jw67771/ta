# 스키마 정의

모든 노트는 **YAML front matter + Markdown 본문** 구조입니다.

```
---
type: video
title: ...
---

## 본문은 여기부터
```

문서 종류는 세 가지이고, 디렉터리로 구분합니다.

| 종류 | 디렉터리 | `type` | 파일명 규칙 | 한 파일이 담는 것 |
|---|---|---|---|---|
| 영상 노트 | `videos/` | `video` | `YYYY-MM-DD-<slug>.md` | 영상 하나의 원본 기록 |
| 종목 분석 | `stocks/` | `stock` | `<TICKER>.md` | 한 종목에 대한 의견의 누적 이력 |
| 투자 원칙 | `philosophy/` | `principle` | `<id>.md` | 반복해서 나타나는 원칙 하나 |

`_`로 시작하는 파일(`_template.md`)은 검증·색인에서 제외됩니다.
슬라이드·차트 캡처 이미지는 `assets/`에 두고 노트 본문에서 상대경로로 링크합니다 (`assets/README.md` 참고).

---

## 1. 영상 노트 (`videos/`)

**이 저장소의 사실 근거(source of truth)입니다.** 종목 분석과 투자 원칙은 반드시 영상 노트를
`source`로 참조해야 하며, 참조 없는 주장은 검증에서 걸러집니다.

```yaml
---
type: video
title: "영상 제목 그대로"
url: https://www.youtube.com/watch?v=XXXXXXXXXXX   # 선택 (멤버십 전용이면 생략)
video_id: XXXXXXXXXXX        # 선택
channel: 성환김
series: 한 눈에 보는 멤버십 강의   # 선택. 연속 강의일 때
episode: 1                   # 선택. series가 있을 때만
access: membership           # 선택. public | membership
published: 2026-08-20        # 선택. 모르면 비워 둘 것
captured: 2026-08-31         # 내가 정리한 날짜
source: transcript           # transcript | summary | manual | slides
confidence: high             # high | medium | low
tickers: ["005930", AAPL]    # 선택. 영상에서 '다룬' 종목
mentioned: [BRK.B, GOOGL]    # 선택. 맥락상 '언급된' 종목 (고객사·경쟁사 등)
topics: [밸류에이션, 반도체]   # 선택
---
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `type` | O | `video` 고정 |
| `title` | O | 영상 제목. 임의로 바꾸지 말 것 |
| `captured` | O | 정리한 날짜. `published`보다 빠를 수 없음 |
| `source` | O | `transcript`(자막) / `summary`(요약본) / `manual`(시청 메모) / `slides`(슬라이드 캡처) |
| `confidence` | O | 원문 확보 정확도. 자막·슬라이드 원문이면 `high`, 기억에 의존하면 `low` |
| `url` | X | 원본 링크. 있으면 `http`로 시작해야 함 |
| `published` | X | 영상 공개일. **알 때만** 채운다 (아래 파일명 규칙 참고) |
| `series` / `episode` | X | 연속 강의의 시리즈명과 화 번호(정수). `episode`는 단독으로 쓸 수 없음 |
| `access` | X | `public` / `membership`. 링크가 없는 이유가 멤버십 전용이면 명시 |
| `video_id` | X | 유튜브 영상 ID |
| `channel` | X | 채널명 |
| `tickers` | X | 영상에서 **다룬** 종목. 대응하는 `stocks/<티커>.md`가 없으면 경고 |
| `mentioned` | X | 맥락상 **언급된** 종목 (고객사·경쟁사 등). 종목 노트를 요구하지 않음 |
| `topics` | X | 주제 태그 |

### 파일명 규칙

- 공개일을 **알면** `YYYY-MM-DD-<slug>.md` — 날짜가 `published`와 일치해야 함
- 공개일을 **모르면** 자유 슬러그 (예: `membership-01-starbucks.md`)
  — 날짜 접두사를 붙이면 오류가 난다. **모르는 날짜를 지어내지 않게** 하려는 규칙이다

공개일이 없으면 검증에서 경고가 남습니다. 나중에 확인되면 채우고 파일명을 바꾸세요.

### `tickers` vs `mentioned`

같은 티커를 양쪽에 넣으면 오류입니다. 기준은 **그 종목이 분석 대상이었는가**입니다.

- `tickers` — 강의가 그 종목을 다뤘다. 종목 노트를 만들어야 한다
- `mentioned` — 다른 종목을 설명하다 이름이 나왔다 (8화의 고객사 BRK.B·GOOGL·META·BLK 등).
  종목 노트가 없어도 되지만, **2개 이상의 노트에서 반복 언급되면** 검증기가
  "정리할 때가 됐는지" 알려줍니다

`confidence`는 **나중에 이 기록을 얼마나 믿을지**를 결정하는 필드입니다. 낮은 값을 부끄러워하지
말고 정직하게 쓰는 편이 훨씬 쓸모 있습니다.

---

## 2. 종목 분석 (`stocks/`)

한 종목당 한 파일. 의견이 바뀌면 파일을 덮어쓰지 말고 `views`에 **항목을 추가**합니다.
그래야 "언제 무슨 말을 했고, 그게 맞았는가"를 나중에 되짚을 수 있습니다.

```yaml
---
type: stock
ticker: "005930"             # 파일명(005930.md)과 일치해야 함
name: 삼성전자
market: KOSPI                # KOSPI | KOSDAQ | NASDAQ | NYSE | AMEX | TSE | HKEX | ETC
sector: 반도체                # 선택
currency: KRW                # 선택
class: 아파트                 # 선택. 아파트 | 빌라 | 재개발 (9화 기준)
views:
  - date: 2026-08-20         # 선택. 비우면 출처 노트의 날짜로 대체됨
    stance: 관심              # 매수 | 비중확대 | 관심 | 중립 | 비중축소 | 매도 | 보유 | 사례
    source: videos/2026-08-20-slug.md   # 반드시 존재하는 영상 노트
    price: 78000             # 선택. 발언 시점 주가
    target_price: 95000      # 선택
    horizon: 장기             # 선택
    summary: 한 줄 요약        # 선택
---
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `ticker` | O | 파일명 stem과 일치. 한국 종목은 `"005930"`처럼 따옴표로 감싸 문자열 유지 |
| `name` | O | 종목명 |
| `market` | O | 상장 시장 |
| `views` | O | 최소 1개. 각 항목은 `stance` / `source` 필수, `date`는 선택 |
| `sector`, `currency` | X | 선택 |
| `class` | X | 9화 기준 분류. `아파트`(회수율 O + 두 자릿수 성장) / `빌라`(고회수율 + 저성장) / `재개발`(회수율 X + 고성장) |

**`class`는 강의가 직접 분류한 경우가 아니면 내가 적용한 것**입니다. 그럴 때는 노트 본문에
"9화 기준을 내가 적용했다"고 반드시 적으세요. 그의 분류와 내 분류가 섞이면 기록의 의미가 없어집니다.
회수율과 성장률 중 하나라도 숫자가 없으면 비워 둡니다.

`views[].source`가 가리키는 파일이 없으면 검증 실패합니다. 이 규칙이 **출처 없는 기록이 쌓이는 것**을
구조적으로 막아 줍니다.

**`사례` 스탠스**는 매매의견이 아니라 강의·설명의 예시로 등장했다는 뜻입니다. 개념을 설명하려고
든 종목에 `관심`이나 `매수`를 붙이면 하지도 않은 추천을 기록하는 셈이 되므로, 그럴 때 `사례`를 씁니다.

**`date`를 비우면** 색인이 출처 노트의 날짜(`published`, 없으면 `captured`)로 대체하고 `~`를 붙여
표시합니다. 강의 공개일을 모를 때 날짜를 지어내지 않기 위한 장치이며, 검증에서 경고가 남습니다.

---

## 3. 투자 원칙 (`philosophy/`)

여러 영상에서 반복되는 사고방식을 하나로 묶은 문서입니다. 한 번 언급된 말은 원칙이 아니라
영상 노트에 남겨 두고, **반복 확인된 뒤에** 여기로 승격시키세요.

```yaml
---
type: principle
id: margin-of-safety         # 파일명(margin-of-safety.md)과 일치. 영소문자·숫자·하이픈
title: 안전마진 확보
category: 매수원칙            # 매수원칙 | 매도원칙 | 종목선정 | 재무제표 | 리스크관리 | 포트폴리오 | 심리 | 시장관
status: confirmed            # confirmed | tentative
sources:
  - videos/2026-08-20-slug.md
  - videos/2026-05-02-slug.md
---
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `id` | O | 파일명 stem과 일치하는 kebab-case 식별자 |
| `title` | O | 원칙 이름 |
| `category` | O | 분류 |
| `status` | O | `confirmed`(2개 이상 영상에서 확인) / `tentative`(1개, 추정) |
| `sources` | O | 최소 1개의 영상 노트 경로 |

`status: confirmed`인데 `sources`가 1개면 검증에서 경고합니다.
