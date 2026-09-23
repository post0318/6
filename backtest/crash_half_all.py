"""후보 A~I 전부에서 급락매수 100% vs 50%(매일반복 / 국면당 1회) 비교.

설정 두 가지:
  원래 설정 : A~G 65/30 전량매도, H 79/31 전량매도, I 79/31 매도50%
  추천 설정 : 매도기준 77 + 매도50% + 추세 보험(나스닥 < 175일선×0.97이면 비중 50%)
             (추천 설정에서는 H와 I가 같아져 'H/I'로 표기)
표본: 최근 5년 / 2011~2026. 결과: backtest/crash_half_all.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "backtest"))
from crash_half_recommended import CRASH  # noqa: E402
from export_dashboard_json import SIGNAL_CANDIDATES  # noqa: E402
from momentum_filter_check import hysteresis  # noqa: E402
from optimize_v2 import perf_from_equity  # noqa: E402
from scenario_2022 import H, PEAK, TROUGH, simulate_overlay  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

FILTER_MA = 175


def configs() -> list[tuple[str, str, dict, float, bool]]:
    """(설정, 후보, 파라미터, 매도비율, 추세보험 사용)"""
    ag = {c["id"]: c["params"] for c in SIGNAL_CANDIDATES if c["id"] in "ABCDEFG"}
    out = [("원래", k, v, 1.0, False) for k, v in ag.items()]
    out += [("원래", "H", H, 1.0, False), ("원래", "I", H, 0.5, False)]
    out += [("추천", k, v | dict(resell_level=77), 0.5, True) for k, v in ag.items()]
    out += [("추천", "H/I", H | dict(resell_level=77), 0.5, True)]
    return out


def run(df: pd.DataFrame, mask: np.ndarray, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
    none = np.zeros(len(df), dtype=bool)
    rows = []
    for setting, cid, params, sf, use_filter in configs():
        for cname, ckw in CRASH.items():
            eq = simulate_overlay(fg, price, mask if use_filter else none, 0.5, sell_fraction=sf, **params, **ckw)
            s = perf_from_equity(eq, dates)
            rows.append({"sample": sample, "setting": setting, "candidate": cid, "crash": cname, **s,
                         "dd_2022": eq[it] / eq[ip] - 1})
    return rows


def main() -> None:
    full = load_full()
    c = full["close"]
    ma = c.rolling(FILTER_MA).mean()
    mask = hysteresis(c < ma * 0.97, c > ma)
    cut = int((full["date"] >= full["date"].max() - pd.DateOffset(years=5)).idxmax())
    five = full.iloc[cut:].reset_index(drop=True)
    out = pd.DataFrame(run(five, mask[cut:], "5y") + run(full, mask, "2011"))
    out.to_csv(ROOT / "backtest" / "crash_half_all.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
