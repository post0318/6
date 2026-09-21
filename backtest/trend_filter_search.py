"""추세 보험 파라미터 × 매수 트리거 공동 탐색.

기준: H/I 구조 + 매도 77에서 50% + 급락 전량매수.
변수: 이평 기간(MA) × 이탈 버퍼(종가 < MA×(1-buffer)이면 발동, MA 위 회복 시 해제) × 축소 비중(cap)
      × 매수 트리거(crash).
표본: 최근 5년 / 2011~2026. 결과: backtest/trend_filter_search.csv
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from half_trade_rolling import rolling  # noqa: E402
from momentum_filter_check import hysteresis  # noqa: E402
from optimize_v2 import perf_from_equity  # noqa: E402
from scenario_2022 import H, PEAK, TROUGH, simulate_overlay  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

MAS = [100, 125, 150, 175, 200, 225, 250]
BUFFERS = [0.0, 0.02, 0.03, 0.05]
CAPS = [0.0, 0.25, 0.5, 0.75]
CRASHES = [28, 29, 30, 31]


def main() -> None:
    full = load_full()
    c = full["close"]
    cut = int((full["date"] >= full["date"].max() - pd.DateOffset(years=5)).idxmax())
    samples = {"5y": (full.iloc[cut:].reset_index(drop=True), cut), "2011": (full, 0)}
    rows = []
    for ma, buf in product(MAS, BUFFERS):
        m = c.rolling(ma).mean()
        mask_full = hysteresis(c < m * (1 - buf), c > m)
        for sname, (df, lo) in samples.items():
            fg = df["fg"].shift(1).bfill().to_numpy()
            price, dates = df["close"].to_numpy(), df["date"]
            ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
            bench = 100.0 * price / price[0]
            mask = mask_full[lo:]
            for cap, crash in product(CAPS, CRASHES):
                eq = simulate_overlay(fg, price, mask, cap, sell_fraction=0.5,
                                      **(H | dict(resell_level=77, crash_level=crash)))
                s, r2 = perf_from_equity(eq, dates), rolling(eq, bench, 504)
                rows.append({"sample": sname, "ma": ma, "buffer": buf, "cap": cap, "crash": crash, **s,
                             "dd_2022": eq[it] / eq[ip] - 1, "r2_worst": r2["worst"], "r2_neg": r2["neg"],
                             "episodes": int((mask[1:] & ~mask[:-1]).sum())})
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "backtest" / "trend_filter_search.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
