"""CNN Fear & Greed Index 과거 데이터를 수집해 data/fear_greed.csv 로 저장한다.

CNN의 비공식 그래프 데이터 엔드포인트를 사용한다. 이 엔드포인트는 문서화되어
있지 않으므로 CNN 측 변경으로 언제든 깨질 수 있다.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import requests

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start}"
HEADERS = {
    # CNN이 기본 User-Agent(예: python-requests)를 차단하므로 브라우저처럼 위장하고,
    # Referer가 없으면 start-date 파라미터를 준 요청이 500을 반환한다.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://edition.cnn.com/markets/fear-and-greed",
}

# CNN 공포탐욕지수 자체는 2011년부터 존재하지만, graphdata 엔드포인트는 조회 시점
# 기준으로 약 6년치 lookback만 허용한다(2020-06 시작 요청은 500, 2020-07-15는 200으로
# 2026-09-19 시점에 확인). 그 이전보다 앞선 날짜를 요청하면 500 Internal Server Error가
# 난다. 다음 세션에서 재확인해 더 당길 수 있는지 다시 탐색해볼 것.
START_DATE = "2020-07-16"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "fear_greed.csv"


def fetch(start: str = START_DATE) -> pd.DataFrame:
    resp = requests.get(URL.format(start=start), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    frames = []
    for key, series in payload.items():
        # 각 시리즈는 {"data": [{"x": ms_timestamp, "y": value, "rating": str}, ...]} 형태.
        # 단, "fear_and_greed"(현재값)는 data 배열이 아닌 단일 스냅샷 dict라 건너뛴다.
        if not isinstance(series, dict) or "data" not in series:
            continue
        series_data = series["data"]
        if not series_data or not isinstance(series_data[0], dict) or "x" not in series_data[0]:
            continue
        df = pd.DataFrame(series_data)
        df["date"] = pd.to_datetime(df["x"], unit="ms").dt.date
        # 최근 며칠은 하루 안에 장중 업데이트가 여러 번 찍혀 같은 날짜에 여러 타임스탬프가
        # 존재한다. 날짜별 마지막(가장 최신) 값만 남겨 merge 시 중복 행이 생기지 않게 한다.
        df = df.sort_values("x").drop_duplicates(subset="date", keep="last")
        df = df.rename(columns={"y": key})
        keep_cols = ["date", key]
        if "rating" in df.columns:
            df = df.rename(columns={"rating": f"{key}_rating"})
            keep_cols.append(f"{key}_rating")
        frames.append(df[keep_cols])

    if not frames:
        raise RuntimeError("CNN 응답에서 시계열 데이터를 찾지 못했습니다: " + json.dumps(payload)[:500])

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on="date", how="outer")

    merged = merged.sort_values("date").reset_index(drop=True)
    return merged


def main() -> None:
    df = fetch()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"저장 완료: {OUT_PATH} ({len(df)} rows, {df['date'].min()} ~ {df['date'].max()})")
    print(df.tail())


if __name__ == "__main__":
    main()
