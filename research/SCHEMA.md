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

---

## 1. 영상 노트 (`videos/`)

**이 저장소의 사실 근거(source of truth)입니다.** 종목 분석과 투자 원칙은 반드시 영상 노트를
`source`로 참조해야 하며, 참조 없는 주장은 검증에서 걸러집니다.

```yaml
---
type: video
title: "영상 제목 그대로"
url: https://www.youtube.com/watch?v=XXXXXXXXXXX
video_id: XXXXXXXXXXX        # 선택
channel: 성환김
published: 2026-08-20        # 영상 공개일
captured: 2026-08-31         # 내가 정리한 날짜
source: transcript           # transcript | summary | manual
confidence: high             # high | medium | low
tickers: ["005930", AAPL]    # 선택. 영상에서 다룬 종목
topics: [밸류에이션, 반도체]   # 선택
---
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `type` | O | `video` 고정 |
| `title` | O | 영상 제목. 임의로 바꾸지 말 것 |
| `url` | O | `http`로 시작하는 원본 링크 |
| `published` | O | 영상 공개일 (`YYYY-MM-DD`). 파일명 날짜 접두사와 일치해야 함 |
| `captured` | O | 정리한 날짜. `published`보다 빠를 수 없음 |
| `source` | O | `transcript`(자막 원문) / `summary`(요약본) / `manual`(직접 시청 메모) |
| `confidence` | O | 원문 확보 정확도. 자막 원문이면 `high`, 기억에 의존하면 `low` |
| `video_id` | X | 유튜브 영상 ID |
| `channel` | X | 채널명 |
| `tickers` | X | 다룬 종목 티커 목록 |
| `topics` | X | 주제 태그 |

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
views:
  - date: 2026-08-20
    stance: 관심              # 매수 | 비중확대 | 관심 | 중립 | 비중축소 | 매도 | 보유
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
| `views` | O | 최소 1개. 각 항목은 `date` / `stance` / `source` 필수 |
| `sector`, `currency` | X | 선택 |

`views[].source`가 가리키는 파일이 없으면 검증 실패합니다. 이 규칙이 **출처 없는 기록이 쌓이는 것**을
구조적으로 막아 줍니다.

---

## 3. 투자 원칙 (`philosophy/`)

여러 영상에서 반복되는 사고방식을 하나로 묶은 문서입니다. 한 번 언급된 말은 원칙이 아니라
영상 노트에 남겨 두고, **반복 확인된 뒤에** 여기로 승격시키세요.

```yaml
---
type: principle
id: margin-of-safety         # 파일명(margin-of-safety.md)과 일치. 영소문자·숫자·하이픈
title: 안전마진 확보
category: 매수원칙            # 매수원칙 | 매도원칙 | 종목선정 | 리스크관리 | 포트폴리오 | 심리 | 시장관
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
