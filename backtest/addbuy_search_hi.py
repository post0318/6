"""후보 H/I 기준 추가매수(주기·비중)만 변수로 탐색.

상수:  초기편입 40% / 10일 분할 / 재진입·매도 79 / 급락 31 / 급락매수 100%
       H: 매도 100%,  I: 매도 50% (국면당 1회)
변수:  buy_interval_days, buy_step

목표 3가지:
  수익률   = 총수익률 최대
  위험관리 = 롤링 1년 최악 수익률 최대(MDD는 전 조합 -36.4%로 동일해 변별력이 없음)
  밸런스   = Sharpe-like 최대
표본 두 가지로 교차검증: 최근 5년 / 2011~2026 전체.
결과: backtest/addbuy_search_hi.csv
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from optimize_v2 import perf_from_equity, simulate  # noqa: E402
from half_trade_rolling import rolling  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

BASE = dict(initial_allocation=0.40, ramp_days=10, resell_level=79, crash_level=31, crash_buy_fraction=1.0)
CANDIDATES = {"H": 1.0, "I": 0.5}
INTERVALS = [1, 2, 3, 5, 7, 10, 14, 21, 28, 42, 63, 84, 126]
STEPS = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.00]


def run(df: pd.DataFrame, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()  # 1일 체결지연 (session 14)
    price, dates = df["close"].to_numpy(), df["date"]
    bench_eq = 100.0 * (price / price[0])
    bench = perf_from_equity(bench_eq, dates)
    rows = []
    for (cand, sell), interval, step in product(CANDIDATES.items(), INTERVALS, STEPS):
        eq = simulate(fg, price, buy_interval_days=interval, buy_step=step, sell_fraction=sell, **BASE)
        r1, r2 = rolling(eq, bench_eq, 252), rolling(eq, bench_eq, 504)
        rows.append({
            "sample": sample, "candidate": cand, "interval": interval, "step": step,
            **perf_from_equity(eq, dates),
            "roll1y_worst": r1["worst"], "roll1y_neg": r1["neg"], "roll1y_win": r1["win"],
            "roll2y_worst": r2["worst"], "roll2y_neg": r2["neg"], "roll2y_win": r2["win"],
            "bench_return": bench["total_return"], "bench_sharpe": bench["sharpe_like"],
            "bench_mdd": bench["max_drawdown"],
        })
    return rows


def main() -> None:
    full = load_full()
    five = full[full["date"] >= full["date"].max() - pd.DateOffset(years=5)].reset_index(drop=True)
    out = pd.DataFrame(run(five, "5y") + run(full, "2011"))
    out.to_csv(ROOT / "backtest" / "addbuy_search_hi.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
