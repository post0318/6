"use client";

import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HorizonKey, HorizonMeta } from "@/lib/types";
import { BASELINE, CHART_SURFACE, DIVERGING, GRIDLINE, INK_MUTED } from "@/lib/palette";

function CorrTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: { horizonKo: string; value: number | null } }[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="font-medium text-[#0b0b0b]">{p.horizonKo}</div>
      <div className="text-[#52514e]">상관계수: {p.value !== null ? p.value.toFixed(3) : "-"}</div>
    </div>
  );
}

export function CorrelationChart({
  correlation,
  horizons,
}: {
  correlation: Record<HorizonKey, number | null>;
  horizons: HorizonMeta[];
}) {
  const chartData = horizons.map((h) => ({
    horizonKo: h.ko,
    value: correlation[h.key],
  }));

  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <XAxis
            dataKey="horizonKo"
            tick={{ fontSize: 11, fill: INK_MUTED }}
            axisLine={{ stroke: GRIDLINE }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={48}
            domain={[-0.25, 0.25]}
          />
          <ReferenceLine y={0} stroke={BASELINE} strokeWidth={1} />
          <Tooltip content={<CorrTooltip />} />
          <Bar dataKey="value" radius={[3, 3, 3, 3]} isAnimationActive={false}>
            {chartData.map((d, i) => (
              <Cell key={i} fill={(d.value ?? 0) < 0 ? DIVERGING.positive : DIVERGING.negative} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-[#898781]">
        0보다 작으면(파랑) &quot;FG 낮음(공포) → 이후 수익률 높음&quot; 방향과 일치, 0보다 크면(빨강) 반대 방향.
      </p>
    </div>
  );
}
