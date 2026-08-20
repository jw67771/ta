# 무한매수법 V4.0 중계기

라오어 무한매수법 V4.0 의 매일 매수/매도 지점을 계산한다.
규칙은 공개 중계표에서 역산했고, `tests/test_strategy.py` 가 8/18·8/19·8/20 세 회차의
공개 표를 그대로 재현하는지, 그리고 하루 매수 후 회차·잔금·평단·1회매수금액이
다음날 표와 맞는지 검증한다 (전이 6건 전부 일치).

## 계산 규칙

| 항목 | 식 |
|---|---|
| 별% | `지정가매도율 x (1 - T / (분할수/2))` — TQQQ 15%, SOXL 20% |
| 1회 매수금액 `u` | `잔금 / (분할수 - T)` |
| 별지점 | `매수평단 x (1 + 별%)` |
| 지정가 매도 | `매수평단 x (1 + 지정가매도율)` |
| 큰수 | `직전종가 x 1.12` |
| 상단 줄 가격 | `min(별지점 - 0.01, 큰수)` |

매수 (전부 LOC)

- 평단이 상단 줄보다 **쌀 때** — 예산을 절반씩 나눠 두 줄:
  상단 줄 `floor((u/2) / 상단가격)` 주, 평단 줄 `floor(u / 직전종가) - 상단 줄 수량` 주
- 평단이 상단 줄보다 **비쌀 때** (후반전이거나 급락 직후) — 평단 줄이 사라지고
  예산 전부가 상단 줄로: `floor(u / 상단가격)` 주
- 그 아래로 `u / k` (k = 총수량+1, +2, ...) 가격에 1주씩 사다리.
  종가가 그만큼 빠지면 더 많은 수량을 사서 그날 집행액이 `u` 로 유지된다.
  직전종가 -20% 지점까지만 걸면 충분하다.

매도 (전·후반 공통)

- 보유수량의 `1/4` (내림) → 별지점에 LOC 매도
- 나머지 전량 → 지정가 매도

별지점이 매수/매도를 가른다. 종가가 별지점 이상이면 매도가, 미만이면 매수가
체결되도록 매수는 별지점보다 1센트 아래에 건다.

`T` 는 진행 회차. **체결 금액이 아니라 체결된 '줄' 로 센다** — 두 줄인 날은
한 줄당 0.5, 상단 줄 하나뿐인 날은 1.0. 사다리 체결은 회차를 올리지 않는다
(같은 예산으로 더 많은 수량을 사는 것이므로). 매도하면
`매도수량 x 매수평단 / u` 만큼 되감긴다. 익절이 나면 잔금이 늘어 `u` 가 커진다.
`T = 분할수/2` 에서 별% 가 0 이 되고(별지점 = 평단) 후반전으로 넘어간다.

## 사용법

두 종목을 동시에 굴린다. 상태 파일이 다르므로 `--state` 로 구분한다.

| 계좌 | 상태 파일 | 원금 | 분할 | 지정가율 |
|---|---|---|---|---|
| TQQQ | `state/tqqq_40.json` (기본값) | $10,000 | 40 | 15% |
| SOXL | `state/soxl_20.json` | $10,000 | 20 | 20% |

```sh
# 시즌 시작 (원금 1만달러, 40분할, TQQQ, 기존 보유 2주 @ 77.91 편입)
python3 -m infinite_buying.cli init --cash 10000 --splits 40 --ticker TQQQ \
    --shares 2 --avg-price 77.91

# SOXL 은 지정가율이 20% 다
python3 -m infinite_buying.cli --state infinite_buying/state/soxl_20.json \
    init --cash 10000 --splits 20 --ticker SOXL --limit-pct 0.20 \
    --shares 3 --avg-price 147.79

# 오늘 걸 주문표 (직전 종가를 넣는다)
python3 -m infinite_buying.cli plan --close 76.40 --date 8/17

# 장 마감 후 체결 반영
python3 -m infinite_buying.cli fill --close 75.10 --bought 3 --date 8/18
python3 -m infinite_buying.cli fill --close 88.20 --sold-loc 5 --sold-limit 10 --limit-price 86.10

python3 -m infinite_buying.cli status
python3 -m infinite_buying.cli new-cycle   # 보유 0 이 되면 잔금 전액으로 다음 사이클
```

SOXL 쪽 명령에는 모두 `--state infinite_buying/state/soxl_20.json` 을 붙인다.
상태는 `infinite_buying/state/` 아래에 저장된다. 컨테이너는 매번
새로 만들어지므로 체결을 반영할 때마다 커밋해야 이어진다.

## 주의

- 매도쪽 회차 되감기는 공개 표에 매도가 찍힌 날이 아직 없어 미검증이다.
  실제 매도가 나오는 날 중계표와 대조해야 한다.
- 원금 소진 후의 리버스 모드는 구현되어 있지 않다.

## SOXL 분할매수 사다리 (`dip_ladder.py`)

무한매수법과 별개 전략. 직전 매수가 대비 15% 씩 빠질 때마다 정해진 금액을
넣어 평단을 낮춘다. 매도 규칙은 없다.

    다음 매수가 = 마지막 매수가 x 0.85
    회당 금액   = $500 + $100 x (채운 단계수)

체결가가 계획가보다 낮게 잡히면 (갭하락) 다음 단계는 계획가가 아니라
**실제 체결가** 기준으로 다시 잡는다. 그래서 체결될 때마다 상태를 갱신해야 한다.

```sh
python3 -c "
import json
from infinite_buying.dip_ladder import DipLadder
l = DipLadder(**{k: v for k, v in json.load(open('infinite_buying/state/soxl_dip.json')).items() if k != 'log'})
for r in l.plan(3):
    print(f'{r.step}단계 {r.price:.2f} x {r.qty}주 (\${r.spend:,.0f}) -> 평단 {r.avg_after:.2f}')
"
```

상태는 `state/soxl_dip.json`. 무한매수법 시절 상태(`state/soxl_20.json`)는
재개할 경우를 대비해 그대로 남겨 뒀다.
