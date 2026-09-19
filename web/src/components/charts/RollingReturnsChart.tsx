"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RollingSeriesPoint } from "@/lib/types";
import { CATEGORICAL, CHART_SURFACE, GRIDLINE, INK_MUTED, INK_PRIMARY } from "@/lib/palette";

const SERIES: { key: keyof Omit<RollingSeriesPoint, "date">; label: string; color: string; dash?: string }[] = [
  { key: "buyHold", label: "Buy & Hold", color: CATEGORICAL.orange },
  { key: "A", label: "후보 A", color: CATEGORICAL.blue },
  { key: "B", label: "후보 B", color: CATEGORICAL.aqua },
  { key: "C", label: "후보 C", color: CATEGORICAL.yellow },
  { key: "D", label: "후보 D", color: CATEGORICAL.magenta },
  { key: "E", label: "후보 E", color: CATEGORICAL.green },
  { key: "F", label: "후보 F", color: CATEGORICAL.violet },
  { key: "G", label: "후보 G", color: CATEGORICAL.red },
  { key: "H", label: "후보 H (F/79/31)", color: INK_PRIMARY, dash: "6 3" },
];

function tickFormatter(dates: string[]) {
  return (value: string) => {
    const idx = dates.indexOf(value);
    if (idx === -1) return "";
    return value.slice(0, 7);
  };
}

function RollingTooltip({
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
      <div className="mb-1 text-[#898781]">{label} 기준 직전 구간 수익률</div>
      {SERIES.map((s) => {
        const p = payload.find((x) => x.dataKey === s.key);
        if (!p) return null;
        return (
          <div key={s.key} style={{ color: s.color }}>
            {s.label}: {(p.value * 100).toFixed(1)}%
          </div>
        );
      })}
    </div>
  );
}

export function RollingReturnsChart({
  series,
  horizonLabel,
}: {
  series: RollingSeriesPoint[];
  horizonLabel: string;
}) {
  const dates = series.map((d) => d.date);
  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">롤링 {horizonLabel} 수익률 추이</h4>
      <p className="mb-3 text-xs text-[#898781]">
        각 날짜를 기준으로 직전 {horizonLabel}간의 수익률. 0% 아래로 내려가면 그 구간은 손실.
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={series} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <ReferenceLine y={0} stroke={INK_MUTED} strokeDasharray="4 4" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: INK_MUTED }}
            tickFormatter={tickFormatter(dates)}
            minTickGap={60}
            axisLine={{ stroke: GRIDLINE }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={52}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip content={<RollingTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v) => SERIES.find((s) => s.key === v)?.label ?? String(v)} />
          {SERIES.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.key}
              stroke={s.color}
              strokeWidth={1.75}
              strokeDasharray={s.dash}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
