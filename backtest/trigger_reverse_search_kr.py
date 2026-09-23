"""K공포지수 × 코스피 전용 트리거 역산 탐색 (나스닥 때 했던 방식과 동일).

두 구조(F: 초기 40% 10일 분할·21일마다 10%, B: 초기 40% 분할없음·21일마다 10%)
× 매도기준(resell) × 급락기준(crash) 격자를 "최근5년"과 "전체(6.2년)" 두 표본에서
각각 탐색하고, 한쪽 표본의 상위 조합이 다른 표본에서도 버티는지(과적합 점검) 확인한다.
K공포지수 히스토리가 6.2년뿐이라 나스닥의 2011~2026(15.7년) 같은 긴 교차검증 표본은
아직 없다 — 이 점은 결과 해석 시 감안해야 한다.
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
from optimize_v2 import INITIAL_CAPITAL, perf_from_equity, simulate  # noqa: E402
from explore_kr import load_kr_arrays  # noqa: E402

STRUCTURES = {
    "F(초기40% 10일분할)": dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10),
    "B(초기40% 분할없음)": dict(initial_allocation=0.40, ramp_days=1, buy_interval_days=21, buy_step=0.10),
}
RESELL_RANGE = range(55, 91)
CRASH_RANGE = range(10, 46)


def samples(df_full: pd.DataFrame) -> dict[str, pd.DataFrame]:
    cutoff = df_full["date"].iloc[-1] - pd.DateOffset(years=5)
    return {
        "최근5년": df_full[df_full["date"] >= cutoff].reset_index(drop=True),
        "전체6.2년": df_full,
    }


def run_grid(df: pd.DataFrame) -> pd.DataFrame:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price = df["kospi"].to_numpy()
    dates = df["date"]
    bench = INITIAL_CAPITAL * (price / price[0])
    bench_perf = perf_from_equity(bench, dates)
    rows = []
    for sname, base in STRUCTURES.items():
        for resell, crash in product(RESELL_RANGE, CRASH_RANGE):
            if crash >= resell:
                continue
            eq = simulate(fg, price, resell_level=resell, crash_level=crash, **base)
            perf = perf_from_equity(eq, dates)
            rows.append({"structure": sname, "resell": resell, "crash": crash, **perf,
                         "beats_bh_return": perf["total_return"] > bench_perf["total_return"],
                         "beats_bh_sharpe": perf["sharpe_like"] > bench_perf["sharpe_like"]})
    out = pd.DataFrame(rows)
    print(f"  Buy&Hold: 수익률 {bench_perf['total_return']:.1%} / Sharpe {bench_perf['sharpe_like']:.3f} / MDD {bench_perf['max_drawdown']:.1%}")
    return out


def cross_check(top: pd.DataFrame, other_df: pd.DataFrame, label: str) -> pd.DataFrame:
    fg = other_df["fg"].shift(1).bfill().to_numpy()
    price = other_df["kospi"].to_numpy()
    dates = other_df["date"]
    rows = []
    for _, r in top.iterrows():
        base = STRUCTURES[r["structure"]]
        eq = simulate(fg, price, resell_level=int(r["resell"]), crash_level=int(r["crash"]), **base)
        perf = perf_from_equity(eq, dates)
        rows.append({"structure": r["structure"], "resell": r["resell"], "crash": r["crash"],
                     f"{label}_total_return": perf["total_return"], f"{label}_sharpe": perf["sharpe_like"],
                     f"{label}_mdd": perf["max_drawdown"]})
    return pd.DataFrame(rows)


def main() -> None:
    _, _, _, df_full = load_kr_arrays()
    samp = samples(df_full)

    grids: dict[str, pd.DataFrame] = {}
    for name, df in samp.items():
        print(f"\n[{name}] 표본 {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()} ({len(df)}거래일) 격자탐색")
        grids[name] = run_grid(df)
        grids[name].to_csv(ROOT / f"trigger_reverse_search_kr_{name}.csv", index=False)

    for name, g in grids.items():
        other_name = "전체6.2년" if name == "최근5년" else "최근5년"
        top_return = g.sort_values("total_return", ascending=False).head(3)
        top_sharpe = g.sort_values("sharpe_like", ascending=False).head(3)
        print(f"\n=== [{name}] 기준 상위 3 (수익률) -> {other_name}에서 재확인 ===")
        cc = cross_check(top_return, samp[other_name], other_name)
        print(pd.concat([top_return[["structure", "resell", "crash", "total_return", "sharpe_like", "max_drawdown"]].reset_index(drop=True), cc.drop(columns=["structure", "resell", "crash"])], axis=1).to_string(index=False))
        print(f"\n=== [{name}] 기준 상위 3 (Sharpe) -> {other_name}에서 재확인 ===")
        cc2 = cross_check(top_sharpe, samp[other_name], other_name)
        print(pd.concat([top_sharpe[["structure", "resell", "crash", "total_return", "sharpe_like", "max_drawdown"]].reset_index(drop=True), cc2.drop(columns=["structure", "resell", "crash"])], axis=1).to_string(index=False))

    for name, g in grids.items():
        n_beat_return = g["beats_bh_return"].sum()
        n_beat_sharpe = g["beats_bh_sharpe"].sum()
        print(f"\n[{name}] Buy&Hold를 수익률로 이긴 조합: {n_beat_return}/{len(g)}, Sharpe로 이긴 조합: {n_beat_sharpe}/{len(g)}")


if __name__ == "__main__":
    main()
