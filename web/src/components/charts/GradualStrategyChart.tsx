"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { GradualBacktestData, GradualEquityPoint } from "@/lib/types";
import { CATEGORICAL, CHART_SURFACE, GRIDLINE, INK_MUTED, INK_PRIMARY, INK_SECONDARY } from "@/lib/palette";

function pct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
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
  const strat = payload.find((p) => p.dataKey === "strategy");
  const bench = payload.find((p) => p.dataKey === "benchmark");
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="text-[#898781]">{label}</div>
      {strat && <div style={{ color: CATEGORICAL.blue }}>전략: {strat.value.toFixed(1)}</div>}
      {bench && <div style={{ color: CATEGORICAL.orange }}>Buy&amp;Hold: {bench.value.toFixed(1)}</div>}
    </div>
  );
}

function WeightTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-md border border-black/10 bg-white px-3 py-2 text-xs shadow-sm">
      <div className="text-[#898781]">{label}</div>
      <div style={{ color: CATEGORICAL.blue }}>주식 비중: {(payload[0].value * 100).toFixed(0)}%</div>
    </div>
  );
}

function StatTile({
  label,
  strat,
  bench,
  format = pct,
}: {
  label: string;
  strat: number;
  bench: number;
  format?: (v: number) => string;
}) {
  const stratBetter = strat > bench;
  return (
    <div className="rounded-lg border border-black/10 p-3" style={{ background: CHART_SURFACE }}>
      <div className="text-[11px] text-[#898781]">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-base font-semibold" style={{ color: stratBetter ? CATEGORICAL.blue : INK_PRIMARY }}>
          {format(strat)}
        </span>
        <span className="text-[11px]" style={{ color: INK_SECONDARY }}>
          전략
        </span>
      </div>
      <div className="mt-0.5 flex items-baseline gap-2">
        <span className="text-sm" style={{ color: !stratBetter ? CATEGORICAL.orange : INK_SECONDARY }}>
          {format(bench)}
        </span>
        <span className="text-[11px]" style={{ color: INK_MUTED }}>
          Buy&amp;Hold
        </span>
      </div>
    </div>
  );
}

export function GradualStrategyChart({ backtest }: { backtest: GradualBacktestData }) {
  const { strategy, benchmark, params, numTrades, tradeCounts, equityCurve } = backtest;
  const dates = equityCurve.map((d: GradualEquityPoint) => d.date);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="총수익률" strat={strategy.total_return} bench={benchmark.total_return} />
        <StatTile label="CAGR (연환산)" strat={strategy.cagr} bench={benchmark.cagr} />
        <StatTile label="최대낙폭 (MDD)" strat={strategy.max_drawdown} bench={benchmark.max_drawdown} />
        <StatTile label="변동성 (연환산)" strat={strategy.annualized_vol} bench={benchmark.annualized_vol} />
      </div>

      <p className="text-xs text-[#898781]">
        규칙: 첫 {params.rampDays}거래일 동안 매일 {params.rampDailyStep * 100}%p씩(지수 무관)
        편입해 30% 도달 &rarr; 이후 FG가 {params.resellLevel} 이상이면 전량매도, {params.resellLevel}{" "}
        밑이면 매수 진행 모드로 매주 수요일 {params.weeklyStep * 100}%p씩 추가 매수(다시{" "}
        {params.resellLevel}을 넘으면 매도, 밑돌면 재개하는 사이클 반복) &rarr; 매수 진행 중
        FG가 {params.crashFullBuy} 밑이면 즉시 100% 전량매수 후 다음 매도 신호까지 보유.
        현금은 무이자, 거래비용 미반영. 총 거래 {numTrades}회 (초기램프{" "}
        {params.rampDays} · 주간매수 {tradeCounts.WEEKLY_BUY ?? 0} · 전량매도{" "}
        {tradeCounts.SELL_ALL ?? 0} · 급락전량매수 {tradeCounts.CRASH_FULL_BUY ?? 0}).
      </p>

      <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
        <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">
          전략 vs Buy&amp;Hold 자산가치 (시작값 100 기준)
        </h4>
        <p className="mb-3 text-xs text-[#898781]">
          30% 초기 편입 후 조건에 따라 점진적으로 비중을 늘렸다 줄였다 반복
        </p>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={equityCurve} syncId="gradual-sync" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
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
            <Tooltip content={<EquityTooltip />} />
            <Legend
              formatter={(value) => (value === "strategy" ? "전략 (30% 시작 + 계단식 매수)" : "Buy & Hold")}
              wrapperStyle={{ fontSize: 12 }}
            />
            <Line type="monotone" dataKey="benchmark" name="benchmark" stroke={CATEGORICAL.orange} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="strategy" name="strategy" stroke={CATEGORICAL.blue} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
        <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">실제 주식 비중 추이</h4>
        <p className="mb-3 text-xs text-[#898781]">
          가격 변동으로 매수 시점 사이에도 비중이 자연스럽게 오르내림 (0~100%)
        </p>
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={equityCurve} syncId="gradual-sync" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
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
              width={48}
              domain={[0, 1]}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip content={<WeightTooltip />} />
            <Area
              type="stepAfter"
              dataKey="weight"
              stroke={CATEGORICAL.blue}
              fill={CATEGORICAL.blue}
              fillOpacity={0.15}
              strokeWidth={1.5}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
