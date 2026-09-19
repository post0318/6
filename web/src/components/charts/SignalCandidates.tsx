"use client";

import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SignalCandidate, SignalTrade, TimeseriesPoint } from "@/lib/types";
import {
  CATEGORICAL,
  CHART_SURFACE,
  EXTREME_FEAR_BAND,
  EXTREME_GREED_BAND,
  GRIDLINE,
  INK_MUTED,
  INK_PRIMARY,
  INK_SECONDARY,
} from "@/lib/palette";

// Buy&Hold가 orange를 쓰므로, 후보들은 나머지 팔레트 슬롯을 고정 순서대로 배정
const CANDIDATE_COLORS: Record<string, string> = {
  A: CATEGORICAL.blue,
  B: CATEGORICAL.aqua,
  C: CATEGORICAL.yellow,
  D: CATEGORICAL.magenta,
  E: CATEGORICAL.green,
  F: CATEGORICAL.violet,
  G: CATEGORICAL.red,
  // 팔레트 8슬롯은 Buy&Hold+A~G가 다 써서, H는 새 색을 만들지 않고 검정 계열 점선(복합 인코딩)으로 구분
  H: INK_PRIMARY,
};

const ACTION_KO: Record<SignalTrade["action"], string> = {
  RAMP_BUY: "초기램프 매수",
  WEEKLY_BUY: "정기 매수",
  CRASH_FULL_BUY: "급락 전량매수",
  SELL_ALL: "전량매도",
};

const ACTION_COLOR: Record<SignalTrade["action"], string> = {
  RAMP_BUY: CATEGORICAL.blue,
  WEEKLY_BUY: CATEGORICAL.blue,
  CRASH_FULL_BUY: CATEGORICAL.aqua,
  SELL_ALL: CATEGORICAL.orange,
};

function pct(v: number) {
  const sign = v >= 0 ? "+" : "";
  return `${sign}${(v * 100).toFixed(1)}%`;
}

function tickFormatter(dates: string[]) {
  return (value: string) => {
    const idx = dates.indexOf(value);
    if (idx === -1) return "";
    return value.slice(0, 7);
  };
}

