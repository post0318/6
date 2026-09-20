"""FG_Trading_H_I.xlsm 검증: 다중 투자자 시나리오를 엑셀 매크로로 일별 실행하고 reference_engine(전일종가 기준)과 대조한다.

확인 항목: (1) 일별 주문 수량 일치 (2) 매수/매도 동시 발생 없음 (3) 최종 STATE(현금/수량) 일치
(4) LOG 매매 이벤트 일치 (5) 중복 실행·날짜 가드 (6) ApplyFills 보정 산식 (7) 저장/재열기 후 연속 실행.
"""

from __future__ import annotations

import math
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(HERE))
from optimize_v2 import load_arrays  # noqa: E402
from reference_engine import replay  # noqa: E402

XLSM = HERE / "FG_Trading_H_I.xlsm"
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "_verify_tmp"
EPOCH = datetime(1899, 12, 30)
TRADE_KINDS = {"RAMP_BUY", "WEEKLY_BUY", "CRASH_BUY", "SELL", "WD_SELL"}


def serial(d: str) -> float:
    return float((datetime.strptime(d, "%Y-%m-%d") - EPOCH).days)


def to_date(v: float) -> str:
    return (EPOCH + timedelta(days=int(round(v)))).strftime("%Y-%m-%d")


def load_market(n: int = 800):
    fg_lag, price, dates = load_arrays()
    fg_raw = np.append(fg_lag[1:], fg_lag[-1])
    m = [(str(d.date()), float(f), float(c)) for d, f, c in zip(dates, fg_raw, price)]
    return m[-n:]


def scenario(m):
    d = [x[0] for x in m]
    return [
        ("A", d[1], 1e8, "H"), ("B", d[1], 5e7, "I"), ("C", d[15], 2e7, "H"), ("A", d[40], 3e7, "H"),
        ("F", d[60], 4e7, "H"), ("F", d[60], -1e7, "H"), ("B", d[90], -1.5e7, "I"), ("D", d[120], 1e6, "I"),
        ("C", d[200], -5e6, "H"), ("E", d[250], 8e7, "I"), ("A", d[300], -6e7, "H"), ("E", d[310], 2e7, "H"),
        ("B", d[350], 2e7, "I"), ("D", d[450], -5e6, "I"), ("G", d[500], 3e7, "H"), ("A", d[600], 1e7, "I"),
        ("C", d[650], -3e7, "H"), ("G", d[700], -1e6, "H"),
    ]


def run_mode(xl, mode: str, m, flows, path: Path):
    shutil.copy(XLSM, path)
    wb = xl.Workbooks.Open(str(path))
    st = wb.Worksheets("Settings")
    inv_ws = wb.Worksheets("INVESTOR")
    mk_ws = wb.Worksheets("MARKET")

    def opt(key, val=None):
        for r in range(2, 20):
            if st.Cells(r, 10).Value2 == key:
                if val is not None:
                    st.Cells(r, 12).Value2 = val
                return st.Cells(r, 12).Value2
        raise KeyError(key)

    opt("QtyMode", mode)
    opt("Silent", "Y")
    by_date: dict[str, list] = {}
    for f in flows:
        by_date.setdefault(f[1], []).append(f)

    def put_market(j):
        mk_ws.Cells(j + 2, 1).Value2 = serial(m[j][0])
        mk_ws.Cells(j + 2, 2).Value2 = m[j][1]
        mk_ws.Cells(j + 2, 3).Value2 = m[j][2]

    put_market(0)
    irow = 2
    msgs = []
    half = len(m) // 2
    for j in range(1, len(m)):
        for inv, d, amt, strat in by_date.get(m[j][0], []):
            inv_ws.Cells(irow, 1).Value2 = inv
            inv_ws.Cells(irow, 2).Value2 = serial(d)
            inv_ws.Cells(irow, 3).Value2 = amt
            inv_ws.Cells(irow, 4).Value2 = strat
            irow += 1
        opt("OrderDate", serial(m[j][0]))
        try:
            xl.Run("RunDay")
        except Exception as e:
            print("RunDay failed at j=", j, m[j][0], e.args)
            raise
        msgs.append(opt("LastMessage"))
        put_market(j)
        if j == half:  # 저장 후 재열기: 상태가 시트에만 있어도 이어지는지
            wb.Save()
            wb.Close(False)
            wb = xl.Workbooks.Open(str(path))
            st, inv_ws, mk_ws = wb.Worksheets("Settings"), wb.Worksheets("INVESTOR"), wb.Worksheets("MARKET")
    return wb, opt, msgs


