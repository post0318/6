"""F/79/31 트리거 기준 구조 탐색.

상수:  (구조 F)   초기편입 40% / 10일 분할 / 재진입·매도 79 / 급락 31
       (구조 A79) 초기편입 50% / 1일 편입   / 재진입·매도 79 / 급락 31
       (구조 A65) 초기편입 50% / 1일 편입   / 재진입·매도 65 / 급락 30  (v2-optimal 원래 트리거)
변수:  buy_interval_days, buy_step, crash_buy_fraction

표본 두 가지로 교차검증: 최근 5년(과적합 소지 큼) / 2011~2026 전체(사건 수 많아 견고).
결과: backtest/structure_search_7931.csv
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

STRUCTURES = {
    "F79": dict(initial_allocation=0.40, ramp_days=10, resell_level=79, crash_level=31),
    "A79": dict(initial_allocation=0.50, ramp_days=1, resell_level=79, crash_level=31),
    "A65": dict(initial_allocation=0.50, ramp_days=1, resell_level=65, crash_level=30),
}
INTERVALS = [3, 5, 7, 10, 14, 21, 28, 42, 63]
STEPS = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
FRACS = [0.0, 0.25, 0.5, 0.75, 1.0]


def load_full() -> pd.DataFrame:
    fg = _load_fg_combined()
    idx = pd.read_csv(ROOT / "data" / "nasdaq.csv", parse_dates=["date"])
    return pd.merge(fg, idx[["date", "close"]], on="date", how="inner").sort_values("date").reset_index(drop=True)


def run(df: pd.DataFrame, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()  # 1일 체결지연 (session 14)
    price, dates = df["close"].to_numpy(), df["date"]
    bench = perf_from_equity(100.0 * (price / price[0]), dates)
    rows = []
    for sname, s in STRUCTURES.items():
        for interval, step, frac in product(INTERVALS, STEPS, FRACS):
            eq = simulate(fg, price, buy_interval_days=interval, buy_step=step, crash_buy_fraction=frac, **s)
            stats = perf_from_equity(eq, dates)
            rows.append({
                "sample": sample, "structure": sname, "interval": interval, "step": step, "crash_frac": frac,
                **stats, "bench_return": bench["total_return"], "bench_sharpe": bench["sharpe_like"],
            })
    return rows


def main() -> None:
    full = load_full()
    five = full[full["date"] >= full["date"].max() - pd.DateOffset(years=5)].reset_index(drop=True)
    rows = run(five, "5y") + run(full, "2011")
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "backtest" / "structure_search_7931.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
