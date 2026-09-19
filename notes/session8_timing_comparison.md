# Session 8 — 추가매수 비중 10% vs 20%, 초기/추가매수 시기 비교

## 요청

추가매수 비중은 최대 20%가 적정해 보인다는 판단 하에, 초기편입 시기(ramp_days)와
추가매수 시기(buy_interval_days)를 비교하되 추가매수 비중은 10%와 20% 두 가지로
고정해서 비교. (`backtest/optimize_v2_timing_sweep.py`)

고정: initial_allocation=40%, resell_level=65, crash_level=30
변수: ramp_days ∈ {1,2,3,5,7,10,14,21}, buy_interval_days ∈ {5,7,10,14,21,30,45,63},
buy_step ∈ {10%, 20%} — 총 128개 조합

## 결과

두 buy_step 모두에서 **ramp_days=1(초기편입은 즉시가 최선), interval_days=21거래일
(~1개월 주기가 최선)** 로 동일하게 수렴했다:

| buy_step | ramp_days | interval | 총수익률 | MDD | 변동성 | Sharpe-like |
|---|---|---|---|---|---|---|
| **20%** | 1 | 21 | **130.9%** | -20.8% | 13.94% | **1.046** |
| 10% | 1 | 21 | 127.9% | -20.8% | 13.90% | 1.033 |

**20%가 10%보다 수익률·Sharpe 모두 더 낫다** (변동성은 거의 동일: 13.94% vs 13.90%).
"더 뜸하게(21거래일=한 달에 한 번), 더 크게(20%)" 사는 쪽이 "더 자주, 더 작게" 사는
쪽보다 이 표본에서는 우월했다.

추가로 확인된 패턴: interval_days=21이 5·7·10·14·30·45·63보다 일관되게 낫고,
ramp_days는 1이 항상 최선(초기편입을 늦출 이유가 없음) — 두 buy_step 모두에서 동일한
형태의 순위가 나와 이 결론이 buy_step 선택에 좌우되지 않는, 비교적 안정적인 패턴으로
보인다.

## 결론

**최종 후보: initial_allocation=40%, ramp_days=1, buy_interval_days=21, buy_step=20%,
resell_level=65, crash_level=30** → 총수익률 130.9% / MDD -20.8% / 변동성 13.9% /
Sharpe-like 1.046. (v1 대비 전부 우위, Buy&Hold 대비 수익률만 7%p 낮고 MDD·변동성·
Sharpe는 모두 우위 — session 7 노트의 결론이 그대로 유지되며 이번엔 정교화됨.)

## 산출물

`backtest/optimize_v2_timing_sweep.py`, `backtest/optimize_v2_timing_sweep.csv` (128행)