def read_sheet(ws, ncol):
    last = ws.Cells(ws.Rows.Count, 1).End(-4162).Row
    if last < 2:
        return []
    return [list(r) for r in ws.Range(ws.Cells(2, 1), ws.Cells(last, ncol)).Value2]


def close(a, b, tol=1e-6):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=tol)


def edge_tests(xl, m) -> list[str]:
    """과거일자 행 처리, 미래일자 대기, 오류행, INT 소액 건너뜀."""
    fails: list[str] = []
    path = SCRATCH / "edge.xlsm"
    shutil.copy(XLSM, path)
    wb = xl.Workbooks.Open(str(path))
    st, iv, mk, od, ss = (wb.Worksheets(n) for n in ("Settings", "INVESTOR", "MARKET", "ORDERS", "STATE"))

    def opt(key, val=None):
        for r in range(2, 20):
            if st.Cells(r, 10).Value2 == key:
                if val is not None:
                    st.Cells(r, 12).Value2 = val
                return st.Cells(r, 12).Value2
        raise KeyError(key)

    opt("Silent", "Y")
    opt("QtyMode", "FRAC")
    mk.Cells(2, 1).Value2, mk.Cells(2, 2).Value2, mk.Cells(2, 3).Value2 = serial(m[0][0]), m[0][1], m[0][2]
    d1 = serial(m[1][0])
    rows = [("P1", d1 - 30, 1e7, "H"), ("P2", d1, 5e6, "I"), ("F1", d1 + 5, 3e6, "H"), ("E1", d1, 1e6, "X"), ("E2", d1, "abc", "H")]
    for i, (a, b, c, d) in enumerate(rows, 2):
        iv.Cells(i, 1).Value2, iv.Cells(i, 2).Value2, iv.Cells(i, 3).Value2, iv.Cells(i, 4).Value2 = a, b, c, d
    opt("OrderDate", d1)
    xl.Run("RunDay")
    status = [iv.Cells(i, 5).Value2 for i in range(2, 7)]
    if status != ["DONE", "DONE", None, "ERR:strategy", "ERR:amount"]:
        fails.append(f"edge status {status}")
    o = read_sheet(od, 12)
    if sorted(r[1] for r in o) != ["P1", "P2"]:
        fails.append(f"edge orders {[r[1] for r in o]}")
    if len(read_sheet(ss, 22)) != 2:
        fails.append("edge tranche count")
    # INT 소액: 1주 가격보다 작은 입금 -> 주문 0행, 메시지에 건너뜀 안내
    opt("QtyMode", "INT")
    iv.Cells(8, 1).Value2, iv.Cells(8, 2).Value2, iv.Cells(8, 3).Value2, iv.Cells(8, 4).Value2 = "S1", serial(m[2][0]), 1000.0, "H"
    mk.Cells(3, 1).Value2, mk.Cells(3, 2).Value2, mk.Cells(3, 3).Value2 = serial(m[1][0]), m[1][1], m[1][2]
    opt("OrderDate", serial(m[2][0]))
    n0 = len(read_sheet(od, 12))
    xl.Run("RunDay")
    msg_orders = [r for r in read_sheet(od, 12)[n0:] if r[1] == "S1"]
    if msg_orders:
        fails.append("tiny INT deposit should not create an order")
    wb.Close(False)
    return fails


