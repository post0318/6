"use client";

import {
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import type { TimeseriesPoint } from "@/lib/types";
import {
  CATEGORICAL,
  GRIDLINE,
  INK_MUTED,
  CHART_SURFACE,
  EXTREME_FEAR_BAND,
  EXTREME_GREED_BAND,
} from "@/lib/palette";

function TimeTooltip({
  active,
  payload,
  label,
  valueLabel,
  formatter,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
  valueLabel: string;
  formatter: (v: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const v = payload[0].value;
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="text-[var(--ink-muted)]">{label}</div>
      <div className="font-medium text-[var(--ink-primary)]">
        {valueLabel}: {formatter(v)}
      </div>
    </div>
  );
}

// 매 n번째 포인트만 x축 tick으로 표시(일별 데이터가 1500개+라 라벨이 겹치지 않도록)
function tickFormatter(dates: string[]) {
  return (value: string) => {
    const idx = dates.indexOf(value);
    if (idx === -1) return "";
    return value.slice(0, 7); // YYYY-MM
  };
}

export function NasdaqChart({ data }: { data: TimeseriesPoint[] }) {
  const dates = data.map((d) => d.date);
  return (
    <div
      className="rounded-lg border border-black/10 p-4"
      style={{ background: CHART_SURFACE }}
    >
      <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">나스닥 종합지수 종가</h4>
      <p className="mb-3 text-xs text-[#898781]">일별 종가, 2020-07 ~ 현재</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} syncId="fg-sp-sync" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
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
            width={56}
            domain={["auto", "auto"]}
          />
          <Tooltip
            content={
              <TimeTooltip
                valueLabel="나스닥"
                formatter={(v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              />
            }
          />
          <Line
            type="monotone"
            dataKey="nasdaq"
            stroke={CATEGORICAL.blue}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FearGreedChart({ data }: { data: TimeseriesPoint[] }) {
  const dates = data.map((d) => d.date);
  return (
    <div
      className="rounded-lg border border-black/10 p-4"
      style={{ background: CHART_SURFACE }}
    >
      <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">CNN Fear &amp; Greed Index</h4>
      <p className="mb-3 text-xs text-[#898781]">
        0~100, 옅은 빨강 = 극단적 공포(&lt;25) 구간 · 옅은 초록 = 극단적 탐욕(&gt;75) 구간
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} syncId="fg-sp-sync" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <ReferenceArea y1={0} y2={25} fill={EXTREME_FEAR_BAND} strokeOpacity={0} />
          <ReferenceArea y1={75} y2={100} fill={EXTREME_GREED_BAND} strokeOpacity={0} />
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
            width={56}
            domain={[0, 100]}
          />
          <Tooltip
            content={
              <TimeTooltip
                valueLabel="Fear & Greed"
                formatter={(v) => v.toFixed(1)}
              />
            }
          />
          <Line
            type="monotone"
            dataKey="fg"
            stroke={CATEGORICAL.orange}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