export function CandidatesEquityChart({
  candidates,
  buyHold,
}: {
  candidates: SignalCandidate[];
  buyHold: { date: string; buyHold: number | null }[];
}) {
  const dates = buyHold.map((d) => d.date);
  const merged = buyHold.map((row, i) => {
    const point: Record<string, number | string> = { date: row.date, buyHold: row.buyHold ?? NaN };
    for (const c of candidates) point[c.id] = c.equityCurve[i]?.equity ?? NaN;
    return point;
  });

  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">후보 A~H 자산가치 비교 (시작값 100 기준)</h4>
      <p className="mb-3 text-xs text-[#898781]">
        A~G의 성과 차이는 매우 작습니다 — B/C/D/F(모두 40%/10% 계열)는 거의 겹쳐 보입니다.
        점선(H)은 트리거만 79/31로 바꾼 설정이라 나머지와 모양이 달라집니다.
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={merged} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: INK_MUTED }}
            tickFormatter={tickFormatter(dates)}
            minTickGap={60}
            axisLine={{ stroke: GRIDLINE }}
            tickLine={false}
          />
          <YAxis tick={{ fontSize: 11, fill: INK_MUTED }} axisLine={false} tickLine={false} width={48} domain={["auto", "auto"]} />
          <Tooltip
            formatter={(value, name) => [typeof value === "number" ? value.toFixed(1) : "-", String(name)]}
            contentStyle={{ fontSize: 12, borderRadius: 6, borderColor: "rgba(11,11,11,0.1)" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v) => (v === "buyHold" ? "Buy & Hold" : `후보 ${v}`)} />
          <Line type="monotone" dataKey="buyHold" name="buyHold" stroke={CATEGORICAL.orange} strokeWidth={2} dot={false} isAnimationActive={false} />
          {candidates.map((c) => (
            <Line
              key={c.id}
              type="monotone"
              dataKey={c.id}
              name={c.id}
              stroke={CANDIDATE_COLORS[c.id] ?? INK_PRIMARY}
              strokeWidth={2}
              strokeDasharray={c.id === "H" ? "6 3" : undefined}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SignalTooltip({
  active,
  payload,
  label,
  valueLabel,
  lineKey,
  formatter,
}: {
  active?: boolean;
  payload?: { value: number; dataKey: string; name?: string }[];
  label?: string;
  valueLabel: string;
  lineKey: string;
  formatter: (v: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const linePoint = payload.find((p) => p.dataKey === lineKey);
  const buyPoint = payload.find((p) => p.name === "buy" && p.value != null);
  const sellPoint = payload.find((p) => p.name === "sell" && p.value != null);
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="text-[#898781]">{label}</div>
      {linePoint && (
        <div className="text-[#0b0b0b]">
          {valueLabel}: {formatter(linePoint.value)}
        </div>
      )}
      {buyPoint && <div className="font-medium" style={{ color: CATEGORICAL.blue }}>매수 신호</div>}
      {sellPoint && <div className="font-medium" style={{ color: CATEGORICAL.orange }}>매도 신호</div>}
    </div>
  );
}

function tsTickFormatter(dates: string[]) {
  return (value: string) => {
    const idx = dates.indexOf(value);
    if (idx === -1) return "";
    return value.slice(0, 7);
  };
}

/** 나스닥 종가/FG 지수 위에 매수(파랑)·매도(주황) 신호를 겹쳐 그린 두 개의 단일축 차트.
 * 신호 마커는 반드시 라인과 "같은" data 배열의 컬럼으로 넣어야 카테고리 축 위치가
 * 라인과 정확히 일치한다 (Scatter에 별도의 짧은 배열을 주면 인덱스가 어긋나 점이
 * 라인 위/아래로 벗어나 보인다). */
export function SignalOverlayCharts({
  candidateId,
  timeseries,
  trades,
}: {
  candidateId: string;
  timeseries: TimeseriesPoint[];
  trades: SignalTrade[];
}) {
  const dates = timeseries.map((d) => d.date);
  const syncId = `signal-overlay-${candidateId}`;

  const buyByDate = new Map(trades.filter((t) => t.action !== "SELL_ALL").map((t) => [t.date, t]));
  const sellByDate = new Map(trades.filter((t) => t.action === "SELL_ALL").map((t) => [t.date, t]));

  const chartData = timeseries.map((row) => {
    const buy = buyByDate.get(row.date);
    const sell = sellByDate.get(row.date);
    return {
      date: row.date,
      nasdaq: row.nasdaq,
      fg: row.fg,
      buyNasdaq: buy ? buy.price : null,
      sellNasdaq: sell ? sell.price : null,
      buyFg: buy ? buy.fg : null,
      sellFg: sell ? sell.fg : null,
    };
  });

  return (
    <div className="mb-3 flex flex-col gap-3">
      <div className="rounded-md border border-black/10 p-3" style={{ background: CHART_SURFACE }}>
        <h5 className="mb-2 text-xs font-medium text-[#0b0b0b]">나스닥 종가 + 매매 신호</h5>
        <ResponsiveContainer width="100%" height={160}>
          <ComposedChart data={chartData} syncId={syncId} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid stroke={GRIDLINE} vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: INK_MUTED }}
              tickFormatter={tsTickFormatter(dates)}
              minTickGap={70}
              axisLine={{ stroke: GRIDLINE }}
              tickLine={false}
            />
            <YAxis tick={{ fontSize: 10, fill: INK_MUTED }} axisLine={false} tickLine={false} width={52} domain={["auto", "auto"]} />
            <Tooltip
              content={<SignalTooltip valueLabel="나스닥" lineKey="nasdaq" formatter={(v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 })} />}
            />
            <Line type="monotone" dataKey="nasdaq" stroke={INK_MUTED} strokeWidth={1.25} dot={false} isAnimationActive={false} />
            <Scatter dataKey="buyNasdaq" name="buy" fill={CATEGORICAL.blue} shape="circle" isAnimationActive={false} />
            <Scatter dataKey="sellNasdaq" name="sell" fill={CATEGORICAL.orange} shape="circle" isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-md border border-black/10 p-3" style={{ background: CHART_SURFACE }}>
        <h5 className="mb-2 text-xs font-medium text-[#0b0b0b]">
          Fear &amp; Greed 지수 + 매매 신호{" "}
          <span className="font-normal text-[#898781]">
            (<span style={{ color: CATEGORICAL.blue }}>●매수</span> / <span style={{ color: CATEGORICAL.orange }}>●매도</span>)
          </span>
        </h5>
        <ResponsiveContainer width="100%" height={160}>
          <ComposedChart data={chartData} syncId={syncId} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid stroke={GRIDLINE} vertical={false} />
            <ReferenceArea y1={0} y2={25} fill={EXTREME_FEAR_BAND} strokeOpacity={0} />
            <ReferenceArea y1={75} y2={100} fill={EXTREME_GREED_BAND} strokeOpacity={0} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: INK_MUTED }}
              tickFormatter={tsTickFormatter(dates)}
              minTickGap={70}
              axisLine={{ stroke: GRIDLINE }}
              tickLine={false}
            />
            <YAxis tick={{ fontSize: 10, fill: INK_MUTED }} axisLine={false} tickLine={false} width={52} domain={[0, 100]} />
            <Tooltip content={<SignalTooltip valueLabel="Fear & Greed" lineKey="fg" formatter={(v) => v.toFixed(1)} />} />
            <Line type="monotone" dataKey="fg" stroke={INK_MUTED} strokeWidth={1.25} dot={false} isAnimationActive={false} />
            <Scatter dataKey="buyFg" name="buy" fill={CATEGORICAL.blue} shape="circle" isAnimationActive={false} />
            <Scatter dataKey="sellFg" name="sell" fill={CATEGORICAL.orange} shape="circle" isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function StatRow({ label, original, rolling1y, rolling2y }: { label: string; original: number; rolling1y: number; rolling2y: number }) {
  return (
    <tr className="border-b border-black/5 last:border-0">
      <td className="px-3 py-1.5 text-[#898781]">{label}</td>
      <td className="px-3 py-1.5 text-[#0b0b0b]">{pct(original)}</td>
      <td className="px-3 py-1.5 text-[#0b0b0b]">{pct(rolling1y)}</td>
      <td className="px-3 py-1.5 text-[#0b0b0b]">{pct(rolling2y)}</td>
    </tr>
  );
}

export function CandidatePanel({ candidate, timeseries }: { candidate: SignalCandidate; timeseries: TimeseriesPoint[] }) {
  const color = CANDIDATE_COLORS[candidate.id] ?? INK_PRIMARY;
  const { params, currentStatus, summary, trades } = candidate;

  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <h4 className="mb-1 text-sm font-medium" style={{ color }}>
        {candidate.label}
      </h4>
      <p className="mb-3 text-xs text-[#898781]">
        초기 {(params.initial_allocation * 100).toFixed(0)}%({params.ramp_days}일) &middot; 추가매수{" "}
        {(params.buy_step * 100).toFixed(0)}%씩 {params.buy_interval_days}일마다 &middot; 재진입/매도{" "}
        {params.resell_level} &middot; 급락전량매수 {params.crash_level}
      </p>

      <div
        className="mb-3 rounded-md border p-3 text-xs"
        style={{ borderColor: `${color}40`, background: `${color}0d` }}
      >
        <div className="font-medium" style={{ color: INK_PRIMARY }}>
          현재 상태 (비중 {(currentStatus.currentWeight * 100).toFixed(0)}%)
        </div>
        <div className="mt-1" style={{ color: INK_SECONDARY }}>
          {currentStatus.hint}
        </div>
        {currentStatus.lastTrade && (
          <div className="mt-1" style={{ color: INK_SECONDARY }}>
            최근 신호: {currentStatus.lastTrade.date} — {ACTION_KO[currentStatus.lastTrade.action]} (FG{" "}
            {currentStatus.lastTrade.fg}, 가격 {currentStatus.lastTrade.price.toLocaleString()})
          </div>
        )}
      </div>

      <table className="mb-3 w-full text-xs">
        <thead>
          <tr className="border-b border-black/10 text-left text-[#898781]">
            <th className="px-3 py-1.5 font-medium"></th>
            <th className="px-3 py-1.5 font-medium">원본(전체기간)</th>
            <th className="px-3 py-1.5 font-medium">롤링 1년 평균</th>
            <th className="px-3 py-1.5 font-medium">롤링 2년 평균</th>
          </tr>
        </thead>
        <tbody>
          <StatRow label="수익률" original={summary.original.total_return} rolling1y={summary.rolling1y.mean} rolling2y={summary.rolling2y.mean} />
          <StatRow
            label="최악의 경우"
            original={summary.original.max_drawdown}
            rolling1y={summary.rolling1y.worst}
            rolling2y={summary.rolling2y.worst}
          />
        </tbody>
      </table>

      <SignalOverlayCharts candidateId={candidate.id} timeseries={timeseries} trades={trades} />

      <div className="text-xs text-[#898781]">
        매매 신호와 포지션 전체 ({trades.length}건) &middot; 롤링 승률(BnH 대비) 1년{" "}
        {(summary.rolling1y.winRateVsBenchmark * 100).toFixed(0)}% / 2년{" "}
        {(summary.rolling2y.winRateVsBenchmark * 100).toFixed(0)}%
      </div>
      <div className="mt-2 max-h-64 overflow-y-auto rounded-md border border-black/10">
        <table className="w-full text-xs">
          <thead className="sticky top-0" style={{ background: CHART_SURFACE }}>
            <tr className="border-b border-black/10 text-left text-[#898781]">
              <th className="px-3 py-1.5 font-medium">날짜</th>
              <th className="px-3 py-1.5 font-medium">신호</th>
              <th className="px-3 py-1.5 font-medium">FG</th>
              <th className="px-3 py-1.5 font-medium">가격</th>
              <th className="px-3 py-1.5 font-medium">비중변화</th>
              <th className="px-3 py-1.5 font-medium">포지션(비중)</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => (
              <tr key={`${t.date}-${i}`} className="border-b border-black/5 last:border-0">
                <td className="px-3 py-1 text-[#0b0b0b]">{t.date}</td>
                <td className="px-3 py-1 font-medium" style={{ color: ACTION_COLOR[t.action] }}>
                  {ACTION_KO[t.action]}
                </td>
                <td className="px-3 py-1 text-[#0b0b0b]">{t.fg}</td>
                <td className="px-3 py-1 text-[#0b0b0b]">{t.price.toLocaleString()}</td>
                <td className="px-3 py-1 text-[#0b0b0b]">{t.pctOfPortfolio !== null ? `+${(t.pctOfPortfolio * 100).toFixed(0)}%p` : "전량"}</td>
                <td className="px-3 py-1 font-medium text-[#0b0b0b]">{(t.resultingWeight * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
