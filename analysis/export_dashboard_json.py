"""analysis/explore.py의 분석 로직을 재사용해 웹 대시보드용 JSON을 생성한다.

출력: web/public/data/dashboard.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from explore import FORWARD_WINDOWS, load_merged

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from strategy_fg_threshold import (  # noqa: E402
    BUY_THRESHOLD,
    SELL_THRESHOLD,
    load_data as load_backtest_data,
    perf_stats,
    run_strategy,
)
import strategy_fg_gradual  # noqa: E402
from optimize_v2 import (  # noqa: E402
    load_arrays as load_opt_arrays,
    perf_from_equity,
    simulate as simulate_opt,
    simulate_with_trades,
)

OUT_PATH = ROOT / "web" / "public" / "data" / "dashboard.json"

RATING_ORDER = ["extreme fear", "fear", "neutral", "greed", "extreme greed"]
RATING_KO = {
    "extreme fear": "극단적 공포",
    "fear": "공포",
    "neutral": "중립",
    "greed": "탐욕",
    "extreme greed": "극단적 탐욕",
}
HORIZON_KO = {"1w": "1주", "1m": "1개월", "3m": "3개월", "6m": "6개월", "12m": "12개월"}


def clean(x):
    if x is None:
        return None
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return None
        return round(float(x), 6)
    if isinstance(x, (int, np.integer)):
        return int(x)
    return x


def build_timeseries(df: pd.DataFrame) -> list[dict]:
    out = []
    for _, row in df.iterrows():
        out.append({
            "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
            "fg": clean(row["fg"]),
            "nasdaq": clean(row["close"]),
        })
    return out


def build_bucket_summary(df: pd.DataFrame) -> dict:
    cols = [f"fwd_ret_{label}" for label in FORWARD_WINDOWS]
    g = df.groupby("fg_rating")[cols].agg(["mean", "count"])

    result = {}
    for rating in RATING_ORDER:
        if rating not in g.index:
            continue
        entry = {"rating": rating, "ratingKo": RATING_KO[rating], "byHorizon": {}}
        for label in FORWARD_WINDOWS:
            mean_v = g.loc[rating, (f"fwd_ret_{label}", "mean")]
            n_v = g.loc[rating, (f"fwd_ret_{label}", "count")]
            entry["byHorizon"][label] = {"mean": clean(mean_v), "n": clean(n_v)}
        result[rating] = entry
    return result


def build_correlation(df: pd.DataFrame) -> dict:
    cols = [f"fwd_ret_{label}" for label in FORWARD_WINDOWS]
    corr = df[["fg"] + cols].corr()["fg"].drop("fg")
    return {label: clean(corr[f"fwd_ret_{label}"]) for label in FORWARD_WINDOWS}


def build_hypothesis1(df: pd.DataFrame) -> dict:
    extreme_fear = df["fg_rating"] == "extreme fear"
    rebounding = extreme_fear & (df["fg_chg_5d"] > 0)
    still_falling = extreme_fear & (df["fg_chg_5d"] <= 0)

    out = {}
    for label in FORWARD_WINDOWS:
        col = f"fwd_ret_{label}"
        out[label] = {
            "reboundingMean": clean(df.loc[rebounding, col].mean()),
            "reboundingN": clean(rebounding.sum()),
            "stillFallingMean": clean(df.loc[still_falling, col].mean()),
            "stillFallingN": clean(still_falling.sum()),
        }
    return out


def build_hypothesis2(df: pd.DataFrame, min_days: int = 10) -> dict:
    is_greed = (df["fg_rating"] == "extreme greed").astype(int)
    run_len = is_greed * (is_greed.groupby((is_greed != is_greed.shift()).cumsum()).cumcount() + 1)
    persistent = run_len >= min_days

    out = {}
    for label in FORWARD_WINDOWS:
        col = f"fwd_ret_{label}"
        out[label] = {
            "persistentMean": clean(df.loc[persistent, col].mean()),
            "persistentN": clean(persistent.sum()),
            "restMean": clean(df.loc[~persistent, col].mean()),
            "restN": clean((~persistent).sum()),
        }
    return out


def build_backtest() -> dict:
    bt_df, trades = run_strategy(load_backtest_data())
    strat_stats = perf_stats(bt_df["strategy_equity"], bt_df["date"])
    bench_stats = perf_stats(bt_df["benchmark_equity"], bt_df["date"])

    curve = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "strategy": clean(row["strategy_equity"]),
            "benchmark": clean(row["benchmark_equity"]),
            "inStock": bool(row["strategy_in_stock"]),
        }
        for _, row in bt_df.iterrows()
    ]

    return {
        "params": {
            "buyThreshold": BUY_THRESHOLD,
            "sellThreshold": SELL_THRESHOLD,
            "cashInterest": 0.0,
        },
        "strategy": strat_stats,
        "benchmark": bench_stats,
        "pctDaysInMarket": clean(bt_df["strategy_in_stock"].mean()),
        "numTrades": len(trades),
        "trades": trades,
        "equityCurve": curve,
    }


def build_backtest_gradual() -> dict:
    bt_df, trades = strategy_fg_gradual.run_strategy(strategy_fg_gradual.load_data())
    strat_stats = perf_stats(bt_df["strategy_equity"], bt_df["date"])
    bench_stats = perf_stats(bt_df["benchmark_equity"], bt_df["date"])

    curve = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "strategy": clean(row["strategy_equity"]),
            "benchmark": clean(row["benchmark_equity"]),
            "weight": clean(row["strategy_weight"]),
            "buyingActive": bool(row["buying_active"]),
        }
        for _, row in bt_df.iterrows()
    ]

    trade_counts: dict[str, int] = {}
    for t in trades:
        trade_counts[t["action"]] = trade_counts.get(t["action"], 0) + 1

    return {
        "params": {
            "rampDays": strategy_fg_gradual.RAMP_DAYS,
            "rampDailyStep": strategy_fg_gradual.RAMP_DAILY_STEP,
            "resellLevel": strategy_fg_gradual.RESELL_LEVEL,
            "crashFullBuy": strategy_fg_gradual.CRASH_FULL_BUY,
            "weeklyStep": strategy_fg_gradual.WEEKLY_STEP,
            "cashInterest": 0.0,
        },
        "strategy": strat_stats,
        "benchmark": bench_stats,
        "finalWeight": clean(bt_df["strategy_weight"].iloc[-1]),
        "numTrades": len(trades),
        "tradeCounts": trade_counts,
        "trades": trades,
        "equityCurve": curve,
    }


PEAK_DATE = "2021-11-19"
TROUGH_DATE = "2022-12-28"
RECOVERY_DATE = "2024-02-29"

# session 7/8에서 찾은 "위험조정 최적" 조합
OPT_PARAMS = dict(initial_allocation=0.50, ramp_days=1, buy_interval_days=21, buy_step=0.20, resell_level=65, crash_level=30)


def build_window_analysis() -> dict:
    fg, price, dates = load_opt_arrays()
    date_strs = dates.dt.strftime("%Y-%m-%d")
    peak_idx = int(date_strs[date_strs == PEAK_DATE].index[0])
    trough_idx = int(date_strs[date_strs == TROUGH_DATE].index[0])
    recovery_idx = int(date_strs[date_strs == RECOVERY_DATE].index[0])

    bench_eq = 100.0 * (price / price[0])
    v1_eq = pd.read_csv(ROOT / "backtest" / "equity_curve.csv")["strategy_equity"].to_numpy()
    v2_default_eq = pd.read_csv(ROOT / "backtest" / "equity_curve_gradual.csv")["strategy_equity"].to_numpy()
    v2_opt_eq = simulate_opt(fg, price, **OPT_PARAMS)

    curves = {
        "buyHold": bench_eq,
        "v1": v1_eq,
        "v2Default": v2_default_eq,
        "v2Optimal": v2_opt_eq,
    }

    def window_stats(eq: np.ndarray) -> dict:
        stats = perf_from_equity(eq, dates)
        return {
            "peakToTrough": clean((eq[trough_idx] / eq[peak_idx]) - 1),
            "peakToRecovery": clean((eq[recovery_idx] / eq[peak_idx]) - 1),
            **{k: clean(v) for k, v in stats.items()},
        }

    equity_curve = [
        {
            "date": date_strs.iloc[i],
            "buyHold": clean(bench_eq[i]),
            "v1": clean(v1_eq[i]),
            "v2Default": clean(v2_default_eq[i]),
            "v2Optimal": clean(v2_opt_eq[i]),
        }
        for i in range(len(fg))
    ]

    return {
        "window": {"peakDate": PEAK_DATE, "troughDate": TROUGH_DATE, "recoveryDate": RECOVERY_DATE},
        "optimalParams": OPT_PARAMS,
        "summary": {name: window_stats(eq) for name, eq in curves.items()},
        "equityCurve": equity_curve,
    }


SIGNAL_CANDIDATES = [
    {
        "id": "A",
        "label": "A: v2-optimal (초기 50% / 추가매수 20%, 21일)",
        "params": dict(initial_allocation=0.50, ramp_days=1, buy_interval_days=21, buy_step=0.20, resell_level=65, crash_level=30),
    },
    {
        "id": "B",
        "label": "B: 40%/10% 최고 (분할 없음, 21일)",
        "params": dict(initial_allocation=0.40, ramp_days=1, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30),
    },
    {
        "id": "C",
        "label": "C: 40%/10% 분할 최고 (2일 램프, 21일)",
        "params": dict(initial_allocation=0.40, ramp_days=2, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30),
    },
    {
        "id": "D",
        "label": "D: 40%/10%, 초기 5회 분할, 21일",
        "params": dict(initial_allocation=0.40, ramp_days=5, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30),
    },
    {
        "id": "E",
        "label": "E: 40%/10%, 초기 5회 분할, 14일",
        "params": dict(initial_allocation=0.40, ramp_days=5, buy_interval_days=14, buy_step=0.10, resell_level=65, crash_level=30),
    },
    {
        "id": "F",
        "label": "F: 40%/10%, 초기 10회 분할, 21일",
        "params": dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=65, crash_level=30),
    },
    {
        "id": "G",
        "label": "G: 40%/10%, 초기 10회 분할, 14일",
        "params": dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=14, buy_step=0.10, resell_level=65, crash_level=30),
    },
]


def rolling_summary(equity: np.ndarray, bench_equity: np.ndarray, n: int) -> dict:
    r = equity[n:] / equity[:-n] - 1
    rb = bench_equity[n:] / bench_equity[:-n] - 1
    return {
        "mean": clean(r.mean()),
        "median": clean(float(np.median(r))),
        "worst": clean(r.min()),
        "best": clean(r.max()),
        "pctNegative": clean((r < 0).mean()),
        "winRateVsBenchmark": clean((r > rb).mean()),
    }


def current_status(weight: float, buying_active: bool, trades: list[dict], params: dict) -> dict:
    last_trade = trades[-1] if trades else None
    if buying_active and weight >= 1.0 - 1e-6:
        hint = f"완전 편입(100%) 상태 — FG가 {params['resell_level']} 이상이면 전량매도"
    elif buying_active:
        hint = (
            f"매수 진행 중(현재 비중 {weight*100:.0f}%) — 다음 정기매수까지 대기, "
            f"FG≥{params['resell_level']}이면 즉시 매도, FG<{params['crash_level']}이면 즉시 전량매수"
        )
    else:
        hint = f"현금 보유 중 — FG가 {params['resell_level']} 밑으로 내려가면 매수 재개"
    return {
        "currentWeight": clean(weight),
        "buyingActive": bool(buying_active),
        "lastTrade": last_trade,
        "hint": hint,
    }


def build_signal_candidates() -> list[dict]:
    fg, price, dates = load_opt_arrays()
    bench_eq = 100.0 * (price / price[0])

    out = []
    for cand in SIGNAL_CANDIDATES:
        eq, weight, active, trades = simulate_with_trades(fg, price, dates, **cand["params"])
        stats = perf_from_equity(eq, dates)
        out.append({
            "id": cand["id"],
            "label": cand["label"],
            "params": cand["params"],
            "currentStatus": current_status(float(weight[-1]), bool(active[-1]), trades, cand["params"]),
            "summary": {
                "original": {k: clean(v) for k, v in stats.items()},
                "rolling1y": rolling_summary(eq, bench_eq, 252),
                "rolling2y": rolling_summary(eq, bench_eq, 504),
            },
            "trades": trades,
            "equityCurve": [
                {"date": str(dates.iloc[i].date()), "equity": clean(eq[i])}
                for i in range(len(fg))
            ],
        })
    return out


def build_rolling_series() -> dict:
    """롤링 1년/2년 수익률의 전체 시계열(요약 통계가 아니라 매일 값)을 반환한다 —
    대시보드에서 시간에 따른 롤링 성과 변화를 차트로 보여주기 위함."""
    fg, price, dates = load_opt_arrays()
    bench_eq = 100.0 * (price / price[0])

    curves = {"buyHold": bench_eq}
    for cand in SIGNAL_CANDIDATES:
        curves[cand["id"]] = simulate_opt(fg, price, **cand["params"])

    def rolling(eq: np.ndarray, n: int) -> np.ndarray:
        return eq[n:] / eq[:-n] - 1

    out = {}
    for horizon_label, n in [("1y", 252), ("2y", 504)]:
        rolled = {name: rolling(eq, n) for name, eq in curves.items()}
        m = len(rolled["buyHold"])
        series = []
        for i in range(m):
            row = {"date": str(dates.iloc[i + n].date())}
            for name in curves:
                row[name] = clean(rolled[name][i])
            series.append(row)
        out[horizon_label] = series
    return out


def main() -> None:
    df = load_merged()

    payload = {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "dateRange": {
                "start": df["date"].min().strftime("%Y-%m-%d"),
                "end": df["date"].max().strftime("%Y-%m-%d"),
            },
            "sampleCaveat": (
                "표본 기간(2021-01~현재)은 대부분 강한 상승장이었고 진짜 공포 국면은 "
                "2022년 약세장 정도뿐입니다. forward return 윈도우들이 서로 겹쳐(overlapping) "
                "있어 관측치가 자기상관되어 있고, 표본 내 독립적인 공포/탐욕 국면 수도 적습니다. "
                "(2020-07~2021-01 구간은 CNN 데이터의 92%가 결측 placeholder(50.0)로 확인돼 "
                "제외했습니다 — session 16 참고). 아래 결과는 방향성 탐색 수준이며 "
                "통계적으로 유의한 결론이 아닙니다."
            ),
        },
        "horizons": [{"key": k, "ko": HORIZON_KO[k]} for k in FORWARD_WINDOWS],
        "ratingOrder": [{"key": r, "ko": RATING_KO[r]} for r in RATING_ORDER],
        "timeseries": build_timeseries(df),
        "bucketSummary": build_bucket_summary(df),
        "correlation": build_correlation(df),
        "hypothesis1": build_hypothesis1(df),
        "hypothesis2": build_hypothesis2(df),
        "backtestThreshold": build_backtest(),
        "backtestGradual": build_backtest_gradual(),
        "windowAnalysis": build_window_analysis(),
        "signalCandidates": build_signal_candidates(),
        "rollingSeries": build_rolling_series(),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"saved: {OUT_PATH}")
    print(f"timeseries rows: {len(payload['timeseries'])}")
    print("correlation:", payload["correlation"])
    print("bucketSummary extreme fear 1w:", payload["bucketSummary"]["extreme fear"]["byHorizon"]["1w"])
    print("backtestThreshold strategy vs benchmark:", payload["backtestThreshold"]["strategy"], payload["backtestThreshold"]["benchmark"])
    print("backtestGradual strategy vs benchmark:", payload["backtestGradual"]["strategy"], payload["backtestGradual"]["benchmark"])
    print("windowAnalysis summary:", json.dumps(payload["windowAnalysis"]["summary"], indent=2))
    for c in payload["signalCandidates"]:
        print(f"{c['id']}: trades={len(c['trades'])} currentStatus={c['currentStatus']['hint']}")
    print("rollingSeries 1y points:", len(payload["rollingSeries"]["1y"]), "2y points:", len(payload["rollingSeries"]["2y"]))
    print("rollingSeries 1y sample:", payload["rollingSeries"]["1y"][-1])


if __name__ == "__main__":
    main()
