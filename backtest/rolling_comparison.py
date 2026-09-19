"""롤링(이동) 윈도우 기준 비교.

peak-to-trough 같은 단일 사건 하나만 보면 우연일 수 있으니, 전체 기간에서 겹치는
윈도우를 다 뽑아(3/6/12/24개월) 각 전략의 수익률 분포와 Buy&Hold 대비 승률을 본다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from optimize_v2 import load_arrays, simulate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HORIZONS = {"3m": 63, "6m": 126, "12m": 252, "24m": 504}

OPT_PARAMS = dict(initial_allocation=0.50, ramp_days=1, buy_interval_days=21, buy_step=0.20, resell_level=65, crash_level=30)


def rolling_returns(eq: np.ndarray, n: int) -> np.ndarray:
    return eq[n:] / eq[:-n] - 1


def main() -> None:
    fg, price, dates = load_arrays()
    bench_eq = 100.0 * (price / price[0])
    v1_eq = pd.read_csv(ROOT / "backtest" / "equity_curve.csv")["strategy_equity"].to_numpy()
    v2d_eq = pd.read_csv(ROOT / "backtest" / "equity_curve_gradual.csv")["strategy_equity"].to_numpy()
    v2o_eq = simulate(fg, price, **OPT_PARAMS)

    curves = {"BuyHold": bench_eq, "v1": v1_eq, "v2Default": v2d_eq, "v2Optimal": v2o_eq}

    rows = []
    for horizon_label, n in HORIZONS.items():
        rr = {name: rolling_returns(eq, n) for name, eq in curves.items()}
        for name, r in rr.items():
            win_vs_bnh = float((r > rr["BuyHold"]).mean()) if name != "BuyHold" else None
            rows.append({
                "horizon": horizon_label,
                "strategy": name,
                "n_windows": len(r),
                "mean": round(float(r.mean()), 4),
                "median": round(float(np.median(r)), 4),
                "worst": round(float(r.min()), 4),
                "best": round(float(r.max()), 4),
                "pct_negative": round(float((r < 0).mean()), 4),
                "win_rate_vs_bnh": round(win_vs_bnh, 4) if win_vs_bnh is not None else None,
            })

    df = pd.DataFrame(rows)
    out_path = ROOT / "backtest" / "rolling_comparison.csv"
    df.to_csv(out_path, index=False)
    print(f"저장: {out_path}")
    for horizon_label in HORIZONS:
        print(f"\n=== {horizon_label} 롤링 ===")
        print(df[df["horizon"] == horizon_label].drop(columns="horizon").to_string(index=False))


if __name__ == "__main__":
    main()
