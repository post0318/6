"""K공포지수(5번 프로젝트, KRX 데이터 기반 국내판 공포·탐욕지수) × 코스피 1차 분석.

CNN FG × 나스닥 분석과 동일한 방법론을 그대로 적용한다: 신호-체결 1일 지연
(fg.shift(1).bfill()), 나스닥용으로 찾은 A~J 전략 파라미터(export_dashboard_json의
최신 SIGNAL_CANDIDATES, J=최종추천)를 그대로 재사용 — 코스피 전용 재탐색은 별도로
trigger_reverse_search_kr.py에서 진행. candidate J의 175일선 추세 보험은 나스닥이
아니라 코스피 자신의 종가로 재계산한다(trend_state_on).

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
from optimize_v2 import INITIAL_CAPITAL, perf_from_equity, simulate, simulate_with_trades  # noqa: E402
from export_dashboard_json import SIGNAL_CANDIDATES as _NASDAQ_CANDIDATES, TREND_KEYS  # noqa: E402

KR_JSON = ROOT / "data" / "kr_fg_full.json"

# 나스닥용 export_dashboard_json.SIGNAL_CANDIDATES(A~J, J는 175일선 추세 보험 포함)를
# 그대로 가져온다 — 트리거·구조 파라미터는 동일, 추세 보험만 "코스피 자신의" 종가로 재계산.
SIGNAL_CANDIDATES = [(c["id"], c["params"]) for c in _NASDAQ_CANDIDATES]


def trend_state_on(price: np.ndarray, dates: pd.Series, ma: int, buffer: float) -> np.ndarray:
    """candidate J의 추세 보험을 나스닥이 아니라 실제 매매 대상(코스피/코스피200) 종가 기준으로 재계산."""
    s = pd.Series(price, index=pd.DatetimeIndex(dates))
    m = s.rolling(ma).mean()
    on, off = (s < m * (1 - buffer)).to_numpy(), (s > m).to_numpy()
    state, out = False, []
    for a, b in zip(on, off):
        state = (not b) if state else bool(a)
        out.append(state)
    signal = pd.Series(out, index=s.index).shift(1, fill_value=False)
    return signal.to_numpy(dtype=bool)


def sim_kwargs_local(params: dict, price: np.ndarray, dates: pd.Series) -> dict:
    kw = {k: v for k, v in params.items() if k not in TREND_KEYS}
    if "trend_ma" in params:
        kw["risk_off"] = trend_state_on(price, dates, params["trend_ma"], params["trend_buffer"])
        kw["risk_off_cap"] = params["trend_cap"]
    return kw


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
        eq, *_ = simulate_with_trades(fg, price, dates, **sim_kwargs_local(params, price, dates))
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
    print("[성과 — 나스닥용 A~J 파라미터(J=최종추천, 175일선 추세 보험 포함)를 코스피에 그대로 적용, 코스피 전용 재탐색 전]")
    print(out.to_string(index=False))
    out.to_csv(ROOT / "backtest" / "kr_candidates_v1.csv", index=False)
    print(f"\n저장: backtest/kr_candidates_v1.csv")


if __name__ == "__main__":
    main()
