"""CNN Fear&Greed(원본, 미국)를 그대로 신호로 쓰되, 매매 대상만 나스닥 대신
코스피200(KODEX 200 ETF, 069500.KS)으로 바꾼 버전.

목적: "미국 투자자 심리가 한국 시장에도 역발상 신호로 통하는가?"를 K공포지수(국내
자체 지수, explore_kr.py에서 이미 확인)와 별도로 점검한다. FG 데이터/지연/구조는
나스닥 분석과 완전히 동일 — 가격 시계열만 교체.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "analysis"))
from explore import _load_fg_combined  # noqa: E402
from optimize_v2 import INITIAL_CAPITAL, perf_from_equity, simulate_with_trades  # noqa: E402
from export_dashboard_json import SIGNAL_CANDIDATES as _NASDAQ_CANDIDATES  # noqa: E402
from explore_kr import sim_kwargs_local  # noqa: E402

KOSPI200_PATH = ROOT / "data" / "kospi200.csv"

# 나스닥용 export_dashboard_json.SIGNAL_CANDIDATES(A~J)를 그대로 가져온다.
# J의 175일선 추세 보험은 나스닥이 아니라 코스피200(매매 대상) 자신의 종가로 재계산(explore_kr 공용 함수).
SIGNAL_CANDIDATES = [(c["id"], c["params"]) for c in _NASDAQ_CANDIDATES]


def load_samples() -> dict[str, pd.DataFrame]:
    fg = _load_fg_combined()
    idx = pd.read_csv(KOSPI200_PATH, parse_dates=["date"])
    full = pd.merge(fg, idx[["date", "close"]], on="date", how="inner").sort_values("date").reset_index(drop=True)
    five = full[full["date"] >= full["date"].max() - pd.DateOffset(years=5)].reset_index(drop=True)
    return {"전체(2011~)": full, "최근5년": five}


def run_sample(name: str, df: pd.DataFrame) -> pd.DataFrame:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price = df["close"].to_numpy()
    dates = df["date"]
    bench = INITIAL_CAPITAL * (price / price[0])
    rows = [{"sample": name, "id": "Buy&Hold", **perf_from_equity(bench, dates)}]
    for cid, params in SIGNAL_CANDIDATES:
        eq, *_ = simulate_with_trades(fg, price, dates, **sim_kwargs_local(params, price, dates))
        rows.append({"sample": name, "id": cid, **perf_from_equity(eq, dates)})
    return pd.DataFrame(rows)


def main() -> None:
    samp = load_samples()
    for name, df in samp.items():
        print(f"[{name}] {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()} ({len(df)}거래일)")

    out = pd.concat([run_sample(name, df) for name, df in samp.items()], ignore_index=True)
    print("\n[CNN FG(원본) 신호 -> 코스피200(KODEX 200 ETF) 매매, 나스닥용 A~J 파라미터 그대로(J 추세보험은 코스피200 자체 종가 기준)]")
    print(out.to_string(index=False))
    out.to_csv(ROOT / "backtest" / "cnn_fg_kospi200_v1.csv", index=False)
    print("\n저장: backtest/cnn_fg_kospi200_v1.csv")


if __name__ == "__main__":
    main()
