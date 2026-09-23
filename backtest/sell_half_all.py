"""후보 A~I 전부 매도비율 100% → 50%(국면당 1회) 비교.

A~G(65/30), H(79/31)은 원래 기준과 77 두 가지로. I는 H + 매도50%라 H의 50% 행이 곧 I.
표본: 최근 5년 / 2011~2026. 결과: backtest/sell_half_all.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "backtest"))
from export_dashboard_json import SIGNAL_CANDIDATES  # noqa: E402
from half_trade_rolling import rolling  # noqa: E402
from optimize_v2 import perf_from_equity, simulate  # noqa: E402
from scenario_2022 import PEAK, TROUGH  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

H_PARAMS = dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=79, crash_level=31)


def run(df: pd.DataFrame, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
    bench = 100.0 * price / price[0]
    cands = {c["id"]: c["params"] for c in SIGNAL_CANDIDATES if c["id"] in "ABCDEFG"} | {"H": H_PARAMS}
    rows = []
    for cid, params in cands.items():
        for level in dict.fromkeys((params["resell_level"], 77)):
            for sf in (1.0, 0.5):
                eq = simulate(fg, price, sell_fraction=sf, **(params | dict(resell_level=level)))
                s, r2 = perf_from_equity(eq, dates), rolling(eq, bench, 504)
                rows.append({"sample": sample, "candidate": cid, "resell": level, "sell_fraction": sf, **s,
                             "dd_2022": eq[it] / eq[ip] - 1, "r2_worst": r2["worst"], "r2_neg": r2["neg"],
                             "r2_win": r2["win"]})
    return rows


def main() -> None:
    full = load_full()
    five = full[full["date"] >= full["date"].max() - pd.DateOffset(years=5)].reset_index(drop=True)
    out = pd.DataFrame(run(five, "5y") + run(full, "2011"))
    out.to_csv(ROOT / "backtest" / "sell_half_all.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
