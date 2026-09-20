"""엑셀 매크로 검증용 기준(오라클) 엔진.

투자자 입금 1건 = 트랜치 1개(각자 시작일부터 초기 분할편입이 따로 진행). 매일 각 트랜치는
FG(전일)로 판단해 매수/매도하고, 투자자 단위로 순매매(매수-매도)를 내서 한쪽만 남긴다.
로직은 backtest/optimize_v2.simulate()와 동일하며, 그 결과와 일치하는지 test_against_backtest()로 확인한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

PARAMS = {
    "H": dict(init=0.40, ramp=10, interval=21, step=0.10, resell=79, crash=31, crash_frac=1.0, sell_frac=1.0),
    "I": dict(init=0.40, ramp=10, interval=21, step=0.10, resell=79, crash=31, crash_frac=1.0, sell_frac=0.5),
}


@dataclass
class Tranche:
    inv: str
    tid: int
    strat: str
    start: str
    cash: float
    shares: float = 0.0
    active: bool = False
    sold: bool = False
    days: int = 0
    k: int = 0
    closed: bool = False
    events: list = field(default_factory=list)


def step_tranche(t: Tranche, P: dict, f: float, p: float, integer: bool) -> list[tuple[str, float]]:
    ev: list[tuple[str, float]] = []

    def buy(value: float, kind: str) -> None:
        q = math.floor(value / p + 1e-9) if integer else value / p
        if q <= 0:
            return
        t.cash -= q * p
        t.shares += q
        ev.append((kind, q))

    total = t.cash + t.shares * p
    if t.k < P["ramp"]:
        buy(min(t.cash, P["init"] / P["ramp"] * total), "RAMP_BUY")
    else:
        cw = t.shares * p / total if total > 0 else 0.0
        if cw > 1e-9 and f >= P["resell"] and not (P["sell_frac"] < 1.0 and t.sold):
            if P["sell_frac"] >= 1.0:
                q = t.shares
            else:
                q = math.floor(t.shares * P["sell_frac"] + 1e-9) if integer else t.shares * P["sell_frac"]
            t.cash += q * p
            t.shares -= q
            t.active, t.sold, t.days = False, True, 0
            if q > 0:
                ev.append(("SELL", -q))
        else:
            was = t.active
            if f < P["resell"]:
                t.active, t.sold = True, False
            if t.active and not was:
                t.days = 0
            total = t.cash + t.shares * p
            cw = t.shares * p / total if total > 0 else 0.0
            if t.active and P["crash_frac"] > 0 and f < P["crash"] and cw < 1.0 - 1e-9:
                buy(P["crash_frac"] * t.cash, "CRASH_BUY")
                t.days = 0
            else:
                t.days += 1
                if t.active and t.days >= P["interval"] and cw < 1.0 - 1e-9:
                    bv = min(t.cash, P["step"] * total)
                    if bv > 0:
                        buy(bv, "WEEKLY_BUY")
                    t.days = 0
    t.k += 1
    return ev


def withdraw(tranches: list[Tranche], amount: float, p: float, integer: bool) -> list[tuple[Tranche, float]]:
    """출금: 현금부터 비례 차감, 부족분은 보유수량을 비례 매도(정수 모드는 올림). 반환: (트랜치, 매도수량).
    매도대금이 부족분을 넘는 부분(올림 때문)은 트랜치 현금으로 남긴다."""
    act = [t for t in tranches if not t.closed]
    sells: list[tuple[Tranche, float]] = []
    cash_total = sum(t.cash for t in act)
    pay_cash = min(amount, cash_total)
    if cash_total > 0:
        for t in act:
            t.cash -= pay_cash * t.cash / cash_total
    short = amount - pay_cash
    if short > 1e-9:
        val = sum(t.shares * p for t in act)
        q_ratio = min(1.0, short / val) if val > 0 else 0.0
        for t in act:
            q = t.shares * q_ratio
            if integer:
                q = min(t.shares, math.ceil(q - 1e-9))
            if q > 0:
                t.shares -= q
                t.cash += q * p
                sells.append((t, q))
        tot = sum(q * p for _, q in sells)
        pay = min(short, tot)
        for t, q in sells:
            t.cash -= pay * (q * p) / tot
    for t in act:
        if t.shares <= 1e-12 and t.cash <= 1e-9:
            t.closed = True
    return sells


def replay(market: list[tuple[str, float, float]], flows: list[tuple[str, str, float, str]], integer: bool = False,
           basis: str = "same", stop_index: int | None = None, start_index: int = 0):
    """market: [(date, fg, close)], flows: [(inv, date, amount, strat)] (입금 +, 출금 -).
    basis: 'same' = 당일 종가로 산정(백테스트 재현용), 'prev' = 전일 종가로 추정(실운영).
    반환: tranches, day_orders[{date: {inv: (buy_qty, sell_qty)}}], events(list)"""
    tranches: list[Tranche] = []
    orders: dict[str, dict[str, list[float]]] = {}
    events: list[tuple] = []
    by_date: dict[str, list] = {}
    for fl in flows:
        by_date.setdefault(fl[1], []).append(fl)
    n = len(market) if stop_index is None else stop_index
    for j in range(start_index, n):
        d, fg, close = market[j]
        f = market[j - 1][1] if j > 0 else market[0][1]
        p = close if (basis == "same" or j == 0) else market[j - 1][2]
        day: dict[str, list[float]] = {}

        def add(inv: str, buy: float = 0.0, sell: float = 0.0) -> None:
            r = day.setdefault(inv, [0.0, 0.0])
            r[0] += buy
            r[1] += sell

        for inv, _, amt, strat in by_date.get(d, []):
            if amt > 0:
                tid = sum(1 for t in tranches if t.inv == inv) + 1
                tranches.append(Tranche(inv, tid, strat, d, amt))
            elif amt < 0:
                mine = [t for t in tranches if t.inv == inv and not t.closed]
                for t, q in withdraw(mine, -amt, p, integer):
                    events.append((d, inv, t.tid, "WD_SELL", -q))
                    add(inv, sell=q)
        for t in tranches:
            if t.closed:
                continue
            for kind, q in step_tranche(t, PARAMS[t.strat], f, p, integer):
                events.append((d, t.inv, t.tid, kind, q))
                add(t.inv, buy=q if q > 0 else 0.0, sell=-q if q < 0 else 0.0)
        for inv, (b, s) in day.items():
            net = b - s
            orders.setdefault(d, {})[inv] = (max(net, 0.0), max(-net, 0.0))
    return tranches, orders, events


def test_against_backtest() -> None:
    import sys
    from pathlib import Path

    import numpy as np

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "backtest"))
    from optimize_v2 import load_arrays, simulate

    fg_lag, price, dates = load_arrays()
    # load_arrays는 FG를 이미 하루 지연시켜 반환한다. 엔진은 원본 FG를 받아 스스로 지연시키므로
    # 원본 FG = 지연값을 한 칸 앞당긴 값과 동일하게 재구성한다.
    fg_raw = np.append(fg_lag[1:], fg_lag[-1])
    market = [(str(d.date()), float(f), float(c)) for d, f, c in zip(dates, fg_raw, price)]
    base = dict(initial_allocation=0.40, ramp_days=10, buy_interval_days=21, buy_step=0.10, resell_level=79, crash_level=31)
    for strat, sf in [("H", 1.0), ("I", 0.5)]:
        eq = simulate(fg_lag, price, sell_fraction=sf, **base)
        tr, _, _ = replay(market, [("A", market[0][0], 100.0, strat)], integer=False, basis="same")
        # 일별 평가를 재현하려면 상태를 매일 저장해야 하므로 마지막 날 평가액만 비교
        t = tr[0]
        final = t.cash + t.shares * market[-1][2]
        print(strat, "backtest final", round(float(eq[-1]), 6), "engine final", round(final, 6),
              "OK" if abs(final - eq[-1]) < 1e-6 else "MISMATCH")


if __name__ == "__main__":
    test_against_backtest()
