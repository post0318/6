Attribute VB_Name = "FG_Trading"
Option Explicit
'------------------------------------------------------------------
' FG strategy (H / I) daily order engine.  ASCII only on purpose.
' Sheets: Settings, MARKET, INVESTOR, STATE, ORDERS, LOG
' Daily flow:  1) append yesterday's US row to MARKET (date, FG, ETF close)
'              2) paste today's cash flows into INVESTOR
'              3) set Settings!OrderDate and press RunDay  -> ORDERS (buy qty / sell qty)
'              4) after execution type fills into ORDERS (H, I) and press ApplyFills
' Signal uses the FG of the last MARKET row (previous US trading day);
' quantities are estimated with that same row's ETF close (previous close).
'------------------------------------------------------------------

Private Type TrancheT
    Inv As String
    TNo As Long
    Strat As String
    StartDate As Double
    Cash As Double
    Shares As Double
    Active As Long
    Sold As Long
    DaysSince As Long
    K As Long
    Closed As Long
End Type

Private Type ParamT
    Init As Double
    Ramp As Long
    Interval As Long
    StepPct As Double
    Resell As Double
    Crash As Double
    CrashFrac As Double
    SellFrac As Double
End Type

Private tr() As TrancheT
Private nTr As Long
Private evD() As Double
Private evInv() As String
Private evT() As Long
Private evKind() As String
Private evQty() As Double
Private evPx() As Double
Private evW() As Double
Private evAmt() As Double
Private evNote() As String
Private evDw() As Double
Private dWhy As Object
Private lbl As Object
Private curRamp As Long
Private oldN As Long
Private skipBuy As Long
Private nEv As Long
Private dBuy As Object
Private dSell As Object
Private dKeys As Object

Private Const EPS As Double = 0.000000001

'------------------------------ settings helpers ------------------
Private Function OptRow(key As String) As Long
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets("Settings")
    For r = 2 To 60
        If Trim(CStr(ws.Cells(r, 10).Value)) = key Then OptRow = r: Exit Function
    Next r
    OptRow = 0
End Function

Private Function OptStr(key As String) As String
    Dim r As Long
    r = OptRow(key)
    If r = 0 Then OptStr = "" Else OptStr = Trim(CStr(ThisWorkbook.Worksheets("Settings").Cells(r, 12).Value))
End Function

Private Function OptNum(key As String) As Double
    Dim r As Long, v As Variant
    r = OptRow(key)
    OptNum = 0
    If r = 0 Then Exit Function
    v = ThisWorkbook.Worksheets("Settings").Cells(r, 12).Value
    If IsEmpty(v) Then Exit Function
    If IsNumeric(v) Or IsDate(v) Then OptNum = CDbl(v)
End Function

Private Sub SetOpt(key As String, v As Variant)
    Dim r As Long
    r = OptRow(key)
    If r > 0 Then ThisWorkbook.Worksheets("Settings").Cells(r, 12).Value2 = v
End Sub

Private Function GetParams(strat As String, ByRef P As ParamT) As Boolean
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets("Settings")
    For r = 2 To 21
        If Trim(CStr(ws.Cells(r, 1).Value)) = strat And strat <> "" Then
            P.Init = CDbl(ws.Cells(r, 2).Value)
            P.Ramp = CLng(ws.Cells(r, 3).Value)
            P.Interval = CLng(ws.Cells(r, 4).Value)
            P.StepPct = CDbl(ws.Cells(r, 5).Value)
            P.Resell = CDbl(ws.Cells(r, 6).Value)
            P.Crash = CDbl(ws.Cells(r, 7).Value)
            P.CrashFrac = CDbl(ws.Cells(r, 8).Value)
            P.SellFrac = CDbl(ws.Cells(r, 9).Value)
            GetParams = True
            Exit Function
        End If
    Next r
    GetParams = False
End Function

Private Sub Fast(onOff As Boolean)
    With Application
        .ScreenUpdating = Not onOff
        .EnableEvents = Not onOff
        If onOff Then
            .Calculation = xlCalculationManual
        Else
            .Calculation = xlCalculationAutomatic
            .Calculate
        End If
    End With
End Sub

Private Sub Say(msg As String, Optional style As Long = 64, Optional korKey As String = "")
    Dim shown As String
    SetOpt "LastMessage", msg
    shown = msg
    If korKey <> "" Then shown = Lbl_(korKey) & vbCrLf & vbCrLf & msg
    If UCase(OptStr("Silent")) <> "Y" Then MsgBox shown, style
End Sub

'------------------------------ event log -------------------------
Private Sub GrowEv()
    Dim n As Long
    n = UBound(evD) * 2
    ReDim Preserve evD(1 To n)
    ReDim Preserve evInv(1 To n)
    ReDim Preserve evT(1 To n)
    ReDim Preserve evKind(1 To n)
    ReDim Preserve evQty(1 To n)
    ReDim Preserve evPx(1 To n)
    ReDim Preserve evW(1 To n)
    ReDim Preserve evAmt(1 To n)
    ReDim Preserve evNote(1 To n)
    ReDim Preserve evDw(1 To n)
