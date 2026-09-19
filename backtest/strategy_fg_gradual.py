"""Phase 4b: 점진적(계단식) 매수 + 임계값 전량매도 전략.

규칙:
- 초기 편입: 시작일에 지수 값과 무관하게 포트폴리오의 30%를 주식으로 매수하고, 이 초기
  편입 자체가 매수 진행 모드(buying_active)를 켠다 — 그날 FG 값이 얼마든 상관없다.
- 매수 진행 모드가 켜져 있는 동안, 매주 수요일마다 포트폴리오 비중의 5%p를 추가로 주식에
  편입(현금->주식), 100%에 도달하면 더 이상 매수하지 않는다. FG가 65를 넘어도 이 모드는
  꺼지지 않고 유지된다.
- 전량매도: 어느 시점이든 FG가 75 이상이면 그날 종가로 보유 주식을 전량 매도하고 매수 진행
  모드를 끈다.
- 재트리거: 전량매도로 모드가 꺼진 뒤에는, FG가 65 밑으로 다시 내려가야 매수 진행 모드가
  재개된다("65 하회"는 최초 진입이 아니라 매도 이후의 재진입 트리거).
- 급락 전량매수: 매수 진행 모드 중 FG가 25 밑으로 내려가면 그날 즉시 나머지 현금을 전부
  주식으로 편입(100%).
- 매수/매도는 모두 당일 종가 기준. 현금 보유 구간은 무이자(0%), 거래비용 없음.
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

INITIAL_ALLOCATION = 0.30
BUY_TRIGGER = 65.0     # 이 밑으로 내려가면 매수 진행 모드 on
SELL_THRESHOLD = 75.0  # 이 이상이면 전량매도, 모드 off
CRASH_FULL_BUY = 25.0  # 매수 진행 모드 중 이 밑이면 즉시 100%
WEEKLY_STEP = 0.05
INITIAL_CAPITAL = 100.0


def load_data() -> pd.DataFrame:
    df = pd.read_csv(MERGED_PATH, parse_dates=["date"])
    return df[["date", "fg", "close"]].sort_values("date").reset_index(drop=True)


def run_strategy(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    n = len(df)
    equity = np.zeros(n, dtype=float)
    weight = np.zeros(n, dtype=float)  # 그날 종가 기준 실제 주식 비중(참고용)
    buying_active_arr = np.zeros(n, dtype=bool)
    trades: list[dict] = []

    cash = INITIAL_CAPITAL
    shares = 0.0
    buying_active = False
    initial_done = False

    for i in range(n):
        fg = float(df["fg"].iloc[i])
        price = float(df["close"].iloc[i])
        date = df["date"].iloc[i]
        weekday = date.weekday()  # Monday=0 ... Wednesday=2

        total_value = cash + shares * price

        if not initial_done:
            buy_value = INITIAL_ALLOCATION * total_value
            shares += buy_value / price
            cash -= buy_value
            initial_done = True
            buying_active = True  # 초기 편입 자체가 매수 트리거 발동 (그날 지수 값과 무관)
            trades.append({
                "date": str(date.date()), "action": "INITIAL_BUY", "fg": round(fg, 2),
                "price": round(price, 2), "pctOfPortfolio": INITIAL_ALLOCATION,
            })
            total_value = cash + shares * price

        current_weight = (shares * price) / total_value if total_value > 0 else 0.0

        if current_weight > 1e-9 and fg >= SELL_THRESHOLD:
            cash += shares * price
            shares = 0.0
            buying_active = False
            trades.append({"date": str(date.date()), "action": "SELL_ALL", "fg": round(fg, 2), "price": round(price, 2)})
        else:
            if fg < BUY_TRIGGER:
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
            "initial_allocation": INITIAL_ALLOCATION,
            "buy_trigger": BUY_TRIGGER,
            "sell_threshold": SELL_THRESHOLD,
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
