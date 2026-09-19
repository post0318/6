"""1차 스윕(resell/crash 임계값만)에서 Buy&Hold를 이기는 조합을 못 찾아서, v2의 나머지
파라미터(램프업 일수/속도, 주간 매수 속도)까지 함께 넓혀 정말로 이길 수 있는 조합이
존재하는지 확인한다."""

from __future__ import annotations

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

RESELL_LEVELS = [75, 80, 85, 90, 95, 99]
CRASH_LEVELS = [15, 20, 25, 30]
RAMP_DAYS_OPTS = [1, 5]
WEEKLY_STEP_OPTS = [0.05, 0.10, 0.15, 0.20]


def run_one(resell_level, crash_level, ramp_days, weekly_step, df) -> dict:
    sg.RESELL_LEVEL = resell_level
    sg.CRASH_FULL_BUY = crash_level
    sg.RAMP_DAYS = ramp_days
    sg.RAMP_DAILY_STEP = 0.30 / ramp_days
    sg.WEEKLY_STEP = weekly_step
    bt_df, trades = sg.run_strategy(df.copy())
    strat_stats = perf_stats(bt_df["strategy_equity"], bt_df["date"])
    return {
        "resell_level": resell_level,
        "crash_level": crash_level,
        "ramp_days": ramp_days,
        "weekly_step": weekly_step,
        "num_trades": len(trades),
        **strat_stats,
    }


def main() -> None:
    df = sg.load_data()
    results = []
    for resell_level, crash_level, ramp_days, weekly_step in product(
        RESELL_LEVELS, CRASH_LEVELS, RAMP_DAYS_OPTS, WEEKLY_STEP_OPTS
    ):
        if crash_level >= resell_level:
            continue
        results.append(run_one(resell_level, crash_level, ramp_days, weekly_step, df))

    results_df = pd.DataFrame(results).sort_values("total_return", ascending=False)
    print(f"총 {len(results_df)}개 조합 테스트\n")

    beats_both = results_df[(results_df["total_return"] > BENCH_TOTAL_RETURN) & (results_df["annualized_vol"] < V1_VOL)]
    beats_return_only = results_df[results_df["total_return"] > BENCH_TOTAL_RETURN]
    beats_bench_return = results_df[results_df["total_return"] > BENCH_TOTAL_RETURN * 0.999]

    print("베스트(수익률>BnH AND 변동성<v1):")
    print(beats_both.to_string(index=False) if not beats_both.empty else "  -> 없음")
    print("\n차선(수익률>BnH, 변동성 무관):")
    print(beats_return_only.to_string(index=False) if not beats_return_only.empty else "  -> 없음")

    print("\n상위 15개 (총수익률 기준):")
    print(results_df.head(15).to_string(index=False))

    out_path = ROOT / "backtest" / "sweep_gradual_v2_results.csv"
    results_df.to_csv(out_path, index=False)
    print(f"\n전체 결과 저장: {out_path}")


if __name__ == "__main__":
    main()
