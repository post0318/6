"""급락 '전량'매수 규칙 대안 비교.

2022 실패의 핵심: 2021-12-01 FG 24.8에서 남은 현금 전부 매수(나스닥은 고점 대비 -5%뿐) → 이후 -33%.
결과를 보기 전에 원리로 정한 대안 3가지 + 각각 인접 파라미터(견고성 확인):
  fg_tiers : FG 깊이별 분할 — 급락 국면 첫 신호 때 현금을 n등분, FG가 각 단계 아래로 갈 때마다 1/n씩
  dd_tiers : 가격 낙폭별 분할 — FG<31이면서 나스닥이 52주 고점 대비 각 단계 이상 빠졌을 때마다 1/n씩
  bounce   : 반등 확인 — FG<31 이후 국면 최저 FG에서 B포인트 반등하면 전량 (README 가설 1)
급락 국면은 FG≥50이 되면 리셋. 정기 추가매수 로직은 기존과 동일.
기준 전략: I 77(F 구조, 매도 77·50%) / H 77(매도 100%). 결과: backtest/crash_buy_rules.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from half_trade_rolling import rolling  # noqa: E402
from optimize_v2 import INITIAL_CAPITAL, perf_from_equity  # noqa: E402
from scenario_2022 import PEAK, TROUGH  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

BASE = dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=77, crash_level=31)
RESET_LEVEL = 50


def simulate_crash(fg, price, dd, rule, arg, initial_allocation, ramp_days, buy_interval_days, buy_step,
                   resell_level, crash_level, sell_fraction):
    """optimize_v2.simulate와 같은 로직에서 급락매수 분기만 rule로 교체. rule='full'이면 기존과 동일."""
    n = len(fg)
    cash, shares = INITIAL_CAPITAL, 0.0
    buying_active = sold_flag = False
    days_since = 0
    ramp_daily = initial_allocation / ramp_days
    epi, epi_cash, epi_min, done = False, 0.0, 100.0, set()
    equity = np.empty(n)
    for i in range(n):
        f, p = fg[i], price[i]
        total = cash + shares * p
        if f >= RESET_LEVEL:
            epi, done = False, set()
        if i < ramp_days:
            bv = min(cash, ramp_daily * total)
            shares += bv / p
            cash -= bv
        else:
            cw = shares * p / total
            if cw > 1e-9 and f >= resell_level and not (sell_fraction < 1.0 and sold_flag):
                sold = shares * sell_fraction
                cash += sold * p
                shares -= sold
                buying_active, sold_flag, days_since = False, True, 0
            else:
                was_active = buying_active
                if f < resell_level:
                    buying_active, sold_flag = True, False
                if buying_active and not was_active:
                    days_since = 0
                if buying_active and f < crash_level and not epi:
                    epi, epi_cash, epi_min, done = True, cash, f, set()
                if epi:
                    epi_min = min(epi_min, f)
                buy = 0.0
                if buying_active and epi and cash > 1e-9:
                    if rule == "full":
                        buy = cash if f < crash_level else 0.0
                    elif rule == "fg_tiers":
                        for k, lvl in enumerate(arg):
                            if f < lvl and k not in done:
                                done.add(k)
                                buy += epi_cash / len(arg)
                    elif rule == "dd_tiers":
                        if f < crash_level:
                            for k, lvl in enumerate(arg):
                                if dd[i] <= lvl and k not in done:
                                    done.add(k)
                                    buy += epi_cash / len(arg)
                    elif rule == "bounce":
                        if f >= epi_min + arg and "b" not in done:
                            done.add("b")
                            buy = cash
                buy = min(buy, cash)
                if buy > 0:
                    shares += buy / p
                    cash -= buy
                    days_since = 0
                else:
                    days_since += 1
                    total = cash + shares * p
                    if buying_active and days_since >= buy_interval_days and shares * p / total < 1 - 1e-9:
                        bv = min(cash, buy_step * total)
                        shares += bv / p
                        cash -= bv
                        days_since = 0
        equity[i] = cash + shares * p
    return equity


RULES = {
    "기존: FG<31 전량": ("full", None),
    "FG 분할 31/20/10": ("fg_tiers", (31, 20, 10)),
    "FG 분할 31/25/15": ("fg_tiers", (31, 25, 15)),
    "FG 분할 31/15/5": ("fg_tiers", (31, 15, 5)),
    "낙폭 분할 -10/-20/-30%": ("dd_tiers", (-0.10, -0.20, -0.30)),
    "낙폭 분할 -8/-16/-24%": ("dd_tiers", (-0.08, -0.16, -0.24)),
    "낙폭 분할 -12/-24/-36%": ("dd_tiers", (-0.12, -0.24, -0.36)),
    "반등확인 +5": ("bounce", 5),
    "반등확인 +10": ("bounce", 10),
    "반등확인 +15": ("bounce", 15),
}


def run(df: pd.DataFrame, dd_full: np.ndarray, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
    bench = 100.0 * price / price[0]
    rows = []
    for base, sf in (("I 77", 0.5), ("H 77", 1.0)):
        for name, (rule, arg) in RULES.items():
            eq = simulate_crash(fg, price, dd_full, rule, arg, sell_fraction=sf, **BASE)
            s, r1, r2 = perf_from_equity(eq, dates), rolling(eq, bench, 252), rolling(eq, bench, 504)
            rows.append({"sample": sample, "base": base, "rule": name, **s, "dd_2022": eq[it] / eq[ip] - 1,
                         "r1_worst": r1["worst"], "r1_neg": r1["neg"], "r2_worst": r2["worst"], "r2_neg": r2["neg"]})
    return rows


def main() -> None:
    full = load_full()
    c = full["close"]
    dd = (c / c.rolling(252, min_periods=1).max() - 1).shift(1).fillna(0).to_numpy()  # 전일 기준
    cut = int((full["date"] >= full["date"].max() - pd.DateOffset(years=5)).idxmax())
    five = full.iloc[cut:].reset_index(drop=True)
    out = pd.DataFrame(run(five, dd[cut:], "5y") + run(full, dd, "2011"))
    out.to_csv(ROOT / "backtest" / "crash_buy_rules.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
