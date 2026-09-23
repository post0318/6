"""K공포지수(5번 프로젝트, KRX 데이터 기반 국내판 공포·탐욕지수) × 코스피 1차 분석.

CNN FG × 나스닥 분석과 동일한 방법론을 그대로 적용한다: 신호-체결 1일 지연
(fg.shift(1).bfill()), 기존에 찾은 A~I 전략 파라미터를 그대로 재사용(코스피 전용
재탐색은 아직 하지 않음 — 1차 점검 결과를 보고 진행 여부를 정한다).

데이터 출처: data/kr_fg_full.json (5번 프로젝트 /api/macro/kr-fg-history export,
2026-09-23 fetch). K공포지수 history: 2020-07-06~. 코스피 종가: 2020-05-27~.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from optimize_v2 import INITIAL_CAPITAL, perf_from_equity, simulate  # noqa: E402

KR_JSON = ROOT / "data" / "kr_fg_full.json"

SIGNAL_CANDIDATES = [
    ("A", dict(initial_allocation=0.50, ramp_days=1, buy_interval_days=21, buy_step=0.20, resell_level=65, crash_level=30)),
    ("B", dict(initial_allocation=0.40, ramp_days=1, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30)),
    ("C", dict(initial_allocation=0.40, ramp_days=2, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30)),
    ("D", dict(initial_allocation=0.40, ramp_days=5, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30)),
    ("E", dict(initial_allocation=0.40, ramp_days=5, buy_interval_days=14, buy_step=0.10, resell_level=65, crash_level=30)),
    ("F", dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30)),
    ("G", dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=14, buy_step=0.10, resell_level=65, crash_level=30)),
    ("H", dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=79, crash_level=31)),
    ("I", dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=79, crash_level=31, sell_fraction=0.5)),
]


def load_kr_arrays() -> tuple[np.ndarray, np.ndarray, pd.Series, pd.DataFrame]:
    data = json.loads(KR_JSON.read_text(encoding="utf-8"))
    fg = pd.DataFrame(data["history"]).rename(columns={"value": "fg"})
    px = pd.DataFrame(data["kospiHistory"]).rename(columns={"close": "kospi"})
    fg["date"] = pd.to_datetime(fg["date"])
    px["date"] = pd.to_datetime(px["date"])
    df = pd.merge(fg, px, on="date", how="inner").dropna(subset=["kospi"]).sort_values("date").reset_index(drop=True)
    fg_lagged = df["fg"].shift(1).bfill()
    return fg_lagged.to_numpy(), df["kospi"].to_numpy(), df["date"], df


def correlation_check(df: pd.DataFrame) -> None:
    """CNN/나스닥 분석에서 1일 지연을 쓴 근거(당일 FG가 당일 수익률과 동행) 재확인."""
    ret = df["kospi"].pct_change()
    same_day = df["fg"].corr(ret)
    next_day = df["fg"].corr(ret.shift(-1))
    print(f"[상관관계 점검] FG(당일) vs 당일수익률: {same_day:.3f} / FG(당일) vs 익일수익률: {next_day:.3f}")
    print("  -> 나스닥과 같은 패턴(당일 동행, 익일 예측력 약함)이면 1일 지연 적용이 K공포지수에도 타당하다.\n")


def run_sample(name: str, df: pd.DataFrame) -> pd.DataFrame:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price = df["kospi"].to_numpy()
    dates = df["date"]
    bench = INITIAL_CAPITAL * (price / price[0])
    rows = [{"sample": name, "id": "Buy&Hold", **perf_from_equity(bench, dates)}]
    for cid, params in SIGNAL_CANDIDATES:
        eq = simulate(fg, price, **params)
        rows.append({"sample": name, "id": cid, **perf_from_equity(eq, dates)})
    return pd.DataFrame(rows)


def main() -> None:
    _, _, dates_full, df_full = load_kr_arrays()
    print(f"전체 표본: {dates_full.iloc[0].date()} ~ {dates_full.iloc[-1].date()} "
          f"({len(df_full)}거래일, {(dates_full.iloc[-1]-dates_full.iloc[0]).days/365.25:.1f}년)\n")

    correlation_check(df_full)

    cutoff = dates_full.iloc[-1] - pd.DateOffset(years=5)
    df_5y = df_full[df_full["date"] >= cutoff].reset_index(drop=True)
    print(f"최근 5년 표본(나스닥 분석과 동일 기준): {df_5y['date'].iloc[0].date()} ~ {df_5y['date'].iloc[-1].date()} ({len(df_5y)}거래일)\n")

    out = pd.concat([run_sample("전체(6.2년)", df_full), run_sample("최근5년", df_5y)], ignore_index=True)
    print("[성과 — 기존 나스닥용 A~I 파라미터를 코스피에 그대로 적용, 코스피 전용 재탐색 전]")
    print(out.to_string(index=False))
    out.to_csv(ROOT / "backtest" / "kr_candidates_v1.csv", index=False)
    print(f"\n저장: backtest/kr_candidates_v1.csv")


if __name__ == "__main__":
    main()
