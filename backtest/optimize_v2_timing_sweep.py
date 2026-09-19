"""추가매수 비중을 10%/20%로 고정하고, 초기편입 시기(ramp_days)와 추가매수 시기
(buy_interval_days)만 비교하는 정밀 탐색.

고정: initial_allocation=40%, resell_level=65, crash_level=30
변수: ramp_days in [1,2,3,5,7,10,14,21], buy_interval_days in [5,7,10,14,21,30,45,63]
      buy_step in [0.10, 0.20]
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from optimize_v2 import load_arrays, perf_from_equity, simulate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

INITIAL_ALLOCATION = 0.40
RESELL_LEVEL = 65
CRASH_LEVEL = 30

RAMP_DAYS_OPTS = [1, 2, 3, 5, 7, 10, 14, 21]
INTERVAL_DAYS_OPTS = [5, 7, 10, 14, 21, 30, 45, 63]
BUY_STEPS = [0.10, 0.20]


def main() -> None:
    fg, price, dates = load_arrays()

    rows = []
    for buy_step in BUY_STEPS:
        for ramp_days, interval_days in product(RAMP_DAYS_OPTS, INTERVAL_DAYS_OPTS):
            equity = simulate(
                fg, price, INITIAL_ALLOCATION, ramp_days, interval_days, buy_step, RESELL_LEVEL, CRASH_LEVEL
            )
            stats = perf_from_equity(equity, dates)
            rows.append({"buy_step": buy_step, "ramp_days": ramp_days, "interval_days": interval_days, **stats})

    df = pd.DataFrame(rows)
    out_path = ROOT / "backtest" / "optimize_v2_timing_sweep.csv"
    df.to_csv(out_path, index=False)
    print(f"저장: {out_path} ({len(df)} rows)")

    for bs in BUY_STEPS:
        sub = df[df["buy_step"] == bs].sort_values("total_return", ascending=False)
        print(f"\n=== buy_step={bs} 총수익률 상위 8 ===")
        print(sub.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
