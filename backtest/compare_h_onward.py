"""후보 H 이후 변형 통합 비교 (session 20~22 결과 한데 모음).

모두 F 구조(초기 40%/10일 분할) + 급락매수 31 기반. 비교 항목: 전체기간 성과, 2022 약세장 구간,
롤링 1/2년(평균·최악·손실확률·BnH대비승률). 표본: 최근 5년 / 2011~2026.
필터 신호(scenario_2022.signals)는 전체 데이터로 계산 후 잘라 써서 5년 표본 시작부터 200일선이 유효.
결과: backtest/compare_h_onward.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from half_trade_rolling import rolling  # noqa: E402
from optimize_v2 import perf_from_equity  # noqa: E402
from scenario_2022 import H, PEAK, TROUGH, signals, simulate_overlay  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

GREED = "탐욕소진: 60일내 FG≥70 후 FG<40 & 200일선 아래"
# 이름: (매도비율, 파라미터 덮어쓰기, 필터 사용, cap)
VARIANTS = {
    "H (79, 21일/10%)": (1.0, {}, False, 1.0),
    "I (H+매도50%)": (0.5, {}, False, 1.0),
    "I 42일/75%": (0.5, dict(buy_interval_days=42, buy_step=0.75), False, 1.0),
    "H 77": (1.0, dict(resell_level=77), False, 1.0),
    "I 77": (0.5, dict(resell_level=77), False, 1.0),
    "H + 탐욕소진(전량)": (1.0, {}, True, 0.0),
    "I + 탐욕소진(전량)": (0.5, {}, True, 0.0),
    "I + 탐욕소진(50%)": (0.5, {}, True, 0.5),
    "I 77 + 탐욕소진(전량)": (0.5, dict(resell_level=77), True, 0.0),
    "I 77 + 탐욕소진(50%)": (0.5, dict(resell_level=77), True, 0.5),
    "I 42일/75% + 77 + 탐욕소진(50%)": (0.5, dict(resell_level=77, buy_interval_days=42, buy_step=0.75), True, 0.5),
}


def run(df: pd.DataFrame, mask_full: np.ndarray, sample: str) -> list[dict]:
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH))
    bench = 100.0 * price / price[0]
    none = np.zeros(len(df), dtype=bool)
    curves = {"Buy&Hold": bench}
    for name, (sf, over, use_filter, cap) in VARIANTS.items():
        curves[name] = simulate_overlay(fg, price, mask_full if use_filter else none, cap,
                                        sell_fraction=sf, **(H | over))
    rows = []
    for name, eq in curves.items():
        s = perf_from_equity(eq, dates)
        r1, r2 = rolling(eq, bench, 252), rolling(eq, bench, 504)
        rows.append({"sample": sample, "strategy": name, **s, "dd_2022": eq[it] / eq[ip] - 1,
                     "r1_mean": r1["mean"], "r1_worst": r1["worst"], "r1_neg": r1["neg"], "r1_win": r1["win"],
                     "r2_mean": r2["mean"], "r2_worst": r2["worst"], "r2_neg": r2["neg"], "r2_win": r2["win"]})
    return rows


def main() -> None:
    full = load_full()
    mask = signals(full)[GREED]
    cut = int((full["date"] >= full["date"].max() - pd.DateOffset(years=5)).idxmax())
    five = full.iloc[cut:].reset_index(drop=True)
    out = pd.DataFrame(run(five, mask[cut:], "5y") + run(full, mask, "2011"))
    out.to_csv(ROOT / "backtest" / "compare_h_onward.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
