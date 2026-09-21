"""후보 A~G의 매도·재진입 기준을 65 → 77로 바꿨을 때 비교 (급락매수 30 유지).

표본: 최근 5년 / 2011~2026. 전체기간 성과, 2022 약세장 구간, 롤링 2년.
결과: backtest/ag_resell77.csv
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


def run(df: pd.DataFrame, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
    bench = 100.0 * price / price[0]

    def row(name, level, eq):
        s, r2 = perf_from_equity(eq, dates), rolling(eq, bench, 504)
        return {"sample": sample, "candidate": name, "resell": level, **s, "dd_2022": eq[it] / eq[ip] - 1,
                "r2_worst": r2["worst"], "r2_neg": r2["neg"], "r2_win": r2["win"]}

    rows = [row("Buy&Hold", np.nan, bench)]
    for c in SIGNAL_CANDIDATES:
        if c["id"] not in "ABCDEFG":
            continue
        for level in (65, 77):
            rows.append(row(c["id"], level, simulate(fg, price, **(c["params"] | dict(resell_level=level)))))
    return rows


def main() -> None:
    full = load_full()
    five = full[full["date"] >= full["date"].max() - pd.DateOffset(years=5)].reset_index(drop=True)
    out = pd.DataFrame(run(five, "5y") + run(full, "2011"))
    out.to_csv(ROOT / "backtest" / "ag_resell77.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
