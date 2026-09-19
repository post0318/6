"use client";

import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HorizonKey, HorizonMeta, Hypothesis1Stat, Hypothesis2Stat } from "@/lib/types";
import { CATEGORICAL, CHART_SURFACE, GRIDLINE, INK_MUTED } from "@/lib/palette";

function pct(v: number | null) {
  return v !== null ? (v * 100).toFixed(2) + "%" : "-";
}

type TooltipRow = { payload: Record<string, number | string | null> };

function makeTooltip(labelA: string, labelB: string, nKeyA: string, nKeyB: string) {
  return function HypTooltip(props: {
    active?: boolean;
    payload?: readonly unknown[];
    label?: ReactNode;
  }) {
    const { active, payload, label } = props;
    if (!active || !payload || payload.length === 0) return null;
    const p = (payload[0] as TooltipRow).payload;
    return (
      <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
        <div className="mb-1 font-medium text-[#0b0b0b]">{label}</div>
        <div style={{ color: CATEGORICAL.blue }}>
          {labelA}: {pct(p.a as number | null)} (n={String(p[nKeyA] ?? "-")})
        </div>
        <div style={{ color: CATEGORICAL.orange }}>
          {labelB}: {pct(p.b as number | null)} (n={String(p[nKeyB] ?? "-")})
        </div>
      </div>
    );
  };
}

function labelFormatter(v: unknown) {
  const n = typeof v === "number" ? v : Number(v);
  if (v === undefined || v === null || Number.isNaN(n)) return "";
  return `${(n * 100).toFixed(1)}%`;
}

export function Hypothesis1Chart({
  data,
  horizons,
}: {
  data: Record<HorizonKey, Hypothesis1Stat>;
  horizons: HorizonMeta[];
}) {
  const chartData = horizons.map((h) => {
    const s = data[h.key];
    return {
      horizonKo: h.ko,
      a: s?.reboundingMean ?? null,
      b: s?.stillFallingMean ?? null,
      nA: s?.reboundingN ?? null,
      nB: s?.stillFallingN ?? null,
    };
  });

  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">
        가설1: 극단적 공포 중 &quot;반등 중&quot; vs &quot;계속 하락 중&quot;
      </h4>
      <p className="mb-3 text-xs text-[#898781]">
        극단적 공포(FG&lt;25) 구간을 5일 전 대비 FG 변화로 나눠 이후 수익률 비교
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 16, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <XAxis dataKey="horizonKo" tick={{ fontSize: 11, fill: INK_MUTED }} axisLine={{ stroke: GRIDLINE }} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11, fill: INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={48}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip content={makeTooltip("반등 중", "계속 하락 중", "nA", "nB")} />
          <Legend
            formatter={(value) => (value === "a" ? "반등 중 (FG 5일 전보다 상승)" : "계속 하락 중")}
            wrapperStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="a" name="a" fill={CATEGORICAL.blue} radius={[3, 3, 0, 0]} isAnimationActive={false}>
            <LabelList dataKey="a" position="top" formatter={labelFormatter} style={{ fontSize: 10, fill: "#52514e" }} />
          </Bar>
          <Bar dataKey="b" name="b" fill={CATEGORICAL.orange} radius={[3, 3, 0, 0]} isAnimationActive={false}>
            <LabelList dataKey="b" position="top" formatter={labelFormatter} style={{ fontSize: 10, fill: "#52514e" }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Hypothesis2Chart({
  data,
  horizons,
}: {
  data: Record<HorizonKey, Hypothesis2Stat>;
  horizons: HorizonMeta[];
}) {
  const chartData = horizons.map((h) => {
    const s = data[h.key];
    return {
      horizonKo: h.ko,
      a: s?.persistentMean ?? null,
      b: s?.restMean ?? null,
      nA: s?.persistentN ?? null,
      nB: s?.restN ?? null,
    };
  });

  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">
        가설2: &quot;극단적 탐욕 10일 이상 지속&quot; vs &quot;나머지&quot;
      </h4>
      <p className="mb-3 text-xs text-[#898781]">
        extreme greed가 10일 이상 연속된 시점 이후 수익률 vs 그 외 전체 기간
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 16, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <XAxis dataKey="horizonKo" tick={{ fontSize: 11, fill: INK_MUTED }} axisLine={{ stroke: GRIDLINE }} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11, fill: INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={48}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip content={makeTooltip("탐욕 10일+ 지속", "나머지 기간", "nA", "nB")} />
          <Legend
            formatter={(value) => (value === "a" ? "탐욕 10일 이상 지속" : "나머지 기간")}
            wrapperStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="a" name="a" fill={CATEGORICAL.blue} radius={[3, 3, 0, 0]} isAnimationActive={false}>
            <LabelList dataKey="a" position="top" formatter={labelFormatter} style={{ fontSize: 10, fill: "#52514e" }} />
          </Bar>
          <Bar dataKey="b" name="b" fill={CATEGORICAL.orange} radius={[3, 3, 0, 0]} isAnimationActive={false}>
            <LabelList dataKey="b" position="top" formatter={labelFormatter} style={{ fontSize: 10, fill: "#52514e" }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
