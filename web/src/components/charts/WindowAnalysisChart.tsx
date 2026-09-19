"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { WindowAnalysisData, WindowEquityPoint } from "@/lib/types";
import { CATEGORICAL, CHART_SURFACE, GRIDLINE, INK_MUTED, INK_PRIMARY } from "@/lib/palette";

const SERIES: { key: keyof Omit<WindowEquityPoint, "date">; label: string; color: string }[] = [
  { key: "buyHold", label: "Buy & Hold", color: CATEGORICAL.orange },
  { key: "v1", label: "v1 (20/70 전량매매)", color: CATEGORICAL.yellow },
  { key: "v2Default", label: "v2-default (70/20)", color: CATEGORICAL.aqua },
  { key: "v2Optimal", label: "v2-optimal (최적화)", color: CATEGORICAL.blue },
];

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

function EquityTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; dataKey: string }[];
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 text-[#898781]">{label}</div>
      {SERIES.map((s) => {
        const p = payload.find((x) => x.dataKey === s.key);
        if (!p) return null;
        return (
          <div key={s.key} style={{ color: s.color }}>
            {s.label}: {p.value.toFixed(1)}
          </div>
        );
      })}
    </div>
  );
}

export function WindowSummaryTable({ data }: { data: WindowAnalysisData }) {
  const rows: { key: keyof WindowAnalysisData["summary"]; label: string }[] = [
    { key: "buyHold", label: "Buy & Hold" },
    { key: "v1", label: "v1 (20/70 전량매매)" },
    { key: "v2Default", label: "v2-default (70/20, 5일램프, 주5%)" },
    { key: "v2Optimal", label: "v2-optimal (최적화)" },
  ];

  return (
    <div className="overflow-x-auto rounded-lg border border-black/10" style={{ background: CHART_SURFACE }}>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-black/10 text-left text-[#898781]">
            <th className="px-3 py-2 font-medium">전략</th>
            <th className="px-3 py-2 font-medium">고점&rarr;저점</th>
            <th className="px-3 py-2 font-medium">고점&rarr;BnH회복일</th>
            <th className="px-3 py-2 font-medium">전체기간 총수익률</th>
            <th className="px-3 py-2 font-medium">MDD</th>
            <th className="px-3 py-2 font-medium">변동성</th>
            <th className="px-3 py-2 font-medium">Sharpe-like</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ key, label }) => {
            const s = data.summary[key];
            const color = SERIES.find((x) => x.key === key)?.color ?? INK_PRIMARY;
            return (
              <tr key={key} className="border-b border-black/5 last:border-0">
                <td className="px-3 py-2 font-medium" style={{ color }}>
                  {label}
                </td>
                <td className="px-3 py-2 text-[#0b0b0b]">{pct(s.peakToTrough)}</td>
                <td className="px-3 py-2 text-[#0b0b0b]">{pct(s.peakToRecovery)}</td>
                <td className="px-3 py-2 text-[#0b0b0b]">{pct(s.total_return)}</td>
                <td className="px-3 py-2 text-[#0b0b0b]">{pct(s.max_drawdown)}</td>
                <td className="px-3 py-2 text-[#0b0b0b]">{(s.annualized_vol * 100).toFixed(1)}%</td>
                <td className="px-3 py-2 text-[#0b0b0b]">{s.sharpe_like.toFixed(3)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function WindowEquityChart({ data }: { data: WindowAnalysisData }) {
  const dates = data.equityCurve.map((d) => d.date);
  const { peakDate, troughDate, recoveryDate } = data.window;

  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">
        전체기간 자산가치 (시작값 100 기준) — 실제 약세장 구간 표시
      </h4>
      <p className="mb-3 text-xs text-[#898781]">
        음영: {peakDate} 고점 &rarr; {troughDate} 저점(나스닥 -36.4%) · 점선: Buy&amp;Hold가
        고점을 재돌파한 {recoveryDate}
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data.equityCurve} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <ReferenceArea x1={peakDate} x2={troughDate} fill={INK_MUTED} fillOpacity={0.08} strokeOpacity={0} />
          <ReferenceLine x={recoveryDate} stroke={INK_MUTED} strokeDasharray="4 4" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: INK_MUTED }}
            tickFormatter={tickFormatter(dates)}
            minTickGap={60}
            axisLine={{ stroke: GRIDLINE }}
            tickLine={false}
          />
          <YAxis tick={{ fontSize: 11, fill: INK_MUTED }} axisLine={false} tickLine={false} width={48} domain={["auto", "auto"]} />
          <Tooltip content={<EquityTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {SERIES.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
