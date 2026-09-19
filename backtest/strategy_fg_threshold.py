"""Phase 4: 규칙 기반 백테스트.

전략: 공포탐욕지수가 20 이하로 내려가면 전량 매수, 70 이상으로 올라가면 전량 매도.
매도 후 보유하는 현금은 무이자(0%)로 가정한다. 거래비용/슬리피지는 반영하지 않는다.

결과를 buy & hold(동일기간 지수 매수 후 보유)와 비교해 backtest/results.json,
backtest/equity_curve.csv 로 저장한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MERGED_PATH = ROOT / "data" / "merged.csv"

BUY_THRESHOLD = 20.0
SELL_THRESHOLD = 70.0
INITIAL_CAPITAL = 100.0  # 지수화(=100)해서 비교


def load_data() -> pd.DataFrame:
    df = pd.read_csv(MERGED_PATH, parse_dates=["date"])
    return df[["date", "fg", "close"]].sort_values("date").reset_index(drop=True)


def run_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """공포탐욕지수 임계값 전략을 시뮬레이션하고 일별 자산가치를 반환한다."""
    n = len(df)
    in_stock = np.zeros(n, dtype=bool)
    equity = np.zeros(n, dtype=float)
    trades = []

    cash = INITIAL_CAPITAL
    shares = 0.0
    holding = False

    for i in range(n):
        fg = df["fg"].iloc[i]
        price = df["close"].iloc[i]
        date = df["date"].iloc[i]

        if not holding and fg <= BUY_THRESHOLD:
            shares = cash / price
            cash = 0.0
            holding = True
            trades.append({"date": str(date.date()), "action": "BUY", "fg": round(float(fg), 2), "price": round(float(price), 2)})
        elif holding and fg >= SELL_THRESHOLD:
            cash = shares * price
            shares = 0.0
            holding = False
            trades.append({"date": str(date.date()), "action": "SELL", "fg": round(float(fg), 2), "price": round(float(price), 2)})

        in_stock[i] = holding
        equity[i] = cash + shares * price

    df = df.copy()
    df["strategy_equity"] = equity
    df["strategy_in_stock"] = in_stock
    df["benchmark_equity"] = INITIAL_CAPITAL * (df["close"] / df["close"].iloc[0])
    return df, trades


def perf_stats(equity: pd.Series, dates: pd.Series) -> dict:
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = (dates.iloc[-1] - dates.iloc[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else float("nan")
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    max_drawdown = drawdown.min()
    daily_ret = equity.pct_change().dropna()
    ann_vol = daily_ret.std() * (252 ** 0.5)
    sharpe = (daily_ret.mean() * 252) / ann_vol if ann_vol > 0 else float("nan")
    return {
        "total_return": round(float(total_return), 4),
        "cagr": round(float(cagr), 4),
        "max_drawdown": round(float(max_drawdown), 4),
        "annualized_vol": round(float(ann_vol), 4),
        "sharpe_like": round(float(sharpe), 3),
    }


def main() -> None:
    df = load_data()
    df, trades = run_strategy(df)

    strat_stats = perf_stats(df["strategy_equity"], df["date"])
    bench_stats = perf_stats(df["benchmark_equity"], df["date"])

    pct_days_in_market = float(df["strategy_in_stock"].mean())

    results = {
        "params": {
            "buy_threshold": BUY_THRESHOLD,
            "sell_threshold": SELL_THRESHOLD,
            "initial_capital": INITIAL_CAPITAL,
            "cash_interest": 0.0,
            "date_range": {"start": str(df["date"].min().date()), "end": str(df["date"].max().date())},
        },
        "strategy": strat_stats,
        "benchmark_buy_and_hold": bench_stats,
        "pct_days_in_market": round(pct_days_in_market, 4),
        "num_trades": len(trades),
        "trades": trades,
    }

    out_dir = ROOT / "backtest"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    df[["date", "fg", "close", "strategy_equity", "benchmark_equity", "strategy_in_stock"]].to_csv(
        out_dir / "equity_curve.csv", index=False
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