def import_test(xl, m, flows, mode: str, j: int) -> list[str]:
    """기존 투자자 일괄 등록: j일 시점의 상태를 IMPORT로 넣고 이어서 실행 -> 끝까지 기준 엔진과 동일해야 한다.
    MARKET에는 직전 3행만 넣어 과거 데이터 없이도 동작함을 함께 확인한다."""
    fails: list[str] = []
    integer = mode == "INT"
    path = SCRATCH / f"imp_{mode}_{j}.xlsm"
    shutil.copy(XLSM, path)
    wb = xl.Workbooks.Open(str(path))
    st, iv, mk, od, ss, im = (wb.Worksheets(n) for n in ("Settings", "INVESTOR", "MARKET", "ORDERS", "STATE", "IMPORT"))

    def opt(key, val=None):
        for r in range(2, 20):
            if st.Cells(r, 10).Value2 == key:
                if val is not None:
                    st.Cells(r, 12).Value2 = val
                return st.Cells(r, 12).Value2
        raise KeyError(key)

    opt("Silent", "Y")
    opt("QtyMode", mode)
    tr_full, ref_orders, _ = replay(m, flows, integer=integer, basis="prev", start_index=1)
    tr_part, _, _ = replay(m, flows, integer=integer, basis="prev", start_index=1, stop_index=j)
    mrow = 2
    for jj in range(j - 3, j):
        mk.Cells(mrow, 1).Value2, mk.Cells(mrow, 2).Value2, mk.Cells(mrow, 3).Value2 = serial(m[jj][0]), m[jj][1], m[jj][2]
        mrow += 1
    row = 2
    for t in tr_part:
        if t.closed:
            continue
        vals = (t.inv, t.strat, serial(t.start), t.cash, t.shares, t.k, t.days, "Y" if t.active else "N", "Y" if t.sold else "N")
        for c, v in enumerate(vals, 1):
            im.Cells(row, c).Value2 = v
        row += 1
    n_imp = row - 2
    xl.Run("ImportExisting")
    if str(opt("LastMessage")) != f"Imported {n_imp}, errors 0":
        fails.append(f"import message: {opt('LastMessage')}")
    by_date: dict[str, list] = {}
    for f in flows:
        by_date.setdefault(f[1], []).append(f)
    irow = 2
    for jj in range(j, len(m)):
        for inv, d, amt, strat in by_date.get(m[jj][0], []):
            for c, v in enumerate((inv, serial(d), amt, strat), 1):
                iv.Cells(irow, c).Value2 = v
            irow += 1
        opt("OrderDate", serial(m[jj][0]))
        xl.Run("RunDay")
        mk.Cells(mrow, 1).Value2, mk.Cells(mrow, 2).Value2, mk.Cells(mrow, 3).Value2 = serial(m[jj][0]), m[jj][1], m[jj][2]
        mrow += 1
    xl_orders: dict[str, dict[str, tuple[float, float]]] = {}
    for r in read_sheet(od, 7):
        xl_orders.setdefault(to_date(r[0]), {})[r[1]] = (float(r[2]), float(r[3]))
    ref_tail = {d: v for d, v in ref_orders.items() if d >= m[j][0]}
    for d in sorted(set(xl_orders) | set(ref_tail)):
        a, b = xl_orders.get(d, {}), ref_tail.get(d, {})
        if set(a) != set(b) or any(not (close(a[k][0], b[k][0]) and close(a[k][1], b[k][1])) for k in a):
            fails.append(f"orders differ {d}: xl={a} ref={b}")
            break
    ref_by_key = {(t.inv, t.start, t.strat): t for t in tr_full if not t.closed}
    xl_by_key = {}
    for row in read_sheet(ss, 13):
        if int(row[10]) == 0:
            xl_by_key[(row[0], to_date(row[3]), row[2])] = row
    if set(ref_by_key) != set(xl_by_key):
        fails.append(f"open tranche sets differ: only_ref={set(ref_by_key) - set(xl_by_key)} only_xl={set(xl_by_key) - set(ref_by_key)}")
    for key, t in ref_by_key.items():
        row = xl_by_key.get(key)
        if row and not (close(row[4], t.cash, 1e-4) and close(row[5], t.shares)):
            fails.append(f"final state differs {key}: xl cash={row[4]} sh={row[5]} ref cash={t.cash} sh={t.shares}")
    # 오류행 처리: 잘못된 전략/음수 보유수량은 ERR로 표시되고 등록되지 않는다
    im.Cells(n_imp + 3, 1).Value2, im.Cells(n_imp + 3, 2).Value2, im.Cells(n_imp + 3, 3).Value2, im.Cells(n_imp + 3, 4).Value2, im.Cells(n_imp + 3, 5).Value2 = "Z1", "Q", serial(m[j][0]), 100, 1
    im.Cells(n_imp + 4, 1).Value2, im.Cells(n_imp + 4, 2).Value2, im.Cells(n_imp + 4, 3).Value2, im.Cells(n_imp + 4, 4).Value2, im.Cells(n_imp + 4, 5).Value2 = "Z2", "H", serial(m[j][0]), 100, -5
    n_before = len(read_sheet(ss, 13))
    xl.Run("ImportExisting")
    if len(read_sheet(ss, 13)) != n_before or [im.Cells(n_imp + 3, 10).Value2, im.Cells(n_imp + 4, 10).Value2] != ["ERR:strategy", "ERR:amount"]:
        fails.append("import error rows not flagged")
    wb.Close(False)
    return fails


