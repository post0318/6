"""H(F/79/31)에서 [기존 100/100] vs [매도만 50%] vs [급락매수·매도 둘 다 50%]의
롤링 수익률(1/2/3/5년)과 매매 시점 비교. 표본은 최근 5년 / 2011~2026.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from half_trade_search import arrays, samples  # noqa: E402
from optimize_v2 import perf_from_equity, simulate_with_trades  # noqa: E402

BASE = dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=79, crash_level=31)
VARIANTS = {"H 100/100(기존)": (1.0, 1.0), "H 매도만50%": (1.0, 0.5), "H 둘다50%": (0.5, 0.5)}
WINDOWS = {"1y": 252, "2y": 504, "3y": 756, "5y": 1260}


def rolling(eq: np.ndarray, bench: np.ndarray, n: int) -> dict | None:
    if n >= len(eq) - 10:
        return None
    r, rb = eq[n:] / eq[:-n] - 1, bench[n:] / bench[:-n] - 1
    return dict(n=len(r), mean=r.mean(), worst=r.min(), neg=(r < 0).mean(), win=(r > rb).mean(),
                b_mean=rb.mean(), b_worst=rb.min(), b_neg=(rb < 0).mean())


def main() -> None:
    out_rows, all_trades = [], {}
    for sname, df in samples().items():
        fg, price, dates = arrays(df)
        bench = 100.0 * (price / price[0])
        curves = {"Buy&Hold": bench}
        for vname, (cf, sf) in VARIANTS.items():
            eq, w, a, trades = simulate_with_trades(fg, price, dates, crash_buy_fraction=cf, sell_fraction=sf, **BASE)
            curves[vname] = eq
            all_trades[(sname, vname)] = trades
        for cname, eq in curves.items():
            s = perf_from_equity(eq, dates)
            for wname, n in WINDOWS.items():
                r = rolling(eq, bench, n)
                if r:
                    out_rows.append({"sample": sname, "strategy": cname, "window": wname, **r,
                                     "total_return": s["total_return"], "sharpe": s["sharpe_like"], "mdd": s["max_drawdown"]})
    pd.DataFrame(out_rows).to_csv(ROOT / "backtest" / "half_trade_rolling.csv", index=False)
    rows = []
    for (sname, vname), trades in all_trades.items():
        for t in trades:
            rows.append({"sample": sname, "variant": vname, **t})
    pd.DataFrame(rows).to_csv(ROOT / "backtest" / "half_trade_signals.csv", index=False)
    print("saved")


if __name__ == "__main__":
    main()