End Sub

Private Sub PushEv(d As Double, inv As String, tno As Long, kind As String, q As Double, px As Double, w As Double, amt As Double, Optional note As String = "", Optional dw As Double = 0)
    nEv = nEv + 1
    If nEv > UBound(evD) Then GrowEv
    evD(nEv) = d: evInv(nEv) = inv: evT(nEv) = tno: evKind(nEv) = kind
    evQty(nEv) = q: evPx(nEv) = px: evW(nEv) = w: evAmt(nEv) = amt
    evNote(nEv) = note: evDw(nEv) = dw
End Sub

Private Function WeightOf(idx As Long, px As Double) As Double
    Dim tot As Double
    tot = tr(idx).Cash + tr(idx).Shares * px
    If tot > 0 Then WeightOf = tr(idx).Shares * px / tot Else WeightOf = 0
End Function

Private Function Lbl_(kind As String) As String
    Dim r As Long, ws As Worksheet
    If lbl Is Nothing Then
        Set lbl = CreateObject("Scripting.Dictionary")
        Set ws = ThisWorkbook.Worksheets("Settings")
        For r = 2 To 40
            If Trim(CStr(ws.Cells(r, 14).Value)) <> "" Then lbl(Trim(CStr(ws.Cells(r, 14).Value))) = CStr(ws.Cells(r, 15).Value)
        Next r
    End If
    If lbl.Exists(kind) Then Lbl_ = lbl(kind) Else Lbl_ = kind
End Function

' trade event: also feeds the per-investor net (buy - sell) order
Private Sub AddTrade(d As Double, idx As Long, kind As String, q As Double, px As Double)
    Dim inv As String, wA As Double, wB As Double, tot As Double, note As String, why As String
    inv = tr(idx).Inv
    tot = tr(idx).Cash + tr(idx).Shares * px
    wA = WeightOf(idx, px)
    If tot > 0 Then wB = (tr(idx).Shares - q) * px / tot Else wB = 0
    note = ""
    If kind = "RAMP_BUY" Then note = (tr(idx).K + 1) & "/" & curRamp
    PushEv d, inv, tr(idx).TNo, kind, q, px, wA, 0, note, wA - wB
    If Not dKeys.Exists(inv) Then dKeys.Add inv, 1: dBuy(inv) = 0#: dSell(inv) = 0#: dWhy(inv) = ""
    If q > 0 Then dBuy(inv) = dBuy(inv) + q Else dSell(inv) = dSell(inv) - q
    why = Lbl_(kind)
    If note <> "" Then why = why & " " & note
    If InStr(dWhy(inv), why) = 0 Then
        If dWhy(inv) <> "" Then dWhy(inv) = dWhy(inv) & " + "
        dWhy(inv) = dWhy(inv) & why
    End If
End Sub

Private Sub DoBuy(idx As Long, value As Double, kind As String, px As Double, isInt As Boolean, d As Double)
    Dim q As Double
    If isInt Then q = Int(value / px + EPS) Else q = value / px
    If q <= 0 Then
        If value > EPS Then skipBuy = skipBuy + 1
        Exit Sub
    End If
    tr(idx).Cash = tr(idx).Cash - q * px
    tr(idx).Shares = tr(idx).Shares + q
    AddTrade d, idx, kind, q, px
End Sub

'------------------------------ strategy step ---------------------
Private Sub StepTr(idx As Long, P As ParamT, f As Double, px As Double, isInt As Boolean, d As Double)
    Dim total As Double, cw As Double, bv As Double, q As Double, was As Long

    curRamp = P.Ramp
    total = tr(idx).Cash + tr(idx).Shares * px
    If tr(idx).K < P.Ramp Then
        bv = P.Init / P.Ramp * total
        If tr(idx).Cash < bv Then bv = tr(idx).Cash
        DoBuy idx, bv, "RAMP_BUY", px, isInt, d
    Else
        If total > 0 Then cw = tr(idx).Shares * px / total Else cw = 0
        If cw > EPS And f >= P.Resell And Not (P.SellFrac < 1 And tr(idx).Sold = 1) Then
            If P.SellFrac >= 1 Then
                q = tr(idx).Shares
            ElseIf isInt Then
                q = Int(tr(idx).Shares * P.SellFrac + EPS)
            Else
                q = tr(idx).Shares * P.SellFrac
            End If
            tr(idx).Cash = tr(idx).Cash + q * px
            tr(idx).Shares = tr(idx).Shares - q
            tr(idx).Active = 0
            tr(idx).Sold = 1
            tr(idx).DaysSince = 0
            If q > 0 Then AddTrade d, idx, "SELL", -q, px
        Else
            was = tr(idx).Active
            If f < P.Resell Then
                tr(idx).Active = 1
                tr(idx).Sold = 0
            End If
            If tr(idx).Active = 1 And was = 0 Then tr(idx).DaysSince = 0
            total = tr(idx).Cash + tr(idx).Shares * px
            If total > 0 Then cw = tr(idx).Shares * px / total Else cw = 0
            If tr(idx).Active = 1 And P.CrashFrac > 0 And f < P.Crash And cw < 1 - EPS Then
                DoBuy idx, P.CrashFrac * tr(idx).Cash, "CRASH_BUY", px, isInt, d
                tr(idx).DaysSince = 0
            Else
                tr(idx).DaysSince = tr(idx).DaysSince + 1
                If tr(idx).Active = 1 And tr(idx).DaysSince >= P.Interval And cw < 1 - EPS Then
                    bv = P.StepPct * total
                    If tr(idx).Cash < bv Then bv = tr(idx).Cash
                    If bv > 0 Then DoBuy idx, bv, "WEEKLY_BUY", px, isInt, d
                    tr(idx).DaysSince = 0
                End If
            End If
        End If
    End If
    tr(idx).K = tr(idx).K + 1