def main() -> int:
    import win32com.client as wc

    SCRATCH.mkdir(parents=True, exist_ok=True)
    m = load_market()
    flows = scenario(m)
    xl = wc.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AutomationSecurity = 1
    ok_all = True
    try:
        for mode in ("FRAC", "INT"):
            integer = mode == "INT"
            tr, ref_orders, ref_events = replay(m, flows, integer=integer, basis="prev", start_index=1)
            wb, opt, msgs = run_mode(xl, mode, m, flows, SCRATCH / f"t_{mode}.xlsm")
            fails: list[str] = []
            errs = sorted({str(x) for x in msgs if str(x).startswith(("ERROR", "Set Settings", "OrderDate must", "Last MARKET", "MARKET is", "Invalid"))})
            if errs:
                fails.append(f"macro messages: {errs[:3]}")

            # (1)(2) ORDERS
            xl_orders: dict[str, dict[str, tuple[float, float]]] = {}
            for r in read_sheet(wb.Worksheets("ORDERS"), 7):
                d, inv, b, s = to_date(r[0]), r[1], float(r[2]), float(r[3])
                if b > 0 and s > 0:
                    fails.append(f"buy&sell both >0 {d} {inv}")
                if r[6] != "OK":
                    fails.append(f"check col not OK {d} {inv}: {r[6]}")
                xl_orders.setdefault(d, {})[inv] = (b, s)
            for d in sorted(set(xl_orders) | set(ref_orders)):
                a, b = xl_orders.get(d, {}), ref_orders.get(d, {})
                if set(a) != set(b):
                    fails.append(f"order investors differ {d}: xl={sorted(a)} ref={sorted(b)}")
                    continue
                for inv in a:
                    if not (close(a[inv][0], b[inv][0]) and close(a[inv][1], b[inv][1])):
                        fails.append(f"qty differ {d} {inv}: xl={a[inv]} ref={b[inv]}")
            n_orders = sum(len(v) for v in xl_orders.values())

            # (3) STATE
            xs = read_sheet(wb.Worksheets("STATE"), 13)
            if len(xs) != len(tr):
                fails.append(f"tranche count xl={len(xs)} ref={len(tr)}")
            for row, t in zip(xs, tr):
                if (row[0], int(row[1]), row[2]) != (t.inv, t.tid, t.strat):
                    fails.append(f"tranche id differ {row[:3]} vs {(t.inv, t.tid, t.strat)}")
                    continue
                if not (close(row[4], t.cash, 1e-4) and close(row[5], t.shares)):
                    fails.append(f"state differ {t.inv}#{t.tid}: xl cash={row[4]} sh={row[5]} ref cash={t.cash} sh={t.shares}")
                if int(row[10]) != int(t.closed):
                    fails.append(f"closed flag differ {t.inv}#{t.tid}")

            # (3b) progress columns (STATE N..V)
            xs22 = read_sheet(wb.Worksheets("STATE"), 22)
            p_last = m[-2][2]
            for row, t in zip(xs22, tr):
                if t.closed:
                    if row[13] != "CLOSED":
                        fails.append(f"stage should be CLOSED {t.inv}#{t.tid}: {row[13]}")
                    continue
                stage = "RAMP" if t.k < 10 else "ACTIVE" if t.active else "SOLD" if t.sold else "IDLE"
                tot = t.cash + t.shares * p_last
                w = t.shares * p_last / tot if tot > 0 else 0.0
                if row[13] != stage:
                    fails.append(f"stage {t.inv}#{t.tid}: xl={row[13]} ref={stage}")
                if int(row[15]) != min(t.k, 10) or not close(float(row[16]), 0.40 * min(t.k, 10) / 10, 1e-12):
                    fails.append(f"ramp progress {t.inv}#{t.tid}: xl={row[15]}/{row[16]} ref={min(t.k, 10)}")
                if stage == "ACTIVE" and int(row[17]) != 21 - t.days:
                    fails.append(f"days-to-next-buy {t.inv}#{t.tid}: xl={row[17]} ref={21 - t.days}")
                if stage != "RAMP":
                    sf = 1.0 if t.strat == "H" else 0.5
                    exp = w if (stage == "SOLD" and sf < 1) else (0.0 if sf >= 1 else w * (1 - sf))
                    if row[20] is None or not close(float(row[20]), exp, 1e-9):
                        fails.append(f"sell-target weight {t.inv}#{t.tid} {stage}: xl={row[20]} ref={exp}")
                if not str(row[14]):
                    fails.append(f"stage label empty {t.inv}#{t.tid}")
            for r in read_sheet(wb.Worksheets("LOG"), 13):
                if r[3] == "RAMP_BUY" and not (str(r[11]).endswith("/10") and 1 <= int(str(r[11]).split("/")[0]) <= 10):
                    fails.append(f"RAMP note bad: {r[11]!r}")
                    break
            for r in read_sheet(wb.Worksheets("ORDERS"), 12):
                if not r[10]:
                    fails.append(f"order reason empty {to_date(r[0])} {r[1]}")
                    break

            # (4) LOG trade events
            xl_ev = sorted((to_date(r[0]), r[1], int(r[2]), r[3], float(r[5])) for r in read_sheet(wb.Worksheets("LOG"), 11) if r[3] in TRADE_KINDS)
            rf_ev = sorted((e[0], e[1], e[2], e[3], float(e[4])) for e in ref_events)
            if len(xl_ev) != len(rf_ev):
                fails.append(f"event count xl={len(xl_ev)} ref={len(rf_ev)}")
            else:
                for a, b in zip(xl_ev, rf_ev):
                    if a[:4] != b[:4] or not close(a[4], b[4]):
                        fails.append(f"event differ xl={a} ref={b}")
                        break
            kinds: dict[str, int] = {}
            for e in xl_ev:
                kinds[e[3]] = kinds.get(e[3], 0) + 1

            # (5) guards
            last_date = m[-1][0]
            opt("OrderDate", serial(m[-2][0]))
            xl.Run("RunDay")
            if "already processed" not in str(opt("LastMessage")):
                fails.append("duplicate-run guard missing")
            opt("OrderDate", serial(last_date) + 5)
            wb.Worksheets("MARKET").Cells(len(m) + 1, 1).Value2 = serial(last_date) + 10
            wb.Worksheets("MARKET").Cells(len(m) + 1, 2).Value2 = 50
            wb.Worksheets("MARKET").Cells(len(m) + 1, 3).Value2 = 100
            n_before = len(read_sheet(wb.Worksheets("ORDERS"), 7))
            xl.Run("RunDay")
            if "earlier than OrderDate" not in str(opt("LastMessage")) or len(read_sheet(wb.Worksheets("ORDERS"), 7)) != n_before:
                fails.append("market-date guard missing")
            wb.Worksheets("MARKET").Range(wb.Worksheets("MARKET").Cells(len(m) + 1, 1), wb.Worksheets("MARKET").Cells(len(m) + 1, 3)).ClearContents()

            # (6) ApplyFills
            wo, ws_state = wb.Worksheets("ORDERS"), wb.Worksheets("STATE")
            orows = read_sheet(wo, 7)
            target = next(i for i, r in enumerate(orows) if r[2] > 0)  # first buy order
            r = orows[target]
            inv, est, basis = r[1], float(r[2]), float(r[4])
            srows = read_sheet(ws_state, 13)
            cand = [(float(x[11]), i) for i, x in enumerate(srows) if x[0] == inv and int(x[10]) == 0]
            big = max(cand)[1]
            before = (float(srows[big][4]), float(srows[big][5]))
            act, px_fill = est + 2 if not integer else est + 2, basis * 1.01
            wo.Cells(target + 2, 8).Value2 = act
            wo.Cells(target + 2, 9).Value2 = px_fill
            xl.Run("ApplyFills")
            after_row = read_sheet(ws_state, 13)[big]
            exp_sh = before[1] + (act - est)
            exp_cash = before[0] + est * basis - act * px_fill
            if not (close(float(after_row[5]), exp_sh) and close(float(after_row[4]), exp_cash, 1e-4)):
                fails.append(f"ApplyFills mismatch sh {after_row[5]} vs {exp_sh}; cash {after_row[4]} vs {exp_cash}")
            xl.Run("ApplyFills")  # 재실행해도 이중 반영되면 안 됨
            again = read_sheet(ws_state, 13)[big]
            if not (close(float(again[5]), exp_sh) and close(float(again[4]), exp_cash, 1e-4)):
                fails.append("ApplyFills double-applied")

            wb.Close(False)
            ok = not fails
            ok_all &= ok
            print(f"[{mode}] sample STATE row: {xs22[0][13:22]}")
            print(f"[{mode}] days={len(m) - 1} tranches={len(tr)} orderRows={n_orders} events={len(xl_ev)} {kinds} -> {'PASS' if ok else 'FAIL'}")
            for f in fails[:15]:
                print("   ", f)
        ef = edge_tests(xl, m)
        ok_all &= not ef
        print("[edge] " + ("PASS" if not ef else "FAIL " + str(ef)))
        for mode in ("FRAC", "INT"):
            for jj in (45, 64, 100, 330):
                f2 = import_test(xl, m, flows, mode, jj)
                ok_all &= not f2
                print(f"[import {mode} j={jj}] " + ("PASS" if not f2 else "FAIL " + str(f2[:4])))
    finally:
        xl.Quit()
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
