"""사용자 지정 범위로 좁힌 정밀 탐색.

고정: ramp_days=1, buy_interval_days=14, resell_level=65, crash_level=30
변수: initial_allocation in [0.30, 0.40], buy_step in [0.00, 0.10] (0.25%p 간격)

목표: v1(총수익률 104.6%, 변동성 15.13%, MDD -25.43%, Sharpe-like 0.845)을
총수익률과 변동성 둘 다에서 이기는(dominate) initial_allocation/buy_step 조합을 찾는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from optimize_v2 import load_arrays, perf_from_equity, simulate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

V1 = {"total_return": 1.0456, "cagr": 0.1229, "max_drawdown": -0.2543, "annualized_vol": 0.1513, "sharpe_like": 0.845}

RAMP_DAYS = 1
BUY_INTERVAL_DAYS = 14
RESELL_LEVEL = 65
CRASH_LEVEL = 30

INITIAL_ALLOC_GRID = np.arange(0.30, 0.40 + 1e-9, 0.0025)
BUY_STEP_GRID = np.arange(0.00, 0.10 + 1e-9, 0.0025)


def main() -> None:
    fg, price, dates = load_arrays()

    rows = []
    for ia in INITIAL_ALLOC_GRID:
        for bs in BUY_STEP_GRID:
            equity = simulate(fg, price, ia, RAMP_DAYS, BUY_INTERVAL_DAYS, bs, RESELL_LEVEL, CRASH_LEVEL)
            stats = perf_from_equity(equity, dates)
            rows.append({"initial_allocation": round(float(ia), 4), "buy_step": round(float(bs), 4), **stats})

    results = pd.DataFrame(rows)
    out_path = ROOT / "backtest" / "optimize_v2_focused_results.csv"
    results.to_csv(out_path, index=False)
    print(f"총 {len(results)}개 조합, 저장: {out_path}")

    dominates_v1 = results[
        (results["total_return"] > V1["total_return"]) & (results["annualized_vol"] < V1["annualized_vol"])
    ].sort_values("sharpe_like", ascending=False)

    print(f"\nv1을 총수익률·변동성 둘 다에서 이기는 조합: {len(dominates_v1)}개")
    if not dominates_v1.empty:
        print(dominates_v1.head(20).to_string(index=False))
        best = dominates_v1.iloc[0]
        print("\n=== Sharpe-like 기준 최상위 1개 ===")
        print(best.to_string())
    else:
        print("  -> 이 범위 안에서는 v1을 완전히 dominate하는 조합이 없습니다.")
        print("\n총수익률 상위 10개 (참고):")
        print(results.sort_values("total_return", ascending=False).head(10).to_string(index=False))
        print("\nSharpe-like 상위 10개 (참고):")
        print(results.sort_values("sharpe_like", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
