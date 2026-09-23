"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { KospiCandidate, KospiExperiment } from "@/lib/types";
import { CATEGORICAL, CHART_SURFACE, GRIDLINE, INK_MUTED } from "@/lib/palette";

// Buy&Hold=orange 관례를 따르고, 후보는 팔레트 순서대로 최대 4개(H/I/J/K)까지 배정.
const BUY_HOLD_COLOR = CATEGORICAL.orange;
const CANDIDATE_COLOR_ORDER = [CATEGORICAL.blue, CATEGORICAL.aqua, CATEGORICAL.violet, CATEGORICAL.green];

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

function buildChartRows(exp: KospiExperiment) {
  const keyed: Record<string, Record<string, number>> = {};
  for (const p of exp.buyHoldEquityCurve) {
    keyed[p.date] = { buyHold: p.equity };
  }
  for (const c of exp.candidates) {
    for (const p of c.equityCurve) {
      keyed[p.date] = { ...(keyed[p.date] ?? {}), [c.id]: p.equity };
    }
  }
  return Object.entries(keyed)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, vals]) => ({ date, ...vals }));
}

function EquityTooltip({
  active,
  payload,
  label,
  candidates,
}: {
  active?: boolean;
  payload?: { value: number; dataKey: string }[];
  label?: string;
  candidates: KospiCandidate[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const series = [{ id: "buyHold", label: "Buy & Hold", color: BUY_HOLD_COLOR }, ...candidates.map((c, i) => ({
    id: c.id,
    label: `후보 ${c.id}`,
    color: CANDIDATE_COLOR_ORDER[i % CANDIDATE_COLOR_ORDER.length],
  }))];
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 text-[#898781]">{label}</div>
      {series.map((s) => {
        const p = payload.find((x) => x.dataKey === s.id);
        if (!p) return null;
        return (
          <div key={s.id} style={{ color: s.color }}>
            {s.label}: {p.value.toFixed(1)}
          </div>
        );
      })}
    </div>
  );
}

function KospiSummaryTable({ exp }: { exp: KospiExperiment }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-black/10" style={{ background: CHART_SURFACE }}>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-black/10 text-left text-[#898781]">
            <th className="px-3 py-2 font-medium">전략</th>
            <th className="px-3 py-2 font-medium">총수익률</th>
            <th className="px-3 py-2 font-medium">CAGR</th>
            <th className="px-3 py-2 font-medium">MDD</th>
            <th className="px-3 py-2 font-medium">변동성</th>
            <th className="px-3 py-2 font-medium">Sharpe-like</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-black/5">
            <td className="px-3 py-2 font-medium" style={{ color: BUY_HOLD_COLOR }}>
              Buy &amp; Hold
            </td>
            <td className="px-3 py-2 text-[#0b0b0b]" colSpan={4}>
              (아래 후보들과 같은 차트의 기준선)
            </td>
          </tr>
          {exp.candidates.map((c, i) => (
            <tr key={c.id} className="border-b border-black/5 last:border-0">
              <td
                className="px-3 py-2 font-medium"
                style={{ color: CANDIDATE_COLOR_ORDER[i % CANDIDATE_COLOR_ORDER.length] }}
              >
                {c.label}
              </td>
              <td className="px-3 py-2 text-[#0b0b0b]">{pct(c.summary.total_return)}</td>
              <td className="px-3 py-2 text-[#0b0b0b]">{pct(c.summary.cagr)}</td>
              <td className="px-3 py-2 text-[#0b0b0b]">{pct(c.summary.max_drawdown)}</td>
              <td className="px-3 py-2 text-[#0b0b0b]">{(c.summary.annualized_vol * 100).toFixed(1)}%</td>
              <td className="px-3 py-2 text-[#0b0b0b]">{c.summary.sharpe_like.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KospiEquityChart({ exp }: { exp: KospiExperiment }) {
  const rows = buildChartRows(exp);
  const dates = rows.map((r) => r.date);

  return (
    <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
      <h4 className="mb-3 text-sm font-medium text-[#0b0b0b]">
        자산가치 (시작값 100 기준), {exp.dateRange.start} ~ {exp.dateRange.end}
      </h4>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={rows} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
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
          <Tooltip content={<EquityTooltip candidates={exp.candidates} />} />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(v) => (v === "buyHold" ? "Buy & Hold" : `후보 ${v}`)}
          />
          <Line
            type="monotone"
            dataKey="buyHold"
            name="buyHold"
            stroke={BUY_HOLD_COLOR}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          {exp.candidates.map((c, i) => (
            <Line
              key={c.id}
              type="monotone"
              dataKey={c.id}
              name={c.id}
              stroke={CANDIDATE_COLOR_ORDER[i % CANDIDATE_COLOR_ORDER.length]}
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

export function KospiExperimentCard({ exp }: { exp: KospiExperiment }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-black/10 p-4">
      <h3 className="text-base font-semibold text-[#0b0b0b]">{exp.label}</h3>
      <p className="text-xs text-[#52514e]">{exp.caveat}</p>
      <KospiSummaryTable exp={exp} />
      <KospiEquityChart exp={exp} />
    </div>
  );
}

export function KospiSection({ experiments }: { experiments: KospiExperiment[] }) {
  return (
    <div className="flex flex-col gap-6">
      {experiments.map((exp) => (
        <KospiExperimentCard key={exp.id} exp={exp} />
      ))}
    </div>
  );
}
