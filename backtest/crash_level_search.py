"""매수 트리거(급락매수 기준 crash_level) 최적점 탐색.

기준: H/I 구조(초기 40%/10일, 21일/10%) + 매도 77에서 50% + 급락 전량매수.
  1D: crash_level 10~50, 추세 보험(나스닥<175일선×0.97 → 비중 50%) 있음/없음
  2D: 추세 보험 있음, resell 70~85 × crash 15~45 (트리거 쌍의 안정 구간 확인)
표본: 최근 5년 / 2011~2026. 결과: backtest/crash_level_search_1d.csv, crash_level_search_2d.csv
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from half_trade_rolling import rolling  # noqa: E402
from momentum_filter_check import hysteresis  # noqa: E402
from optimize_v2 import perf_from_equity  # noqa: E402
from scenario_2022 import H, PEAK, TROUGH, simulate_overlay  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

FILTER_MA = 175


def samples():
    full = load_full()
    c = full["close"]
    ma = c.rolling(FILTER_MA).mean()
    mask = hysteresis(c < ma * 0.97, c > ma)
    cut = int((full["date"] >= full["date"].max() - pd.DateOffset(years=5)).idxmax())
    return {"5y": (full.iloc[cut:].reset_index(drop=True), mask[cut:]), "2011": (full, mask)}


def evaluate(df, mask, resell, crash) -> dict:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
    eq = simulate_overlay(fg, price, mask, 0.5, sell_fraction=0.5,
                          **(H | dict(resell_level=resell, crash_level=crash)))
    s, r2 = perf_from_equity(eq, dates), rolling(eq, 100.0 * price / price[0], 504)
    return {**s, "dd_2022": eq[it] / eq[ip] - 1, "r2_worst": r2["worst"], "r2_neg": r2["neg"],
            "crash_buys": int(np.sum((fg < crash)[1:] & ~(fg < crash)[:-1]))}


def main() -> None:
    rows1, rows2 = [], []
    for sname, (df, mask) in samples().items():
        none = np.zeros(len(df), dtype=bool)
        for use_filter, crash in product((True, False), range(10, 51)):
            rows1.append({"sample": sname, "filter": use_filter, "crash": crash,
                          **evaluate(df, mask if use_filter else none, 77, crash)})
        for resell, crash in product(range(70, 86), range(15, 46)):
            rows2.append({"sample": sname, "resell": resell, "crash": crash, **evaluate(df, mask, resell, crash)})
    pd.DataFrame(rows1).to_csv(ROOT / "backtest" / "crash_level_search_1d.csv", index=False)
    pd.DataFrame(rows2).to_csv(ROOT / "backtest" / "crash_level_search_2d.csv", index=False)
    print(f"저장: 1D {len(rows1)}행, 2D {len(rows2)}행")


if __name__ == "__main__":
    main()
