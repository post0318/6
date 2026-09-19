"""나스닥 종합지수(^IXIC) 일별 가격 데이터를 수집해 data/nasdaq.csv 로 저장한다."""

from __future__ import annotations

from pathlib import Path

import yfinance as yf

TICKER = "^IXIC"
START_DATE = "2020-07-01"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "nasdaq.csv"


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
