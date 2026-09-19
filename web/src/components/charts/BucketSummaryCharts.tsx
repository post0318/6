"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { BucketSummaryEntry, HorizonMeta, RatingMeta } from "@/lib/types";
import { CHART_SURFACE, GRIDLINE, INK_MUTED, SEQUENTIAL_ORDINAL_5 } from "@/lib/palette";

function BucketTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: { ratingKo: string; mean: number | null; n: number | null } }[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="font-medium text-[#0b0b0b]">{p.ratingKo}</div>
      <div className="text-[#52514e]">
        평균 수익률: {p.mean !== null ? (p.mean * 100).toFixed(2) + "%" : "-"}
      </div>
      <div className="text-[#898781]">n = {p.n ?? "-"}</div>
    </div>
  );
}

export function BucketSummaryCharts({
  bucketSummary,
  ratingOrder,
  horizons,
}: {
  bucketSummary: Record<string, BucketSummaryEntry>;
  ratingOrder: RatingMeta[];
  horizons: HorizonMeta[];
}) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {horizons.map((h) => {
        const chartData = ratingOrder.map((r) => {
          const stat = bucketSummary[r.key]?.byHorizon[h.key];
          return {
            ratingKo: r.ko,
            mean: stat?.mean ?? null,
            n: stat?.n ?? null,
          };
        });
        return (
          <div
            key={h.key}
            className="rounded-lg border border-black/10 p-3"
            style={{ background: CHART_SURFACE }}
          >
            <h5 className="mb-2 text-xs font-medium text-[#0b0b0b]">{h.ko} 이후 평균 수익률</h5>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke={GRIDLINE} vertical={false} />
                <XAxis
                  dataKey="ratingKo"
                  tick={{ fontSize: 9, fill: INK_MUTED }}
                  axisLine={{ stroke: GRIDLINE }}
                  tickLine={false}
                  interval={0}
                  angle={-20}
                  textAnchor="end"
                  height={40}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: INK_MUTED }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                  tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                />
                <Tooltip content={<BucketTooltip />} />
                <Bar dataKey="mean" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={SEQUENTIAL_ORDINAL_5[i]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}
