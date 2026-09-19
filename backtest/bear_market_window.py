"""전체기간 집계 지표는 상승장 편향 때문에 변별력이 약하다는 지적에 대한 응답.

실제 약세장 구간(나스닥 고점 2021-11-19 -> 저점 2022-12-28, -36.4%)에서 각 전략이
얼마나 버텼는지, 그리고 Buy&Hold가 고점을 회복한 날(2024-02-29)까지 각 전략이 얼마나
회복했는지를 비교한다. 전체기간 총수익률만으로는 안 보이는 차이를 드러내기 위함.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from optimize_v2 import load_arrays, simulate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

PEAK_DATE = pd.Timestamp("2021-11-19")
TROUGH_DATE = pd.Timestamp("2022-12-28")
RECOVERY_DATE = pd.Timestamp("2024-02-29")  # Buy&Hold가 고점을 재돌파한 날


def main() -> None:
    fg, price, dates = load_arrays()
    peak_idx = dates[dates == PEAK_DATE].index[0]
    trough_idx = dates[dates == TROUGH_DATE].index[0]
    recovery_idx = dates[dates == RECOVERY_DATE].index[0]
    end_idx = len(fg) - 1

    def summarize(name: str, equity) -> None:
        peak_v, trough_v, recov_v, end_v = equity[peak_idx], equity[trough_idx], equity[recovery_idx], equity[end_idx]
        print(
            f"{name:38s} 고점→저점: {trough_v/peak_v-1:+7.1%}   "
            f"고점→BnH회복일: {recov_v/peak_v-1:+7.1%}   전체기간: {end_v/equity[0]-1:+7.1%}"
        )

    bench = 100.0 * (price / price[0])
    summarize("Buy & Hold", bench)

    v1_df = pd.read_csv(ROOT / "backtest" / "equity_curve.csv")
    summarize("v1 (20/70 전량매매)", v1_df["strategy_equity"].to_numpy())

    v2default_df = pd.read_csv(ROOT / "backtest" / "equity_curve_gradual.csv")
    summarize("v2-default (70/20, 5일램프, 주5%)", v2default_df["strategy_equity"].to_numpy())

    eq_opt = simulate(
        fg, price, initial_allocation=0.50, ramp_days=1, buy_interval_days=21,
        buy_step=0.20, resell_level=65, crash_level=30,
    )
    summarize("v2-optimal (50%/1일/21일/20%/65/30)", eq_opt)


if __name__ == "__main__":
    main()