End Sub

'------------------------------ withdrawal ------------------------
Private Sub DoWithdraw(inv As String, amount As Double, px As Double, isInt As Boolean, d As Double)
    Dim i As Long, cashTot As Double, payCash As Double, shortAmt As Double, valTot As Double
    Dim ratio As Double, q As Double, tot As Double, pay As Double
    Dim sq() As Double
    ReDim sq(0 To nTr)
    For i = 1 To nTr
        If tr(i).Inv = inv And tr(i).Closed = 0 Then cashTot = cashTot + tr(i).Cash
    Next i
    payCash = amount
    If cashTot < payCash Then payCash = cashTot
    If cashTot > 0 Then
        For i = 1 To nTr
            If tr(i).Inv = inv And tr(i).Closed = 0 Then tr(i).Cash = tr(i).Cash - payCash * tr(i).Cash / cashTot
        Next i
    End If
    shortAmt = amount - payCash
    If shortAmt > EPS Then
        For i = 1 To nTr
            If tr(i).Inv = inv And tr(i).Closed = 0 Then valTot = valTot + tr(i).Shares * px
        Next i
        If valTot > 0 Then
            ratio = shortAmt / valTot
            If ratio > 1 Then ratio = 1
        Else
            ratio = 0
        End If
        For i = 1 To nTr
            If tr(i).Inv = inv And tr(i).Closed = 0 Then
                q = tr(i).Shares * ratio
                If isInt Then
                    q = -Int(-(q - EPS))
                    If q > tr(i).Shares Then q = tr(i).Shares
                End If
                If q > 0 Then
                    tr(i).Shares = tr(i).Shares - q
                    tr(i).Cash = tr(i).Cash + q * px
                    sq(i) = q
                    tot = tot + q * px
                End If
            End If
        Next i
        pay = shortAmt
        If tot < pay Then pay = tot
        For i = 1 To nTr
            If sq(i) > 0 Then
                tr(i).Cash = tr(i).Cash - pay * (sq(i) * px) / tot
                AddTrade d, i, "WD_SELL", -sq(i), px
            End If
        Next i
    End If
    For i = 1 To nTr
        If tr(i).Inv = inv And tr(i).Closed = 0 Then
            If tr(i).Shares <= 0.000000000001 And tr(i).Cash <= EPS Then tr(i).Closed = 1
        End If
    Next i
    PushEv d, inv, 0, "WITHDRAW", 0, px, 0, -amount
End Sub

Private Function InvWeight(inv As String, px As Double) As Double
    Dim i As Long, sh As Double, tt As Double
    For i = 1 To nTr
        If tr(i).Inv = inv And tr(i).Closed = 0 Then
            sh = sh + tr(i).Shares * px
            tt = tt + tr(i).Cash + tr(i).Shares * px
        End If
    Next i
    If tt > 0 Then InvWeight = sh / tt Else InvWeight = 0
End Function

'------------------------------ STATE load / write ----------------
Private Sub LoadState()
    Dim wsS As Worksheet, lastI As Long, arr As Variant, i As Long
    Set wsS = ThisWorkbook.Worksheets("STATE")
    lastI = wsS.Cells(wsS.Rows.Count, 1).End(xlUp).Row
    nTr = lastI - 1
    If nTr < 0 Then nTr = 0
    oldN = nTr
    ReDim tr(0 To nTr + 500)
    If nTr > 0 Then
        arr = wsS.Range("A2:K" & lastI).Value
        For i = 1 To nTr
            tr(i).Inv = CStr(arr(i, 1)): tr(i).TNo = CLng(arr(i, 2)): tr(i).Strat = CStr(arr(i, 3))
            tr(i).StartDate = CDbl(arr(i, 4)): tr(i).Cash = CDbl(arr(i, 5)): tr(i).Shares = CDbl(arr(i, 6))
            tr(i).Active = CLng(arr(i, 7)): tr(i).Sold = CLng(arr(i, 8)): tr(i).DaysSince = CLng(arr(i, 9))
            tr(i).K = CLng(arr(i, 10)): tr(i).Closed = CLng(arr(i, 11))
        Next i
    End If
End Sub

