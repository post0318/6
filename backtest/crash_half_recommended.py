"""추천안(I 77 + 추세 보험)에서 급락매수를 100% → 50%로 바꾸면?

급락매수 50% 두 방식:
  매일 반복 : FG<31인 날마다 남은 현금의 50% (session 20의 crash_buy_fraction=0.5와 동일, 사실상 분할 재진입)
  국면당 1회: 급락 국면(FG≥50에서 리셋)당 한 번만 현금의 50%, 나머지는 정기 추가매수로
추세 보험: 나스닥 종가 < MA×0.97이면 비중 50%로 축소, MA 위 회복 시 복원 (MA 150/175/200).
결과: backtest/crash_half_recommended.csv
"""

from __future__ import annotations

import sys
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

CRASH = {"급락 100%": dict(), "급락 50% 매일반복": dict(crash_buy_fraction=0.5),
         "급락 50% 국면당1회": dict(crash_buy_fraction=0.5, crash_once=True)}
FILTERS = [None, 150, 175, 200]


def run(df: pd.DataFrame, masks: dict, lo: int, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
    bench = 100.0 * price / price[0]
    none = np.zeros(len(df), dtype=bool)
    rows = []
    for base, sf in (("I 77", 0.5), ("H 77", 1.0)):
        for ma in FILTERS:
            mask = none if ma is None else masks[ma][lo:]
            for cname, ckw in CRASH.items():
                eq = simulate_overlay(fg, price, mask, 0.5, sell_fraction=sf, **(H | dict(resell_level=77)), **ckw)
                s, r2 = perf_from_equity(eq, dates), rolling(eq, bench, 504)
                rows.append({"sample": sample, "base": base, "filter_ma": ma or "없음", "crash": cname, **s,
                             "dd_2022": eq[it] / eq[ip] - 1, "r2_worst": r2["worst"], "r2_neg": r2["neg"]})
    return rows


def main() -> None:
    full = load_full()
    c = full["close"]
    masks = {n: hysteresis(c < c.rolling(n).mean() * 0.97, c > c.rolling(n).mean()) for n in FILTERS if n}
    cut = int((full["date"] >= full["date"].max() - pd.DateOffset(years=5)).idxmax())
    five = full.iloc[cut:].reset_index(drop=True)
    out = pd.DataFrame(run(five, masks, cut, "5y") + run(full, masks, 0, "2011"))
    out.to_csv(ROOT / "backtest" / "crash_half_recommended.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
