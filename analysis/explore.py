"""Phase 2: 탐색적 분석.

Fear & Greed 지수 구간/변화와 나스닥 종합지수 이후 수익률의 관계를 살펴본다.
결과는 notes/session1_findings.md 에 요약해 기록한다. (session 9부터 벤치마크를
S&P 500에서 나스닥 종합지수(^IXIC)로 변경 — notes/session9_nasdaq.md 참고)

Session 16: 2020-07-16 ~ 2021-01-21 구간은 CNN graphdata 응답의 92%(131일 중 121일)가
정확히 50.0(neutral) placeholder였음이 확인됨 — 실제 계산된 값이 아니라 결측치를
채운 더미값으로 보인다(2021-01-22부터는 이런 정확히-50.0 패턴이 전혀 나타나지 않음).
이 구간을 신뢰할 수 없어 CLEAN_START_DATE 이전 데이터는 전부 제외한다. 자세한 내용은
notes/session16_data_quality.md 참고.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FG_PATH = ROOT / "data" / "fear_greed.csv"
INDEX_PATH = ROOT / "data" / "nasdaq.csv"

FORWARD_WINDOWS = {"1w": 5, "1m": 21, "3m": 63, "6m": 126, "12m": 252}

# 2020-07-16 ~ 2021-01-21 구간은 92%가 placeholder(정확히 50.0)라 신뢰할 수 없음(session 16).
CLEAN_START_DATE = "2021-01-22"


def load_merged() -> pd.DataFrame:
    fg = pd.read_csv(FG_PATH, parse_dates=["date"])
    idx = pd.read_csv(INDEX_PATH, parse_dates=["date"])

    df = pd.merge(
        fg[["date", "fear_and_greed_historical", "fear_and_greed_historical_rating"]],
        idx[["date", "close"]],
        on="date",
        how="inner",
    ).sort_values("date").reset_index(drop=True)
    df = df.rename(columns={
        "fear_and_greed_historical": "fg",
        "fear_and_greed_historical_rating": "fg_rating",
    })
    df = df[df["date"] >= CLEAN_START_DATE].reset_index(drop=True)

    # 미래 수익률 (forward return)
    for label, n in FORWARD_WINDOWS.items():
        df[f"fwd_ret_{label}"] = df["close"].shift(-n) / df["close"] - 1

    # 5일 전 대비 지수 변화 (반등/하락 모멘텀)
    df["fg_chg_5d"] = df["fg"] - df["fg"].shift(5)
    return df


def bucket_summary(df: pd.DataFrame) -> pd.DataFrame:
    """FG 등급(rating)별 이후 수익률 평균/중앙값."""
    cols = [f"fwd_ret_{label}" for label in FORWARD_WINDOWS]
    g = df.groupby("fg_rating")[cols].agg(["mean", "median", "count"])
    return g


def correlation_summary(df: pd.DataFrame) -> pd.Series:
    cols = [f"fwd_ret_{label}" for label in FORWARD_WINDOWS]
    return df[["fg"] + cols].corr()["fg"].drop("fg")


def rebound_vs_persistent_fear(df: pd.DataFrame) -> dict:
    """가설1: 극단적 공포에서 '반등 중'인 경우 vs '계속 하락 중'인 경우 이후 수익률 비교."""
    extreme_fear = df["fg_rating"] == "extreme fear"
    rebounding = extreme_fear & (df["fg_chg_5d"] > 0)
    still_falling = extreme_fear & (df["fg_chg_5d"] <= 0)

    out = {}
    for label in FORWARD_WINDOWS:
        col = f"fwd_ret_{label}"
        out[label] = {
            "rebounding_mean": df.loc[rebounding, col].mean(),
            "rebounding_n": int(rebounding.sum()),
            "still_falling_mean": df.loc[still_falling, col].mean(),
            "still_falling_n": int(still_falling.sum()),
        }
    return out


def persistent_greed(df: pd.DataFrame, min_days: int = 10) -> dict:
    """가설2: 'extreme greed'가 min_days 이상 연속될 때 이후 수익률."""
    is_greed = (df["fg_rating"] == "extreme greed").astype(int)
    run_len = is_greed * (is_greed.groupby((is_greed != is_greed.shift()).cumsum()).cumcount() + 1)
    persistent = run_len >= min_days

    out = {}
    for label in FORWARD_WINDOWS:
        col = f"fwd_ret_{label}"
        out[label] = {
            "persistent_greed_mean": df.loc[persistent, col].mean(),
            "persistent_greed_n": int(persistent.sum()),
            "rest_mean": df.loc[~persistent, col].mean(),
        }
    return out


def main() -> None:
    df = load_merged()
    df.to_csv(ROOT / "data" / "merged.csv", index=False)

    print("=== FG rating별 이후 수익률 요약 ===")
    print(bucket_summary(df))

    print("\n=== FG 수준과 이후 수익률의 상관계수 ===")
    print(correlation_summary(df))

    print("\n=== 가설1: 극단적 공포 - 반등 중 vs 계속 하락 중 ===")
    for label, stats in rebound_vs_persistent_fear(df).items():
        print(label, stats)

    print("\n=== 가설2: extreme greed 10일 이상 지속 후 수익률 ===")
    for label, stats in persistent_greed(df).items():
        print(label, stats)


if __name__ == "__main__":
    main()
