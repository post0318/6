"""코스피 전용 추세 보험 파라미터 탐색 (나스닥 session 26의 trend_filter_search.py와 동일 방법론).

candidate J(나스닥 175일/3%/25%)를 코스피 자체 종가로 재계산했더니 오히려 손해였다
(notes/session28). 나스닥 파라미터를 그대로 옮기지 말고, 코스피 자신의 가격 리듬에 맞는
이평·버퍼·cap을 직접 찾는다. 기준 구조는 H/I(초기40% 10일분할·21일마다10%)+매도77(50%)+
급락30(전량매수), 여기에 추세 보험만 격자 탐색.

두 시장 각각 최근5년/전체 표본에서 탐색하고, 상위 조합이 다른 표본에서도 버티는지 확인한다.
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "analysis"))
from optimize_v2 import INITIAL_CAPITAL, perf_from_equity, simulate_with_trades  # noqa: E402
from explore_kr import load_kr_arrays, trend_state_on  # noqa: E402
from explore_cnn_kospi200 import load_samples as load_cnn_kospi200_samples  # noqa: E402

BASE = dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10,
            resell_level=77, sell_fraction=0.5)
MAS = [60, 80, 100, 125, 150, 175, 200]
BUFFERS = [0.0, 0.02, 0.03, 0.05]
CAPS = [0.0, 0.25, 0.5, 0.75]
CRASHES = [28, 29, 30, 31]


def kr_samples() -> dict[str, pd.DataFrame]:
    _, _, _, df_full = load_kr_arrays()
    cutoff = df_full["date"].iloc[-1] - pd.DateOffset(years=5)
    return {"최근5년": df_full[df_full["date"] >= cutoff].reset_index(drop=True), "전체6.2년": df_full}


def cnn_kospi200_samples() -> dict[str, pd.DataFrame]:
    samp = load_cnn_kospi200_samples()
    return {"최근5년": samp["최근5년"], "전체(2011~)": samp["전체(2011~)"]}


def run_grid(df: pd.DataFrame, price_col: str) -> tuple[pd.DataFrame, dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price = df[price_col].to_numpy()
    dates = df["date"]
    bench = INITIAL_CAPITAL * (price / price[0])
    bench_perf = perf_from_equity(bench, dates)
    rows = []
    for ma, buf in product(MAS, BUFFERS):
        risk_off = trend_state_on(price, dates, ma, buf)
        for cap, crash in product(CAPS, CRASHES):
            eq, *_ = simulate_with_trades(fg, price, dates, crash_level=crash, risk_off=risk_off,
                                          risk_off_cap=cap, risk_off_retrim=False, **BASE)
            perf = perf_from_equity(eq, dates)
            rows.append({"ma": ma, "buffer": buf, "cap": cap, "crash": crash, **perf})
    out = pd.DataFrame(rows)
    print(f"  Buy&Hold: 수익률 {bench_perf['total_return']:.1%} / Sharpe {bench_perf['sharpe_like']:.3f} / MDD {bench_perf['max_drawdown']:.1%}")
    return out, bench_perf


def cross_check(top: pd.DataFrame, other_df: pd.DataFrame, price_col: str, label: str) -> pd.DataFrame:
    fg = other_df["fg"].shift(1).bfill().to_numpy()
    price = other_df[price_col].to_numpy()
    dates = other_df["date"]
    rows = []
    for _, r in top.iterrows():
        risk_off = trend_state_on(price, dates, int(r["ma"]), float(r["buffer"]))
        eq, *_ = simulate_with_trades(fg, price, dates, crash_level=int(r["crash"]), risk_off=risk_off,
                                      risk_off_cap=float(r["cap"]), risk_off_retrim=False, **BASE)
        perf = perf_from_equity(eq, dates)
        rows.append({f"{label}_total_return": perf["total_return"], f"{label}_sharpe": perf["sharpe_like"],
                     f"{label}_mdd": perf["max_drawdown"]})
    return pd.DataFrame(rows)


def analyze(name: str, samples: dict[str, pd.DataFrame], price_col: str, tag: str) -> None:
    print(f"\n========== {name} ==========")
    grids: dict[str, pd.DataFrame] = {}
    for sname, df in samples.items():
        print(f"\n[{sname}] {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()} ({len(df)}거래일) 추세보험 격자탐색")
        g, _ = run_grid(df, price_col)
        g.to_csv(ROOT / f"trend_filter_search_kr_{tag}_{sname}.csv", index=False)
        grids[sname] = g

    names = list(samples.keys())
    for base_name in names:
        other_name = [n for n in names if n != base_name][0]
        g = grids[base_name]
        top = g.sort_values("sharpe_like", ascending=False).head(3)
        print(f"\n=== [{name}/{base_name}] Sharpe 상위3 -> {other_name}에서 재확인 ===")
        cc = cross_check(top, samples[other_name], price_col, other_name)
        merged = pd.concat([top[["ma", "buffer", "cap", "crash", "total_return", "sharpe_like", "max_drawdown"]].reset_index(drop=True), cc], axis=1)
        print(merged.to_string(index=False))


def main() -> None:
    analyze("K공포지수 x 코스피", kr_samples(), "kospi", "kfg")
    analyze("CNN FG x 코스피200(KODEX200)", cnn_kospi200_samples(), "close", "cnn")


if __name__ == "__main__":
    main()
