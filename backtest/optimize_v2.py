"""v2 로직의 최적 기준점(초기편입 비중/속도, 추가매수 주기/비중, 매수·매도 트리거 지수)을
찾기 위한 전면 그리드 서치.

v2의 메커니즘(램프업 -> 단일 재진입/매도 임계값 -> 계단식 추가매수 -> 급락 전량매수)은
그대로 두고 아래 6개 파라미터를 모두 스캔한다:

1. initial_allocation : 초기 편입 목표 비중
2. ramp_days           : 그 비중까지 매일 균등 분할해서 채우는 데 걸리는 거래일 수
3. buy_interval_days   : 초기 편입 이후 추가 매수 주기(거래일 단위, 5≈1주)
4. buy_step            : 추가 매수 1회당 편입 비중
5. resell_level        : 이 이상이면 전량매도 / 이 밑이면 매수 진행(재진입) 트리거
6. crash_level         : 매수 진행 중 이 밑이면 즉시 전량매수

주의: 스캔 속도를 위해 요일(수요일) 앵커 대신 "거래일 카운트" 기반 주기를 쓴다 — 결과가
strategy_fg_gradual.py(요일 앵커 버전)와 완전히 같은 숫자는 아니고 근사치다. 최적 후보를
찾은 뒤에는 정밀 버전(strategy_fg_gradual.py)으로 재검증해서 최종 수치를 확정한다.

Session 14: load_arrays()가 반환하는 fg는 하루 지연(shift)된 값이다 — FG(D)는 D일 당일
종가와 강하게 연동됨이 확인되어(상관계수 0.56), "FG(D)로 판단, D일 종가 체결"은 동시성을
가정하는 셈이라 더 보수적으로 "FG(D-1)로 판단, D일 종가 체결"로 바꿨다.
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
MERGED_PATH = ROOT / "data" / "merged.csv"
INITIAL_CAPITAL = 100.0

V1_TOTAL_RETURN = 1.0456
V1_VOL = 0.1513
BENCH_TOTAL_RETURN = 1.3792
BENCH_VOL = 0.1657

INITIAL_ALLOCATIONS = [0.1, 0.2, 0.3, 0.4, 0.5]
RAMP_DAYS_OPTS = [1, 2, 5, 10]
BUY_INTERVAL_OPTS = [3, 5, 10, 15, 21]
BUY_STEP_OPTS = [0.05, 0.10, 0.15, 0.20, 0.25]
RESELL_LEVELS = [60, 65, 70, 75, 80, 85, 90]
CRASH_LEVELS = [10, 15, 20, 25, 30]


def load_arrays() -> tuple[np.ndarray, np.ndarray, pd.Series]:
    df = pd.read_csv(MERGED_PATH, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    # 신호-체결 1일 지연 (session 14): 전날까지 알려진 FG로 오늘 종가에 체결
    fg_lagged = df["fg"].shift(1).bfill()
    return fg_lagged.to_numpy(), df["close"].to_numpy(), df["date"]


def simulate(
    fg: np.ndarray,
    price: np.ndarray,
    initial_allocation: float,
    ramp_days: int,
    buy_interval_days: int,
    buy_step: float,
    resell_level: float,
    crash_level: float,
    crash_buy_fraction: float = 1.0,
    sell_fraction: float = 1.0,
) -> np.ndarray:
    """sell_fraction<1이면 FG>=resell 국면(에피소드)당 1회만 그 비율만큼 매도하고 나머지는
    FG<resell로 내려와 매수가 재개될 때까지 보유한다(매일 반씩 팔려 결국 전량 매도가
    되는 것을 막기 위함). 1.0이면 기존 전량매도와 동일."""
    n = len(fg)
    cash = INITIAL_CAPITAL
    shares = 0.0
    buying_active = False
    sold_flag = False
    days_since = 0
    ramp_daily = initial_allocation / ramp_days
    equity = np.empty(n)

    for i in range(n):
        f = fg[i]
        p = price[i]
        total = cash + shares * p

        if i < ramp_days:
            bv = min(cash, ramp_daily * total)
            if bv > 0:
                shares += bv / p
                cash -= bv
        else:
            cw = (shares * p) / total if total > 0 else 0.0
            if cw > 1e-9 and f >= resell_level and not (sell_fraction < 1.0 and sold_flag):
                sold_sh = shares * sell_fraction
                cash += sold_sh * p
                shares -= sold_sh
                buying_active = False
                sold_flag = True
                days_since = 0
            else:
                was_active = buying_active
                if f < resell_level:
                    buying_active = True
                    sold_flag = False
                if buying_active and not was_active:
                    days_since = 0

                total = cash + shares * p
                cw = (shares * p) / total if total > 0 else 0.0

                if buying_active and crash_buy_fraction > 0 and f < crash_level and cw < 1.0 - 1e-9:
                    bv = crash_buy_fraction * cash
                    shares += bv / p
                    cash -= bv
                    days_since = 0
                else:
                    days_since += 1
                    if buying_active and days_since >= buy_interval_days and cw < 1.0 - 1e-9:
                        total = cash + shares * p
                        bv = min(cash, buy_step * total)
                        if bv > 0:
                            shares += bv / p
                            cash -= bv
                        days_since = 0

        equity[i] = cash + shares * p

    return equity


def simulate_with_trades(
    fg: np.ndarray,
    price: np.ndarray,
    dates: pd.Series,
    initial_allocation: float,
    ramp_days: int,
    buy_interval_days: int,
    buy_step: float,
    resell_level: float,
    crash_level: float,
    crash_buy_fraction: float = 1.0,
    sell_fraction: float = 1.0,
):
    """simulate()와 완전히 동일한 로직이지만, 매매 신호(trades)와 비중/매수모드 배열도
    함께 기록한다 — 대시보드의 "실전 매매 시그널" 표시용."""
    n = len(fg)
    cash = INITIAL_CAPITAL
    shares = 0.0
    buying_active = False
    sold_flag = False
    days_since = 0
    ramp_daily = initial_allocation / ramp_days
    equity = np.empty(n)
    weight = np.empty(n)
    buying_active_arr = np.empty(n, dtype=bool)
    trades: list[dict] = []

    def record(i: int, action: str, pct: float | None = None) -> None:
        total_now = cash + shares * price[i]
        resulting_weight = (shares * price[i]) / total_now if total_now > 0 else 0.0
        trades.append({
            "date": str(dates.iloc[i].date()),
            "action": action,
            "fg": round(float(fg[i]), 2),
            "price": round(float(price[i]), 2),
            "pctOfPortfolio": round(float(pct), 4) if pct is not None else None,
            "resultingWeight": round(float(resulting_weight), 4),
        })

    for i in range(n):
        f = fg[i]
        p = price[i]
        total = cash + shares * p

        if i < ramp_days:
            bv = min(cash, ramp_daily * total)
            if bv > 0:
                shares += bv / p
                cash -= bv
                record(i, "RAMP_BUY", bv / total if total > 0 else None)
        else:
            cw = (shares * p) / total if total > 0 else 0.0
            if cw > 1e-9 and f >= resell_level and not (sell_fraction < 1.0 and sold_flag):
                sold_sh = shares * sell_fraction
                cash += sold_sh * p
                shares -= sold_sh
                buying_active = False
                sold_flag = True
                days_since = 0
                if sell_fraction >= 1.0:
                    record(i, "SELL_ALL")
                else:
                    record(i, "SELL_HALF", cw * sell_fraction)
            else:
                was_active = buying_active
                if f < resell_level:
                    buying_active = True
                    sold_flag = False
                if buying_active and not was_active:
                    days_since = 0

                total = cash + shares * p
                cw = (shares * p) / total if total > 0 else 0.0

                if buying_active and crash_buy_fraction > 0 and f < crash_level and cw < 1.0 - 1e-9:
                    bv = crash_buy_fraction * cash
                    shares += bv / p
                    cash -= bv
                    days_since = 0
                    if crash_buy_fraction >= 1.0:
                        record(i, "CRASH_FULL_BUY", 1.0 - cw)
                    else:
                        record(i, "CRASH_HALF_BUY", bv / total if total > 0 else None)
                else:
                    days_since += 1
                    if buying_active and days_since >= buy_interval_days and cw < 1.0 - 1e-9:
                        total = cash + shares * p
                        bv = min(cash, buy_step * total)
                        if bv > 0:
                            shares += bv / p
                            cash -= bv
                            record(i, "WEEKLY_BUY", bv / total)
                        days_since = 0

        total = cash + shares * p
        equity[i] = total
        weight[i] = (shares * p) / total if total > 0 else 0.0
        buying_active_arr[i] = buying_active

    return equity, weight, buying_active_arr, trades


def perf_from_equity(equity: np.ndarray, dates: pd.Series) -> dict:
    total_return = equity[-1] / equity[0] - 1
    years = (dates.iloc[-1] - dates.iloc[0]).days / 365.25
    cagr = (equity[-1] / equity[0]) ** (1 / years) - 1 if years > 0 else float("nan")
    eq = pd.Series(equity)
    running_max = eq.cummax()
    drawdown = eq / running_max - 1
    max_dd = drawdown.min()
    daily_ret = eq.pct_change().dropna()
    ann_vol = daily_ret.std() * (252 ** 0.5)
    sharpe = (daily_ret.mean() * 252) / ann_vol if ann_vol > 0 else float("nan")
    return {
        "total_return": round(float(total_return), 4),
        "cagr": round(float(cagr), 4),
        "max_drawdown": round(float(max_dd), 4),
        "annualized_vol": round(float(ann_vol), 4),
        "sharpe_like": round(float(sharpe), 3),
    }


def main() -> None:
    fg, price, dates = load_arrays()

    combos = [
        (ia, rd, bi, bs, rl, cl)
        for ia, rd, bi, bs, rl, cl in product(
            INITIAL_ALLOCATIONS, RAMP_DAYS_OPTS, BUY_INTERVAL_OPTS, BUY_STEP_OPTS, RESELL_LEVELS, CRASH_LEVELS
        )
        if cl < rl
    ]
    print(f"총 {len(combos)}개 조합")

    rows = []
    for ia, rd, bi, bs, rl, cl in combos:
        equity = simulate(fg, price, ia, rd, bi, bs, rl, cl)
        stats = perf_from_equity(equity, dates)
        rows.append({
            "initial_allocation": ia, "ramp_days": rd, "buy_interval_days": bi,
            "buy_step": bs, "resell_level": rl, "crash_level": cl, **stats,
        })

    results = pd.DataFrame(rows)
    out_path = ROOT / "backtest" / "optimize_v2_results.csv"
    results.to_csv(out_path, index=False)
    print(f"결과 저장: {out_path} ({len(results)} rows)")

    results_sorted = results.sort_values("total_return", ascending=False)

    beats_both = results_sorted[
        (results_sorted["total_return"] > BENCH_TOTAL_RETURN) & (results_sorted["annualized_vol"] < V1_VOL)
    ]
    beats_return_only = results_sorted[results_sorted["total_return"] > BENCH_TOTAL_RETURN]

    print(f"\n베스트(수익률>BnH {BENCH_TOTAL_RETURN} AND 변동성<v1 {V1_VOL}): {len(beats_both)}개")
    if not beats_both.empty:
        print(beats_both.head(15).to_string(index=False))

    print(f"\n차선(수익률>BnH만): {len(beats_return_only)}개")
    if not beats_return_only.empty:
        print(beats_return_only.head(15).to_string(index=False))

    # Sharpe-like 기준 상위 (위험조정 최적)
    print("\nSharpe-like 상위 15개:")
    print(results.sort_values("sharpe_like", ascending=False).head(15).to_string(index=False))

    print("\n총수익률 상위 15개:")
    print(results_sorted.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
