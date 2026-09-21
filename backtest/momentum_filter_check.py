"""FG 구성요소 '시장 모멘텀'(S&P500 vs 125일 이평) 대비 200일선 필터 비교.

FG에 이미 이평선 요소가 들어있으므로, 우리 필터의 이평선을 CNN 모멘텀과 같은 정의로 바꿔도 결과가
유지되는지 확인. CNN 구성요소 원자료는 2020-07부터라 S&P 기준 변형은 5년 표본에서만 가능.
결과: backtest/momentum_filter_check.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from optimize_v2 import perf_from_equity  # noqa: E402
from scenario_2022 import H, PEAK, TROUGH, simulate_overlay  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402


def hysteresis(on: pd.Series, off: pd.Series) -> np.ndarray:
    state, out = False, []
    for a, b in zip(on.to_numpy(), off.to_numpy()):
        state = (not b) if state else bool(a)
        out.append(state)
    return pd.Series(out, index=on.index).shift(1).fillna(False).to_numpy(dtype=bool)


def main() -> None:
    df = load_full()
    cnn = pd.read_csv(ROOT / "data" / "fear_greed.csv", parse_dates=["date"])[
        ["date", "market_momentum_sp500", "market_momentum_sp125"]]
    df = df.merge(cnn, on="date", how="left")
    c, fg = df["close"], df["fg"]
    greed = fg.rolling(60, min_periods=1).max() >= 70
    below = {
        "나스닥<200일선": (c < c.rolling(200).mean(), c > c.rolling(200).mean()),
        "나스닥<125일선": (c < c.rolling(125).mean(), c > c.rolling(125).mean()),
        "S&P500<125일선(CNN 모멘텀)": (df["market_momentum_sp500"] < df["market_momentum_sp125"],
                                   df["market_momentum_sp500"] > df["market_momentum_sp125"]),
    }
    masks = {}
    for name, (dn, up) in below.items():
        masks[f"탐욕소진 + {name}"] = hysteresis(greed & (fg < 40) & dn, up)
        masks[f"추세만: {name}"] = hysteresis(dn, up)

    cut = int((df["date"] >= df["date"].max() - pd.DateOffset(years=5)).idxmax())
    rows = []
    for sample, lo in (("5y", cut), ("2011", 0)):
        sub = df.iloc[lo:].reset_index(drop=True)
        f, p, d = sub["fg"].shift(1).bfill().to_numpy(), sub["close"].to_numpy(), sub["date"]
        ip, it = (int(d[d == x].index[0]) for x in (PEAK, TROUGH))
        for mname, mask in masks.items():
            if sample == "2011" and "CNN" in mname:
                continue  # CNN 구성요소 원자료는 2020-07부터
            m = mask[lo:]
            for cap in (0.0, 0.5):
                eq = simulate_overlay(f, p, m, cap, sell_fraction=0.5, **(H | dict(resell_level=77)))
                s = perf_from_equity(eq, d)
                rows.append({"sample": sample, "filter": mname, "cap": cap, **s, "dd_2022": eq[it] / eq[ip] - 1,
                             "episodes": int(np.sum(m[1:] & ~m[:-1]))})
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "backtest" / "momentum_filter_check.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
