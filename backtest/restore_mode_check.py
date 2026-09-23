"""추세 보험 해제 시 즉시 복원 vs 복원 없이 정기매수로만 채우기 (session 29).

기준: 후보 J(매도 77·50%, 급락 30 전량, 175일선×0.97 → 비중 25%, 발동 시 1회 축소).
복원 없음일 때는 정기매수(주기·비중)를 몇 가지 바꿔 함께 본다. 표본: 최근 5년 / 2011~2026.
결과: backtest/restore_mode_check.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from half_trade_rolling import rolling  # noqa: E402
from momentum_filter_check import hysteresis  # noqa: E402
from optimize_v2 import perf_from_equity  # noqa: E402
from scenario_2022 import H, PEAK, TROUGH, simulate_overlay  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

J = H | dict(resell_level=77, crash_level=30)
VARIANTS = {
    "즉시 복원 (현재 J)": (True, {}),
    "복원 없음, 정기 21일/10%": (False, {}),
    "복원 없음, 정기 21일/20%": (False, dict(buy_step=0.20)),
    "즉시 복원, 정기 14일/10%": (True, dict(buy_interval_days=14)),
    "복원 없음, 정기 14일/10%": (False, dict(buy_interval_days=14)),
    "복원 없음, 정기 14일/20%": (False, dict(buy_interval_days=14, buy_step=0.20)),
    "복원 없음, 정기 10일/10%": (False, dict(buy_interval_days=10)),
    "복원 없음, 정기 5일/10%": (False, dict(buy_interval_days=5)),
}


def main() -> None:
    full = load_full()
    c = full["close"]
    ma = c.rolling(175).mean()
    mask = hysteresis(c < ma * 0.97, c > ma)
    cut = int((full["date"] >= full["date"].max() - pd.DateOffset(years=5)).idxmax())
    rows = []
    for sample, lo in (("5y", cut), ("2011", 0)):
        df = full.iloc[lo:].reset_index(drop=True)
        fg, price, dates = df["fg"].shift(1).bfill().to_numpy(), df["close"].to_numpy(), df["date"]
        ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
        bench = 100.0 * price / price[0]
        for name, (restore, over) in VARIANTS.items():
            eq = simulate_overlay(fg, price, mask[lo:], 0.25, sell_fraction=0.5, retrim=False, restore=restore,
                                  **(J | over))
            s, r1, r2 = perf_from_equity(eq, dates), rolling(eq, bench, 252), rolling(eq, bench, 504)
            rows.append({"sample": sample, "variant": name, **s, "dd_2022": eq[it] / eq[ip] - 1,
                         "r1_worst": r1["worst"], "r2_worst": r2["worst"], "r2_neg": r2["neg"], "r2_win": r2["win"]})
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "backtest" / "restore_mode_check.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
