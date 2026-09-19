"""v2 로직(계단식 매수, 초기 램프업, 단일 재진입/매도 임계값, 급락 전량매수)을 그대로 둔 채
resell_level(매도&재진입 임계값)과 crash_full_buy(급락 전량매수 임계값)만 스캔해서
v1(session3, 104.6%/vol 15.1%)과 Buy&Hold(137.9%/vol 16.6%)를 동시에 이기는 조합이
있는지 찾는다.

기준:
- best: total_return > Buy&Hold total_return AND annualized_vol < v1 annualized_vol
  (수익률과 변동성 둘 다 잡는 조합)
- 차선: total_return > Buy&Hold total_return (변동성은 못 잡아도 수익률 우선)
"""

from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strategy_fg_threshold import perf_stats  # noqa: E402
import strategy_fg_gradual as sg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

V1_TOTAL_RETURN = 1.0456
V1_VOL = 0.1513
BENCH_TOTAL_RETURN = 1.3792
BENCH_VOL = 0.1657

RESELL_LEVELS = [60, 62.5, 65, 67.5, 70, 72.5, 75, 77.5, 80]
CRASH_LEVELS = [10, 12.5, 15, 17.5, 20, 22.5, 25]


def run_one(resell_level: float, crash_level: float, df: pd.DataFrame) -> dict:
    sg.RESELL_LEVEL = resell_level
    sg.CRASH_FULL_BUY = crash_level
    bt_df, trades = sg.run_strategy(df.copy())
    strat_stats = perf_stats(bt_df["strategy_equity"], bt_df["date"])
    return {
        "resell_level": resell_level,
        "crash_level": crash_level,
        "num_trades": len(trades),
        **strat_stats,
    }


def main() -> None:
    df = sg.load_data()
    results = []
    for resell_level, crash_level in product(RESELL_LEVELS, CRASH_LEVELS):
        if crash_level >= resell_level:
            continue
        results.append(run_one(resell_level, crash_level, df))

    results_df = pd.DataFrame(results).sort_values("total_return", ascending=False)

    beats_both = results_df[(results_df["total_return"] > BENCH_TOTAL_RETURN) & (results_df["annualized_vol"] < V1_VOL)]
    beats_return_only = results_df[results_df["total_return"] > BENCH_TOTAL_RETURN]

    print(f"총 {len(results_df)}개 조합 테스트")
    print(f"\n기준: Buy&Hold 총수익률 {BENCH_TOTAL_RETURN:.4f} 초과 AND v1 변동성 {V1_VOL:.4f} 미만 (베스트)")
    print(beats_both.to_string(index=False) if not beats_both.empty else "  -> 해당 조합 없음")

    print(f"\n기준: Buy&Hold 총수익률 {BENCH_TOTAL_RETURN:.4f} 초과 (차선, 변동성 무관)")
    print(beats_return_only.to_string(index=False) if not beats_return_only.empty else "  -> 해당 조합 없음")

    print("\n상위 10개 (총수익률 기준):")
    print(results_df.head(10).to_string(index=False))

    out_path = ROOT / "backtest" / "sweep_gradual_results.csv"
    results_df.to_csv(out_path, index=False)
    print(f"\n전체 결과 저장: {out_path}")


if __name__ == "__main__":
    main()
