"""2022 약세장에 '사전에' 대응할 수 있었던 규칙 시나리오 분석.

H(F/79/31)는 2021-11 고점 당시 FG 최고치가 77.2로 매도 기준 79에 못 미쳐 하락장 내내 100% 편입.
그 시점에 알 수 있던 정보(전일까지의 FG·종가)만 쓰는 위험회피(risk-off) 오버레이를 H/I 위에 얹어
  (1) 2022 하락 구간 방어력  (2) 2011~2026 전체 성과  (3) 거짓경보(risk-off 진입 횟수)
를 함께 본다. 하락장 한 번에 맞춘 규칙은 전체 표본에서 비용이 드러나야 한다.

오버레이 규칙: risk_off가 켜지면 편입비중을 cap까지 줄이고 모든 매수를 중단한다.
꺼지면 진입 직전 비중까지 즉시 되사고 H/I 원래 로직을 재개한다.
결과: backtest/scenario_2022.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
from optimize_v2 import INITIAL_CAPITAL, perf_from_equity  # noqa: E402
from structure_search_7931 import load_full  # noqa: E402

PEAK, TROUGH, RECOVERY = pd.Timestamp("2021-11-19"), pd.Timestamp("2022-12-28"), pd.Timestamp("2024-02-29")
H = dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=79, crash_level=31)


def simulate_overlay(fg, price, risk_off, cap, initial_allocation, ramp_days, buy_interval_days, buy_step,
                     resell_level, crash_level, sell_fraction=1.0, crash_guard=None,
                     crash_buy_fraction=1.0, crash_once=False, retrim=True):
    """optimize_v2.simulate와 동일한 로직 + risk_off 오버레이.
    crash_guard: True인 날에만 급락매수 허용(None이면 항상 허용).
    crash_buy_fraction: 급락매수 시 남은 현금 중 매수 비율. crash_once=True면 급락 국면(FG≥50에서 리셋)당 1회만.
    retrim: True면 risk_off 동안 가격 상승으로 비중이 cap을 넘을 때마다 다시 cap까지 매도(기존 결과),
            False면 발동 시 1회만 축소(실전용, 대시보드 후보 J — 성과 차이 무시할 수준, session 26)."""
    n = len(fg)
    cash, shares = INITIAL_CAPITAL, 0.0
    buying_active = sold_flag = off = False
    days_since, restore_w = 0, 0.0
    crash_done = cut_done = False
    ramp_daily = initial_allocation / ramp_days
    equity = np.empty(n)
    for i in range(n):
        f, p = fg[i], price[i]
        if f >= 50:
            crash_done = False
        total = cash + shares * p
        cw = shares * p / total
        if risk_off[i] and i >= ramp_days:
            if not off:
                off, restore_w, cut_done = True, cw, False
            if cw > cap and (retrim or not cut_done):
                sell = (cw - cap) * total / p
                shares -= sell
                cash += sell * p
                cut_done = True
            equity[i] = cash + shares * p
            continue
        if off:  # 해제: 진입 직전 비중까지 복원
            off = False
            if restore_w > cw:
                bv = min(cash, (restore_w - cw) * total)
                shares += bv / p
                cash -= bv
            days_since = 0
        if i < ramp_days:
            bv = min(cash, ramp_daily * total)
            shares += bv / p
            cash -= bv
        else:
            total = cash + shares * p
            cw = shares * p / total
            if cw > 1e-9 and f >= resell_level and not (sell_fraction < 1.0 and sold_flag):
                sold = shares * sell_fraction
                cash += sold * p
                shares -= sold
                buying_active, sold_flag, days_since = False, True, 0
            else:
                was_active = buying_active
                if f < resell_level:
                    buying_active, sold_flag = True, False
                if buying_active and not was_active:
                    days_since = 0
                total = cash + shares * p
                cw = shares * p / total
                guard_ok = crash_guard is None or crash_guard[i]
                if buying_active and f < crash_level and cw < 1 - 1e-9 and guard_ok and not (crash_once and crash_done):
                    bv = crash_buy_fraction * cash
                    shares += bv / p
                    cash -= bv
                    crash_done = True
                    days_since = 0
                else:
                    days_since += 1
                    if buying_active and days_since >= buy_interval_days and cw < 1 - 1e-9:
                        bv = min(cash, buy_step * (cash + shares * p))
                        shares += bv / p
                        cash -= bv
                        days_since = 0
        equity[i] = cash + shares * p
    return equity


def signals(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """모든 신호는 전일 값 기준(1일 체결지연, session 14)."""
    c, fg = df["close"], df["fg"]
    ma50, ma200 = c.rolling(50).mean(), c.rolling(200).mean()
    hi252 = c.rolling(252, min_periods=1).max()
    fg_max60 = fg.rolling(60, min_periods=1).max()
    greed_days = (fg >= 70).astype(int).rolling(60, min_periods=1).sum()

    def hysteresis(on: pd.Series, off: pd.Series) -> pd.Series:
        state, out = False, []
        for a, b in zip(on.to_numpy(), off.to_numpy()):
            state = (not b) if state else bool(a)
            out.append(state)
        return pd.Series(out, index=on.index)

    raw = {
        "추세: 종가<200일선": c < ma200,
        "추세: 종가<200일선×0.97": hysteresis(c < ma200 * 0.97, c > ma200),
        "추세: 데드크로스(50<200)": ma50 < ma200,
        "낙폭: 52주고점 -10%": hysteresis(c < hi252 * 0.90, c > ma200),
        "낙폭: 52주고점 -15%": hysteresis(c < hi252 * 0.85, c > ma200),
        "탐욕소진: 60일내 FG≥70 후 FG<40 & 200일선 아래": hysteresis((fg_max60 >= 70) & (fg < 40) & (c < ma200), c > ma200),
        "탐욕지속: 60일중 FG≥70 20일↑ 후 50일선 이탈": hysteresis((greed_days >= 20) & (c < ma50), c > ma50),
    }
    return {k: v.shift(1).fillna(False).to_numpy(dtype=bool) for k, v in raw.items()} | {
        "_above_ma200": (c > ma200).shift(1).fillna(True).to_numpy(dtype=bool)}


def episodes(mask: np.ndarray) -> int:
    return int(np.sum(mask[1:] & ~mask[:-1]) + mask[0])


def main() -> None:
    df = load_full()
    fg = df["fg"].shift(1).bfill().to_numpy()
    price, dates = df["close"].to_numpy(), df["date"]
    ip, it, ir = (int(dates[dates == d].index[0]) for d in (PEAK, TROUGH, RECOVERY))
    sig = signals(df)
    none = np.zeros(len(df), dtype=bool)
    bench = 100.0 * price / price[0]

    def row(name, cand, eq, mask=none, cap=np.nan):
        s = perf_from_equity(eq, dates)
        seg = eq[ip:it + 1]
        return {"scenario": name, "candidate": cand, "cap": cap,
                "peak_to_trough": eq[it] / eq[ip] - 1, "mdd_2022": float((seg / np.maximum.accumulate(seg) - 1).min()),
                "peak_to_recovery": eq[ir] / eq[ip] - 1, "total_return": s["total_return"], "sharpe": s["sharpe_like"],
                "mdd": s["max_drawdown"], "cagr": s["cagr"], "riskoff_episodes": episodes(mask),
                "riskoff_days_pct": mask.mean()}

    rows = [row("Buy&Hold", "-", bench)]
    for cand, sf in (("H", 1.0), ("I", 0.5)):
        rows.append(row("기준(오버레이 없음)", cand, simulate_overlay(fg, price, none, 1.0, sell_fraction=sf, **H)))
        for lvl in (65, 70, 75):
            p = dict(H, resell_level=lvl)
            rows.append(row(f"매도기준 {lvl}로 하향", cand, simulate_overlay(fg, price, none, 1.0, sell_fraction=sf, **p)))
        rows.append(row("급락매수는 200일선 위에서만", cand,
                        simulate_overlay(fg, price, none, 1.0, sell_fraction=sf, crash_guard=sig["_above_ma200"], **H)))
        for name, mask in sig.items():
            if name.startswith("_"):
                continue
            for cap in (0.0, 0.5):
                eq = simulate_overlay(fg, price, mask, cap, sell_fraction=sf, **H)
                rows.append(row(name, cand, eq, mask, cap))
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "backtest" / "scenario_2022.csv", index=False)
    print(f"저장: {len(out)}행")


if __name__ == "__main__":
    main()
