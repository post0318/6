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
import type { BacktestData, BacktestEquityPoint } from "@/lib/types";
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
      {strat && (
        <div style={{ color: CATEGORICAL.blue }}>전략: {strat.value.toFixed(1)}</div>
      )}
      {bench && (
        <div style={{ color: CATEGORICAL.orange }}>Buy&amp;Hold: {bench.value.toFixed(1)}</div>
      )}
    </div>
  );
}

function StatTile({ label, strat, bench, format = pct }: { label: string; strat: number; bench: number; format?: (v: number) => string }) {
  const stratBetter = strat > bench;
  return (
    <div className="rounded-lg border border-black/10 p-3" style={{ background: CHART_SURFACE }}>
      <div className="text-[11px] text-[var(--ink-muted)]">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span
          className="text-base font-semibold"
          style={{ color: stratBetter ? CATEGORICAL.blue : INK_PRIMARY }}
        >
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

export function BacktestChart({ backtest }: { backtest: BacktestData }) {
  const { strategy, benchmark, params, pctDaysInMarket, numTrades, equityCurve } = backtest;
  const dates = equityCurve.map((d: BacktestEquityPoint) => d.date);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="총수익률" strat={strategy.total_return} bench={benchmark.total_return} />
        <StatTile label="CAGR (연환산)" strat={strategy.cagr} bench={benchmark.cagr} />
        <StatTile label="최대낙폭 (MDD)" strat={strategy.max_drawdown} bench={benchmark.max_drawdown} />
        <StatTile
          label="변동성 (연환산)"
          strat={strategy.annualized_vol}
          bench={benchmark.annualized_vol}
        />
      </div>

      <p className="text-xs text-[#898781]">
        규칙: FG &le; {params.buyThreshold} 이면 전량매수, FG &ge; {params.sellThreshold} 이면 전량매도.
        현금 보유 구간은 무이자(0%) 가정, 거래비용 미반영. 전체 기간 중 주식 보유 비중{" "}
        {pct(pctDaysInMarket)}, 총 거래 {numTrades}회(매수 {Math.ceil(numTrades / 2)}회 · 매도{" "}
        {Math.floor(numTrades / 2)}회).
      </p>

      <div className="rounded-lg border border-black/10 p-4" style={{ background: CHART_SURFACE }}>
        <h4 className="mb-1 text-sm font-medium text-[#0b0b0b]">
          전략 vs Buy&amp;Hold 자산가치 (시작값 100 기준)
        </h4>
        <p className="mb-3 text-xs text-[#898781]">
          매수 시점에 전량 매수, 매도 시점에 전량 현금화(무이자) 후 재진입을 반복
        </p>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={equityCurve} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
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
              domain={["auto", "auto"]}
            />
            <Tooltip content={<EquityTooltip />} />
            <Legend
              formatter={(value) => (value === "strategy" ? "전략 (FG 임계값)" : "Buy & Hold")}
              wrapperStyle={{ fontSize: 12 }}
            />
            <Line
              type="monotone"
              dataKey="benchmark"
              name="benchmark"
              stroke={CATEGORICAL.orange}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="strategy"
              name="strategy"
              stroke={CATEGORICAL.blue}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
