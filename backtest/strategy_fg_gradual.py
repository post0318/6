"""Phase 4b: 계단식 매수 + 단일 임계값(70) 전량매도 전략 (v2, 65 트리거 혼선 정리 후 재정의).

규칙:
- 초기 편입(램프업): 시뮬레이션 첫 5거래일 동안 매일 포트폴리오의 6%씩 매수해 30%까지 채운다.
  이 구간은 FG 값과 완전히 무관하게 진행된다("30% 편입 전에는 지수 여부 무관 매수진행").
- 30% 편입이 끝난 뒤부터 매 거래일 다음 로직을 적용한다:
  - FG >= 70 이면 그날 종가로 보유 주식을 전량 매도(현금화), 매수 진행 모드 off.
  - FG < 70 이면 매수 진행 모드 on(최초든 재진입이든 동일 트리거). 매수 진행 모드가 켜져
    있는 동안 매주 수요일마다 포트폴리오 비중의 5%p를 추가로 주식에 편입(현금->주식),
    100%에 도달하면 더 이상 매수하지 않는다. FG가 다시 70을 넘으면 위 매도 규칙이 그대로
    적용되어 다시 청산되고, 이후 70 하회 시 매수가 재개되는 사이클이 반복된다.
  - 매수 진행 모드 중 FG가 20 밑으로 내려가면 그날 즉시 잔여 현금을 전부 주식으로 편입
    (전량매수, 100%). 이후에는 다음 70 돌파(매도) 전까지 그냥 보유(buy & hold)한다.
- 매수/매도는 모두 당일 종가 기준. 현금 보유 구간은 무이자(0%), 거래비용 없음.

이전 버전과 달라진 점: 매수재개(구 65)와 전량매도(구 75) 임계값을 70 하나로 통일했고,
초기 편입을 하루짜리 30% 매수 대신 5거래일 x 6% 램프업으로 바꿨고, 급락 전량매수 임계값을
25 -> 20으로 낮췄다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strategy_fg_threshold import perf_stats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MERGED_PATH = ROOT / "data" / "merged.csv"

RAMP_DAYS = 5
RAMP_DAILY_STEP = 0.06     # 5 x 6% = 30%
RESELL_LEVEL = 70.0        # 이 이상이면 전량매도 / 이 밑이면 매수 진행 모드 on
CRASH_FULL_BUY = 20.0      # 매수 진행 모드 중 이 밑이면 즉시 100%
WEEKLY_STEP = 0.05
INITIAL_CAPITAL = 100.0


def load_data() -> pd.DataFrame:
    df = pd.read_csv(MERGED_PATH, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    df = df[["date", "fg", "close"]].copy()
    # 신호-체결 1일 지연 (session 14): 전날까지 알려진 FG로 오늘 종가에 체결
    df["fg"] = df["fg"].shift(1).bfill()
    return df


def run_strategy(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    n = len(df)
    equity = np.zeros(n, dtype=float)
    weight = np.zeros(n, dtype=float)
    buying_active_arr = np.zeros(n, dtype=bool)
    trades: list[dict] = []

    cash = INITIAL_CAPITAL
    shares = 0.0
    buying_active = False

    for i in range(n):
        fg = float(df["fg"].iloc[i])
        price = float(df["close"].iloc[i])
        date = df["date"].iloc[i]
        weekday = date.weekday()  # Monday=0 ... Wednesday=2

        total_value = cash + shares * price

        if i < RAMP_DAYS:
            # 초기 램프업: 지수 값과 무관하게 매일 6%p씩 편입
            buy_value = min(cash, RAMP_DAILY_STEP * total_value)
            if buy_value > 0:
                shares += buy_value / price
                cash -= buy_value
                trades.append({
                    "date": str(date.date()), "action": "RAMP_BUY", "fg": round(fg, 2),
                    "price": round(price, 2), "pctOfPortfolio": round(buy_value / total_value, 4),
                })
        else:
            current_weight = (shares * price) / total_value if total_value > 0 else 0.0

            if current_weight > 1e-9 and fg >= RESELL_LEVEL:
                cash += shares * price
                shares = 0.0
                buying_active = False
                trades.append({"date": str(date.date()), "action": "SELL_ALL", "fg": round(fg, 2), "price": round(price, 2)})
            else:
                if fg < RESELL_LEVEL:
                    buying_active = True

                total_value = cash + shares * price
                current_weight = (shares * price) / total_value if total_value > 0 else 0.0

                if buying_active and fg < CRASH_FULL_BUY and current_weight < 1.0 - 1e-9:
                    buy_value = cash
                    shares += buy_value / price
                    cash -= buy_value
                    trades.append({
                        "date": str(date.date()), "action": "CRASH_FULL_BUY", "fg": round(fg, 2),
                        "price": round(price, 2), "pctOfPortfolio": round(1.0 - current_weight, 4),
                    })
                elif buying_active and weekday == 2 and current_weight < 1.0 - 1e-9:
                    total_value = cash + shares * price
                    buy_value = min(cash, WEEKLY_STEP * total_value)
                    if buy_value > 0:
                        shares += buy_value / price
                        cash -= buy_value
                        trades.append({
                            "date": str(date.date()), "action": "WEEKLY_BUY", "fg": round(fg, 2),
                            "price": round(price, 2), "pctOfPortfolio": round(buy_value / total_value, 4),
                        })

        total_value = cash + shares * price
        equity[i] = total_value
        weight[i] = (shares * price) / total_value if total_value > 0 else 0.0
        buying_active_arr[i] = buying_active

    out = df.copy()
    out["strategy_equity"] = equity
    out["strategy_weight"] = weight
    out["buying_active"] = buying_active_arr
    out["benchmark_equity"] = INITIAL_CAPITAL * (out["close"] / out["close"].iloc[0])
    return out, trades


def main() -> None:
    df = load_data()
    df, trades = run_strategy(df)

    strat_stats = perf_stats(df["strategy_equity"], df["date"])
    bench_stats = perf_stats(df["benchmark_equity"], df["date"])

    results = {
        "params": {
            "ramp_days": RAMP_DAYS,
            "ramp_daily_step": RAMP_DAILY_STEP,
            "resell_level": RESELL_LEVEL,
            "crash_full_buy": CRASH_FULL_BUY,
            "weekly_step": WEEKLY_STEP,
            "cash_interest": 0.0,
            "date_range": {"start": str(df["date"].min().date()), "end": str(df["date"].max().date())},
        },
        "strategy": strat_stats,
        "benchmark_buy_and_hold": bench_stats,
        "final_weight": round(float(df["strategy_weight"].iloc[-1]), 4),
        "num_trades": len(trades),
        "trade_counts": pd.Series([t["action"] for t in trades]).value_counts().to_dict(),
        "trades": trades,
    }

    out_dir = ROOT / "backtest"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results_gradual.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    df[["date", "fg", "close", "strategy_equity", "benchmark_equity", "strategy_weight", "buying_active"]].to_csv(
        out_dir / "equity_curve_gradual.csv", index=False
    )

    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
