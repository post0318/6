"""코스피200 대용 가격 데이터 수집.

Yahoo Finance에 코스피200 지수 티커(^KS200)는 히스토리가 사실상 없어(1일치만 반환),
코스피200을 그대로 추종하는 KODEX 200 ETF(069500.KS, 2011-01-03부터 데이터 존재 —
CNN 공포탐욕지수 외부 보완 데이터 시작일과 일치)를 대신 쓴다. 실제 ETF라 나중에
실매매 검증(엑셀 워크북)에도 그대로 재사용 가능하다.
"""

from __future__ import annotations

from pathlib import Path

import yfinance as yf

TICKER = "069500.KS"  # KODEX 200
START_DATE = "2011-01-01"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "kospi200.csv"


def main() -> None:
    df = yf.download(TICKER, start=START_DATE, auto_adjust=True, progress=False)
    df = df.reset_index()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df["Date"] = df["Date"].dt.date
    df = df.rename(columns={"Date": "date", "Close": "close"})

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df[["date", "close"]].to_csv(OUT_PATH, index=False)
    print(f"saved: {OUT_PATH} ({len(df)} rows, {df['date'].min()} ~ {df['date'].max()})")
    print(df.tail())


if __name__ == "__main__":
    main()
