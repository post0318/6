"""analysis/explore.py의 분석 로직을 재사용해 웹 대시보드용 JSON을 생성한다.

출력: web/public/data/dashboard.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from explore import FORWARD_WINDOWS, load_merged

ROOT = Path(__file__).resolve().parent.parent
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
            "sp500": clean(row["close"]),
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
                "표본 기간(2020-07~현재)은 대부분 강한 상승장이었고 진짜 공포 국면은 "
                "2022년 약세장 정도뿐입니다. forward return 윈도우들이 서로 겹쳐(overlapping) "
                "있어 관측치가 자기상관되어 있고, 표본 내 독립적인 공포/탐욕 국면 수도 적습니다. "
                "아래 결과는 방향성 탐색 수준이며 통계적으로 유의한 결론이 아닙니다."
            ),
        },
        "horizons": [{"key": k, "ko": HORIZON_KO[k]} for k in FORWARD_WINDOWS],
        "ratingOrder": [{"key": r, "ko": RATING_KO[r]} for r in RATING_ORDER],
        "timeseries": build_timeseries(df),
        "bucketSummary": build_bucket_summary(df),
        "correlation": build_correlation(df),
        "hypothesis1": build_hypothesis1(df),
        "hypothesis2": build_hypothesis2(df),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"saved: {OUT_PATH}")
    print(f"timeseries rows: {len(payload['timeseries'])}")
    print("correlation:", payload["correlation"])
    print("bucketSummary extreme fear 1w:", payload["bucketSummary"]["extreme fear"]["byHorizon"]["1w"])


if __name__ == "__main__":
    main()