Private Sub WriteState(px As Double, isInt As Boolean)
    Dim wsS As Worksheet, i As Long, P As ParamT
    Set wsS = ThisWorkbook.Worksheets("STATE")
    If oldN > 0 Then wsS.Range("A2:V" & (oldN + 1)).ClearContents
    If nTr > 0 Then
        Dim outS() As Variant, tot As Double, w As Double, stg As String, nxt As Double
        ReDim outS(1 To nTr, 1 To 22)
        For i = 1 To nTr
            outS(i, 1) = tr(i).Inv: outS(i, 2) = tr(i).TNo: outS(i, 3) = tr(i).Strat
            outS(i, 4) = tr(i).StartDate: outS(i, 5) = tr(i).Cash: outS(i, 6) = tr(i).Shares
            outS(i, 7) = tr(i).Active: outS(i, 8) = tr(i).Sold: outS(i, 9) = tr(i).DaysSince
            outS(i, 10) = tr(i).K: outS(i, 11) = tr(i).Closed
            If tr(i).Closed = 1 Then
                outS(i, 12) = 0: outS(i, 13) = 0: outS(i, 14) = "CLOSED"
            Else
                tot = tr(i).Cash + tr(i).Shares * px
                w = WeightOf(i, px)
                outS(i, 12) = tot: outS(i, 13) = w
                If GetParams(tr(i).Strat, P) Then
                    If tr(i).K < P.Ramp Then
                        stg = "RAMP"
                    ElseIf tr(i).Active = 1 Then
                        stg = "ACTIVE"
                    ElseIf tr(i).Sold = 1 Then
                        stg = "SOLD"
                    Else
                        stg = "IDLE"
                    End If
                    outS(i, 14) = stg
                    If tr(i).K < P.Ramp Then outS(i, 16) = tr(i).K Else outS(i, 16) = P.Ramp
                    outS(i, 17) = P.Init * outS(i, 16) / P.Ramp
                    If stg = "ACTIVE" Then
                        outS(i, 18) = P.Interval - tr(i).DaysSince
                        nxt = P.StepPct * tot
                        If tr(i).Cash < nxt Then nxt = tr(i).Cash
                        If w >= 1 - EPS Then nxt = 0
                        outS(i, 19) = nxt
                        If tot > 0 Then outS(i, 20) = nxt / tot
                    End If
                    If stg <> "RAMP" Then
                        If stg = "SOLD" And P.SellFrac < 1 Then
                            outS(i, 21) = w: outS(i, 22) = 0
                        ElseIf P.SellFrac >= 1 Then
                            outS(i, 21) = 0: outS(i, 22) = tr(i).Shares
                        Else
                            outS(i, 21) = w * (1 - P.SellFrac)
                            If isInt Then outS(i, 22) = Int(tr(i).Shares * P.SellFrac + EPS) Else outS(i, 22) = tr(i).Shares * P.SellFrac
                        End If
                    End If
                End If
            End If
        Next i
        wsS.Range("A2").Resize(nTr, 22).Value = outS
        wsS.Range("D2").Resize(nTr, 1).NumberFormat = "yyyy-mm-dd"
        wsS.Range("O2").Resize(nTr, 1).Formula = "=IFERROR(VLOOKUP(N2,Settings!$N$2:$O$40,2,FALSE),N2)&IF(N2=""RAMP"","" ""&P2&""/""&INDEX(Settings!$C$2:$C$21,MATCH(C2,Settings!$A$2:$A$21,0)),"""")"
    End If

    oldN = nTr
End Sub

'------------------------------ main: create today's orders -------
Public Sub RunDay()
    Dim wsM As Worksheet, wsI As Worksheet, wsS As Worksheet, wsL As Worksheet, wsO As Worksheet
    Dim lastM As Long, n As Long, mk As Variant, D As Double, lastRun As Double
    Dim f As Double, px As Double, isInt As Boolean
    Dim r As Long, lastI As Long, arr As Variant, i As Long
    Dim P As ParamT, k As Variant, net As Double, msg As String

    On Error GoTo EH
    Set wsM = ThisWorkbook.Worksheets("MARKET")
    Set wsI = ThisWorkbook.Worksheets("INVESTOR")
    Set wsS = ThisWorkbook.Worksheets("STATE")
    Set wsL = ThisWorkbook.Worksheets("LOG")
    Set wsO = ThisWorkbook.Worksheets("ORDERS")

    D = OptNum("OrderDate")
    If D <= 0 Then Say "Set Settings!OrderDate first.", vbExclamation, "MSG_NODATE": Exit Sub
    D = Int(D)
    lastRun = OptNum("LastRunDate")
    If D <= lastRun Then Say "OrderDate must be later than LastRunDate (already processed).", vbExclamation, "MSG_DUP": Exit Sub

    lastM = wsM.Cells(wsM.Rows.Count, 1).End(xlUp).Row
    n = lastM - 1
    If n < 1 Then Say "MARKET is empty.", vbExclamation, "MSG_NOMKT": Exit Sub
    mk = wsM.Range("A2:C" & lastM).Value
    If Int(CDbl(mk(n, 1))) >= D Then Say "Last MARKET date must be earlier than OrderDate (signal uses the previous trading day).", vbExclamation, "MSG_MKTDATE": Exit Sub
    f = CDbl(mk(n, 2))
    px = CDbl(mk(n, 3))
    If px <= 0 Then Say "Invalid ETF close in the last MARKET row.", vbExclamation, "MSG_PX": Exit Sub
    isInt = (UCase(OptStr("QtyMode")) = "INT")

    Dim nOld As Long
    lastI = wsI.Cells(wsI.Rows.Count, 1).End(xlUp).Row
    For r = 2 To lastI
        If Trim(CStr(wsI.Cells(r, 1).Value)) <> "" And Trim(CStr(wsI.Cells(r, 5).Value)) = "" Then
            If IsDate(wsI.Cells(r, 2).Value) Or IsNumeric(wsI.Cells(r, 2).Value) Then
                If Int(CDbl(wsI.Cells(r, 2).Value)) < D - 7 Then nOld = nOld + 1
            End If
        End If
    Next r
    If nOld > 0 And UCase(OptStr("Silent")) <> "Y" Then
        If MsgBox(Replace(Lbl_("MSG_OLDROWS"), "{OLD}", CStr(nOld)), vbYesNo + vbQuestion) <> vbYes Then
            Say "Cancelled: old-dated rows pending", vbInformation
            Exit Sub
        End If
    End If

    Fast True
    LoadState

    nEv = 0
    skipBuy = 0
    ReDim evD(1 To 200): ReDim evInv(1 To 200): ReDim evT(1 To 200): ReDim evKind(1 To 200)
    ReDim evQty(1 To 200): ReDim evPx(1 To 200): ReDim evW(1 To 200): ReDim evAmt(1 To 200)
    ReDim evNote(1 To 200): ReDim evDw(1 To 200)
    Set dWhy = CreateObject("Scripting.Dictionary")
    Set lbl = Nothing
    Set dBuy = CreateObject("Scripting.Dictionary")
    Set dSell = CreateObject("Scripting.Dictionary")
    Set dKeys = CreateObject("Scripting.Dictionary")

    ' unprocessed cash flows dated on or before today (blank status)
    Dim inv As String, amt As Double, strat As String, cnt As Long, dt As Double
    Dim nDep As Long, nWd As Long, nErr As Long, nFut As Long, nOrd As Long
    lastI = wsI.Cells(wsI.Rows.Count, 1).End(xlUp).Row
    For r = 2 To lastI
        If Trim(CStr(wsI.Cells(r, 1).Value)) <> "" And Trim(CStr(wsI.Cells(r, 5).Value)) = "" Then
            If Not (IsDate(wsI.Cells(r, 2).Value) Or IsNumeric(wsI.Cells(r, 2).Value)) Then
                wsI.Cells(r, 5).Value = "ERR:date": nErr = nErr + 1
            ElseIf Not IsNumeric(wsI.Cells(r, 3).Value) Or IsEmpty(wsI.Cells(r, 3).Value) Then
                wsI.Cells(r, 5).Value = "ERR:amount": nErr = nErr + 1
            Else
                dt = Int(CDbl(wsI.Cells(r, 2).Value))
                amt = CDbl(wsI.Cells(r, 3).Value)
                If dt > D Then
                    nFut = nFut + 1
                ElseIf amt = 0 Then
                    wsI.Cells(r, 5).Value = "ERR:amount": nErr = nErr + 1
                Else
                    inv = Trim(CStr(wsI.Cells(r, 1).Value))
                    strat = Trim(CStr(wsI.Cells(r, 4).Value))
                    If amt > 0 Then
                        If Not GetParams(strat, P) Then
                            wsI.Cells(r, 5).Value = "ERR:strategy": nErr = nErr + 1
                        Else
                            cnt = 0
                            For i = 1 To nTr
                                If tr(i).Inv = inv Then cnt = cnt + 1
                            Next i
                            nTr = nTr + 1
                            If nTr > UBound(tr) Then ReDim Preserve tr(0 To UBound(tr) * 2)
                            tr(nTr).Inv = inv: tr(nTr).TNo = cnt + 1: tr(nTr).Strat = strat
                            tr(nTr).StartDate = D: tr(nTr).Cash = amt: tr(nTr).Shares = 0
                            tr(nTr).Active = 0: tr(nTr).Sold = 0: tr(nTr).DaysSince = 0: tr(nTr).K = 0: tr(nTr).Closed = 0
                            PushEv D, inv, tr(nTr).TNo, "DEPOSIT", 0, px, 0, amt
                            wsI.Cells(r, 5).Value = "DONE"
                            nDep = nDep + 1
                        End If
                    Else
                        DoWithdraw inv, -amt, px, isInt, D
                        wsI.Cells(r, 5).Value = "DONE"
                        nWd = nWd + 1
                    End If
                End If
            End If
        End If
    Next r

    ' strategy step for every open tranche
    For i = 1 To nTr
        If tr(i).Closed = 0 Then
            If GetParams(tr(i).Strat, P) Then StepTr i, P, f, px, isInt, D
        End If
    Next i

    WriteState px, isInt

    ' append LOG
    If nEv > 0 Then
        Dim lr As Long, outL() As Variant
        lr = wsL.Cells(wsL.Rows.Count, 1).End(xlUp).Row + 1
        ReDim outL(1 To nEv, 1 To 13)
        For i = 1 To nEv
            outL(i, 1) = evD(i): outL(i, 2) = evInv(i): outL(i, 3) = evT(i): outL(i, 4) = evKind(i)
            outL(i, 5) = "": outL(i, 6) = evQty(i): outL(i, 7) = evPx(i): outL(i, 8) = evQty(i) * evPx(i)
            outL(i, 9) = evW(i): outL(i, 10) = "EST": outL(i, 11) = evAmt(i)
            outL(i, 12) = evNote(i): outL(i, 13) = evDw(i)
        Next i
        wsL.Range("L" & lr).Resize(nEv, 1).NumberFormat = "@"
        wsL.Range("A" & lr).Resize(nEv, 13).Value = outL
        wsL.Range("A" & lr).Resize(nEv, 1).NumberFormat = "yyyy-mm-dd"
        wsL.Range("E" & lr).Resize(nEv, 1).Formula = "=IFERROR(VLOOKUP(D" & lr & ",Settings!$N$2:$O$40,2,FALSE),D" & lr & ")"
    End If

    ' append ORDERS (one row per investor, buy qty OR sell qty)
    Dim orow As Long
    orow = wsO.Cells(wsO.Rows.Count, 1).End(xlUp).Row + 1
    For Each k In dKeys.Keys
        net = dBuy(k) - dSell(k)
        If Abs(net) > EPS Then
            wsO.Cells(orow, 1).Value2 = D: wsO.Cells(orow, 1).NumberFormat = "yyyy-mm-dd"
            wsO.Cells(orow, 2).Value = CStr(k)
            If net > 0 Then
                wsO.Cells(orow, 3).Value = net: wsO.Cells(orow, 4).Value = 0
            Else
                wsO.Cells(orow, 3).Value = 0: wsO.Cells(orow, 4).Value = -net
            End If
            wsO.Cells(orow, 5).Value = px
            wsO.Cells(orow, 6).Formula = "=(C" & orow & "-D" & orow & ")*E" & orow
            wsO.Cells(orow, 7).Formula = "=IF(AND(C" & orow & ">0,D" & orow & ">0),""ERROR"",""OK"")"
            wsO.Cells(orow, 11).Value = dWhy(k)
            wsO.Cells(orow, 12).Value = InvWeight(CStr(k), px)
            nOrd = nOrd + 1
            orow = orow + 1
        End If
    Next k

    SetOpt "LastRunDate", D
    Fast False
    msg = "Orders created for " & Format(D, "yyyy-mm-dd") & " (FG " & Format(f, "0.0") & ", basis close " & Format(px, "0.00") & ")"
    Dim kor As String
    kor = Lbl_("MSG_DONE")
    kor = Replace(kor, "{DATE}", Format(D, "yyyy-mm-dd"))
    kor = Replace(kor, "{FG}", Format(f, "0.0"))
    kor = Replace(kor, "{PX}", Format(px, "#,##0.00"))
    kor = Replace(kor, "{DEP}", CStr(nDep))
    kor = Replace(kor, "{WD}", CStr(nWd))
    kor = Replace(kor, "{ERR}", CStr(nErr))
    kor = Replace(kor, "{FUT}", CStr(nFut))
    kor = Replace(kor, "{ORD}", CStr(nOrd))
    kor = Replace(kor, "{TR}", CStr(nTr))
    If nTr = 0 Then kor = kor & vbCrLf & Lbl_("MSG_NOINV")
    If nErr > 0 Then kor = kor & vbCrLf & Lbl_("MSG_ERRROWS")
    If skipBuy > 0 Then kor = kor & vbCrLf & Replace(Lbl_("MSG_SMALL"), "{SKIP}", CStr(skipBuy))
    If nOrd = 0 And nTr > 0 Then kor = kor & vbCrLf & Lbl_("MSG_NOORDER")
    SetOpt "LastMessage", msg
    If UCase(OptStr("Silent")) <> "Y" Then MsgBox kor, vbInformation
    Exit Sub
EH:
    Fast False
    Say "ERROR " & Err.Number & ": " & Err.Description, vbCritical
End Sub

'------------------------------ actual fills ----------------------
' type actual quantity (positive) in ORDERS!H and actual price in ORDERS!I, then run.
Public Sub ApplyFills()
    Dim wsO As Worksheet, wsS As Worksheet, wsL As Worksheet
    Dim lastO As Long, r As Long, inv As String, estSigned As Double, actSigned As Double
    Dim basis As Double, fillPx As Double, dq As Double, dCash As Double
    Dim lastS As Long, i As Long, best As Long, bestVal As Double, v As Double, cnt As Long
    Dim lr As Long

    On Error GoTo EH
    Set wsO = ThisWorkbook.Worksheets("ORDERS")
    Set wsS = ThisWorkbook.Worksheets("STATE")
    Set wsL = ThisWorkbook.Worksheets("LOG")
    lastO = wsO.Cells(wsO.Rows.Count, 1).End(xlUp).Row
    lastS = wsS.Cells(wsS.Rows.Count, 1).End(xlUp).Row
    If lastO < 2 Or lastS < 2 Then Exit Sub
    Fast True

    For r = 2 To lastO
        If IsNumeric(wsO.Cells(r, 8).Value) And Not IsEmpty(wsO.Cells(r, 8).Value) And IsNumeric(wsO.Cells(r, 9).Value) And Not IsEmpty(wsO.Cells(r, 9).Value) And Trim(CStr(wsO.Cells(r, 10).Value)) = "" Then
            inv = CStr(wsO.Cells(r, 2).Value)
            basis = CDbl(wsO.Cells(r, 5).Value)
            fillPx = CDbl(wsO.Cells(r, 9).Value)
            If CDbl(wsO.Cells(r, 3).Value) > 0 Then
                estSigned = CDbl(wsO.Cells(r, 3).Value)
                actSigned = CDbl(wsO.Cells(r, 8).Value)
            Else
                estSigned = -CDbl(wsO.Cells(r, 4).Value)
                actSigned = -CDbl(wsO.Cells(r, 8).Value)
            End If
            dq = actSigned - estSigned
            dCash = estSigned * basis - actSigned * fillPx
            ' apply the difference to the investor's largest open tranche
            best = 0: bestVal = -1
            For i = 2 To lastS
                If CStr(wsS.Cells(i, 1).Value) = inv And CLng(wsS.Cells(i, 11).Value) = 0 Then
                    v = CDbl(wsS.Cells(i, 12).Value)
                    If v > bestVal Then bestVal = v: best = i
                End If
            Next i
            If best > 0 Then
                wsS.Cells(best, 6).Value = CDbl(wsS.Cells(best, 6).Value) + dq
                wsS.Cells(best, 5).Value = CDbl(wsS.Cells(best, 5).Value) + dCash
                lr = wsL.Cells(wsL.Rows.Count, 1).End(xlUp).Row + 1
                wsL.Cells(lr, 1).Value2 = wsO.Cells(r, 1).Value2: wsL.Cells(lr, 1).NumberFormat = "yyyy-mm-dd"
                wsL.Cells(lr, 2).Value = inv
                wsL.Cells(lr, 3).Value = wsS.Cells(best, 2).Value
                wsL.Cells(lr, 4).Value = "FILL_ADJ"
                wsL.Cells(lr, 6).Value = dq
                wsL.Cells(lr, 7).Value = fillPx
                wsL.Cells(lr, 8).Value = actSigned * fillPx
                wsL.Cells(lr, 10).Value = "CONFIRMED"
                wsL.Cells(lr, 11).Value = dCash
                wsL.Cells(lr, 5).Formula = "=IFERROR(VLOOKUP(D" & lr & ",Settings!$N$2:$O$40,2,FALSE),D" & lr & ")"
                wsO.Cells(r, 10).Value = "APPLIED"
                cnt = cnt + 1
            Else
                wsO.Cells(r, 10).Value = "ERR:no tranche"
            End If
        End If
    Next r
    Fast False
    Say cnt & " fill(s) applied.", vbInformation
    Exit Sub
EH:
    Fast False
    Say "ERROR " & Err.Number & ": " & Err.Description, vbCritical
End Sub

'------------------------------ existing investors ----------------
' IMPORT sheet columns: A id, B strategy, C start date, D cash, E shares,
' F ramp steps done, G days since last regular buy, H active Y/N, I sold Y/N, J status
Public Sub ImportExisting()
    Dim wsX As Worksheet, wsM As Worksheet, wsL As Worksheet
    Dim lastX As Long, lastM As Long, r As Long, i As Long, cnt As Long, lr As Long
    Dim inv As String, strat As String, P As ParamT, isInt As Boolean
    Dim cash As Double, sh As Double, kk As Long, ds As Long, act As Long, sld As Long
    Dim fLast As Double, px As Double, nOk As Long, nErr As Long, st As String, dStart As Double, v As Variant

    On Error GoTo EH
    Set wsX = ThisWorkbook.Worksheets("IMPORT")
    Set wsM = ThisWorkbook.Worksheets("MARKET")
    Set wsL = ThisWorkbook.Worksheets("LOG")
    lastM = wsM.Cells(wsM.Rows.Count, 1).End(xlUp).Row
    If lastM < 2 Then Say "MARKET is empty.", vbExclamation, "MSG_NOMKT": Exit Sub
    fLast = CDbl(wsM.Cells(lastM, 2).Value)
    px = CDbl(wsM.Cells(lastM, 3).Value)
    If px <= 0 Then Say "Invalid ETF close in the last MARKET row.", vbExclamation, "MSG_PX": Exit Sub
    isInt = (UCase(OptStr("QtyMode")) = "INT")

    Fast True
    LoadState
    lastX = wsX.Cells(wsX.Rows.Count, 1).End(xlUp).Row
    For r = 2 To lastX
        inv = Trim(CStr(wsX.Cells(r, 1).Value))
        If inv <> "" And Trim(CStr(wsX.Cells(r, 10).Value)) = "" Then
            st = ""
            cash = 0: sh = 0
            strat = Trim(CStr(wsX.Cells(r, 2).Value))
            If Not GetParams(strat, P) Then st = "ERR:strategy"
            If st = "" Then
                v = wsX.Cells(r, 3).Value
                If IsDate(v) Or IsNumeric(v) Then dStart = Int(CDbl(v)) Else st = "ERR:date"
            End If
            If st = "" Then
                v = wsX.Cells(r, 4).Value
                If Not IsEmpty(v) Then
                    If IsNumeric(v) Then cash = CDbl(v) Else st = "ERR:amount"
                End If
                v = wsX.Cells(r, 5).Value
                If Not IsEmpty(v) Then
                    If IsNumeric(v) Then sh = CDbl(v) Else st = "ERR:amount"
                End If
                If st = "" Then
                    If cash < 0 Or sh < 0 Or cash + sh * px <= 0 Then st = "ERR:amount"
                End If
            End If
            If st = "" Then
                kk = P.Ramp: ds = 0
                v = wsX.Cells(r, 6).Value
                If Not IsEmpty(v) Then
                    If IsNumeric(v) Then
                        kk = CLng(v)
                        If kk < 0 Then st = "ERR:progress"
                    Else
                        st = "ERR:progress"
                    End If
                End If
                v = wsX.Cells(r, 7).Value
                If Not IsEmpty(v) Then
                    If IsNumeric(v) Then
                        ds = CLng(v)
                        If ds < 0 Then st = "ERR:progress"
                    Else
                        st = "ERR:progress"
                    End If
                End If
            End If
            If st = "" Then
                sld = 0
                If UCase(Trim(CStr(wsX.Cells(r, 9).Value))) = "Y" Then sld = 1
                v = UCase(Trim(CStr(wsX.Cells(r, 8).Value)))
                If v = "Y" Then
                    act = 1
                ElseIf v = "N" Then
                    act = 0
                ElseIf kk >= P.Ramp And sld = 0 And fLast < P.Resell Then
                    act = 1
                Else
                    act = 0
                End If
                cnt = 0
                For i = 1 To nTr
                    If tr(i).Inv = inv Then cnt = cnt + 1
                Next i
                nTr = nTr + 1
                If nTr > UBound(tr) Then ReDim Preserve tr(0 To UBound(tr) * 2)
                tr(nTr).Inv = inv: tr(nTr).TNo = cnt + 1: tr(nTr).Strat = strat
                tr(nTr).StartDate = dStart: tr(nTr).Cash = cash: tr(nTr).Shares = sh
                tr(nTr).Active = act: tr(nTr).Sold = sld: tr(nTr).DaysSince = ds: tr(nTr).K = kk: tr(nTr).Closed = 0
                lr = wsL.Cells(wsL.Rows.Count, 1).End(xlUp).Row + 1
                wsL.Cells(lr, 1).Value2 = CDbl(Date): wsL.Cells(lr, 1).NumberFormat = "yyyy-mm-dd"
                wsL.Cells(lr, 2).Value = inv
                wsL.Cells(lr, 3).Value = tr(nTr).TNo
                wsL.Cells(lr, 4).Value = "IMPORT"
                wsL.Cells(lr, 5).Formula = "=IFERROR(VLOOKUP(D" & lr & ",Settings!$N$2:$O$40,2,FALSE),D" & lr & ")"
                wsL.Cells(lr, 6).Value = sh
                wsL.Cells(lr, 7).Value = px
                wsL.Cells(lr, 8).Value = sh * px
                wsL.Cells(lr, 10).Value = "CONFIRMED"
                wsL.Cells(lr, 11).Value = cash
                st = "DONE"
                nOk = nOk + 1
            Else
                nErr = nErr + 1
            End If
            wsX.Cells(r, 10).Value = st
        End If
    Next r
    If nOk > 0 Then WriteState px, isInt
    Fast False
    Dim kor As String
    kor = Lbl_("MSG_IMP_DONE")
    kor = Replace(kor, "{OK}", CStr(nOk))
    kor = Replace(kor, "{ERR}", CStr(nErr))
    kor = Replace(kor, "{TR}", CStr(nTr))
    If nErr > 0 Then kor = kor & vbCrLf & Lbl_("MSG_ERRROWS")
    SetOpt "LastMessage", "Imported " & nOk & ", errors " & nErr
    If UCase(OptStr("Silent")) <> "Y" Then MsgBox kor, vbInformation
    Exit Sub
EH:
    Fast False
    Say "ERROR " & Err.Number & ": " & Err.Description, vbCritical
End Sub
