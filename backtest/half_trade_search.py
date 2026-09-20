"""급락매수·매도를 전량(100%) 대신 50%만 하면? (session 20)

1) 4개 구조 x (급락매수 100/50%) x (매도 100/50%) 직접 비교, 두 표본(최근 5년 / 2011~2026)
2) (50%,50%) 규칙에서 트리거(재진입·매도, 급락) 격자 탐색을 (100%,100%)와 나란히 비교

매도 50%는 FG>=재진입·매도 국면당 1회만 50% 매도(optimize_v2.simulate의 sell_fraction 참고).
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "backtest"))
from explore import _load_fg_combined  # noqa: E402
from optimize_v2 import perf_from_equity, simulate  # noqa: E402

STRUCTS = {
    "A(50%/1일,20%)@65/30": dict(initial_allocation=0.50, ramp_days=1, buy_interval_days=21, buy_step=0.20, resell_level=65, crash_level=30),
    "B(40%/1일,10%)@65/30": dict(initial_allocation=0.40, ramp_days=1, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30),
    "F(40%/10일,10%)@65/30": dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30),
    "H=F@79/31": dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=79, crash_level=31),
}
FRACS = [1.0, 0.5]


def samples() -> dict[str, pd.DataFrame]:
    fg = _load_fg_combined()
    idx = pd.read_csv(ROOT / "data" / "nasdaq.csv", parse_dates=["date"])
    full = pd.merge(fg, idx[["date", "close"]], on="date", how="inner").sort_values("date").reset_index(drop=True)
    five = full[full["date"] >= full["date"].max() - pd.DateOffset(years=5)].reset_index(drop=True)
    return {"5y": five, "2011": full}


def arrays(df: pd.DataFrame):
    return df["fg"].shift(1).bfill().to_numpy(), df["close"].to_numpy(), df["date"]


def main() -> None:
    rows = []
    for sname, df in samples().items():
        fg, price, dates = arrays(df)
        bench = perf_from_equity(100.0 * (price / price[0]), dates)
        for stname, p in STRUCTS.items():
            for cf, sf in product(FRACS, FRACS):
                st = perf_from_equity(simulate(fg, price, crash_buy_fraction=cf, sell_fraction=sf, **p), dates)
                rows.append({"sample": sname, "structure": stname, "crash_buy": cf, "sell": sf, **st,
                             "bench_return": bench["total_return"], "bench_sharpe": bench["sharpe_like"]})
    pd.DataFrame(rows).to_csv(ROOT / "backtest" / "half_trade_compare.csv", index=False)

    grid = []
    base = STRUCTS["F(40%/10일,10%)@65/30"]
    base = {k: v for k, v in base.items() if k not in ("resell_level", "crash_level")}
    for sname, df in samples().items():
        fg, price, dates = arrays(df)
        for resell, crash, (cf, sf) in product(range(55, 91, 5), range(10, 41, 5), [(1.0, 1.0), (0.5, 0.5)]):
            if crash >= resell:
                continue
            st = perf_from_equity(simulate(fg, price, resell_level=resell, crash_level=crash,
                                           crash_buy_fraction=cf, sell_fraction=sf, **base), dates)
            grid.append({"sample": sname, "resell": resell, "crash": crash, "crash_buy": cf, "sell": sf, **st})
    pd.DataFrame(grid).to_csv(ROOT / "backtest" / "half_trade_trigger_grid.csv", index=False)
    print("saved")


if __name__ == "__main__":
    main()
