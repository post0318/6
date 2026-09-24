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
import type { KospiCandidate, KospiExperiment, KospiTimeseriesPoint, SignalTrade } from "@/lib/types";
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

// Buy&Hold=orange 관례를 따르고, 후보는 팔레트 순서대로 최대 4개(H/I/J/K)까지 배정.
const BUY_HOLD_COLOR = CATEGORICAL.orange;
const CANDIDATE_COLOR_ORDER = [CATEGORICAL.blue, CATEGORICAL.aqua, CATEGORICAL.violet, CATEGORICAL.green];

const ACTION_KO: Record<SignalTrade["action"], string> = {
  RAMP_BUY: "초기램프 매수",
  WEEKLY_BUY: "정기 매수",
  CRASH_FULL_BUY: "급락 전량매수",
  SELL_ALL: "전량매도",
  SELL_HALF: "절반 매도",
  TREND_CUT: "추세 보험 축소",
  TREND_RESTORE: "추세 보험 복원",
  CRASH_HALF_BUY: "급락 절반매수",
};

const ACTION_COLOR: Record<SignalTrade["action"], string> = {
  RAMP_BUY: CATEGORICAL.blue,
  WEEKLY_BUY: CATEGORICAL.blue,
  CRASH_FULL_BUY: CATEGORICAL.aqua,
  SELL_ALL: CATEGORICAL.orange,
  SELL_HALF: CATEGORICAL.orange,
  TREND_CUT: CATEGORICAL.orange,
  TREND_RESTORE: CATEGORICAL.blue,
  CRASH_HALF_BUY: CATEGORICAL.aqua,
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

function priceLabel(exp: KospiExperiment): string {
  return exp.id === "cnn_kospi200" ? "코스피200" : "코스피";
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

/** 코스피/코스피200 종가·FG 지수 위에 매수(파랑)·매도(주황) 신호를 겹쳐 그린다.
 * SignalCandidates.tsx의 SignalOverlayCharts와 동일한 방식이나, 나스닥 전용 timeseries
 * 대신 이 실험 자신의 (date, fg, price) 시계열을 쓴다. */
function KospiSignalOverlayCharts({
  candidateId,
  timeseries,
  trades,
  priceLabel: label,
}: {
  candidateId: string;
  timeseries: KospiTimeseriesPoint[];
  trades: SignalTrade[];
  priceLabel: string;
}) {
  const dates = timeseries.map((d) => d.date);
  const syncId = `kospi-signal-overlay-${candidateId}`;

  const isSell = (a: SignalTrade["action"]) => a === "SELL_ALL" || a === "SELL_HALF" || a === "TREND_CUT";
  const buyByDate = new Map(trades.filter((t) => !isSell(t.action)).map((t) => [t.date, t]));
  const sellByDate = new Map(trades.filter((t) => isSell(t.action)).map((t) => [t.date, t]));

  const chartData = timeseries.map((row) => {
    const buy = buyByDate.get(row.date);
    const sell = sellByDate.get(row.date);
    return {
      date: row.date,
      price: row.price,
      fg: row.fg,
      buyPrice: buy ? buy.price : null,
      sellPrice: sell ? sell.price : null,
      buyFg: buy ? buy.fg : null,
      sellFg: sell ? sell.fg : null,
    };
  });

  return (
    <div className="mb-3 flex flex-col gap-3">
      <div className="rounded-md border border-black/10 p-3" style={{ background: CHART_SURFACE }}>
        <h5 className="mb-2 text-xs font-medium text-[#0b0b0b]">{label} 종가 + 매매 신호</h5>
        <ResponsiveContainer width="100%" height={160}>
          <ComposedChart data={chartData} syncId={syncId} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid stroke={GRIDLINE} vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: INK_MUTED }}
              tickFormatter={tickFormatter(dates)}
              minTickGap={70}
              axisLine={{ stroke: GRIDLINE }}
              tickLine={false}
            />
            <YAxis tick={{ fontSize: 10, fill: INK_MUTED }} axisLine={false} tickLine={false} width={52} domain={["auto", "auto"]} />
            <Tooltip
              content={<SignalTooltip valueLabel={label} lineKey="price" formatter={(v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 })} />}
            />
            <Line type="monotone" dataKey="price" stroke={INK_MUTED} strokeWidth={1.25} dot={false} isAnimationActive={false} />
            <Scatter dataKey="buyPrice" name="buy" fill={CATEGORICAL.blue} shape="circle" isAnimationActive={false} />
            <Scatter dataKey="sellPrice" name="sell" fill={CATEGORICAL.orange} shape="circle" isAnimationActive={false} />
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
              tickFormatter={tickFormatter(dates)}
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

function KospiCandidatePanel({
  candidate,
  color,
  timeseries,
  label,
}: {
  candidate: KospiCandidate;
  color: string;
  timeseries: KospiTimeseriesPoint[];
  label: string;
}) {
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
        {params.sell_fraction !== undefined && params.sell_fraction < 1 ? ` · 매도는 보유분의 ${params.sell_fraction * 100}%씩` : ""}
        {params.trend_ma !== undefined && params.trend_buffer !== undefined && params.trend_cap !== undefined
          ? ` · 추세 보험: ${label}이 ${params.trend_ma}일선 -${params.trend_buffer * 100}% 아래면 비중 ${params.trend_cap * 100}%로 축소, ${params.trend_ma}일선 회복 시 복원`
          : ""}
      </p>

      <div className="mb-3 rounded-md border p-3 text-xs" style={{ borderColor: `${color}40`, background: `${color}0d` }}>
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

      <div className="mb-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <div>
          <div className="text-[#898781]">총수익률</div>
          <div className="font-medium text-[#0b0b0b]">{pct(summary.total_return)}</div>
        </div>
        <div>
          <div className="text-[#898781]">CAGR</div>
          <div className="font-medium text-[#0b0b0b]">{pct(summary.cagr)}</div>
        </div>
        <div>
          <div className="text-[#898781]">MDD</div>
          <div className="font-medium text-[#0b0b0b]">{pct(summary.max_drawdown)}</div>
        </div>
        <div>
          <div className="text-[#898781]">Sharpe-like</div>
          <div className="font-medium text-[#0b0b0b]">{summary.sharpe_like.toFixed(3)}</div>
        </div>
      </div>

      <KospiSignalOverlayCharts candidateId={candidate.id} timeseries={timeseries} trades={trades} priceLabel={label} />

      <div className="text-xs text-[#898781]">매매 신호와 포지션 전체 ({trades.length}건)</div>
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
                <td className="px-3 py-1 text-[#0b0b0b]">
                  {t.action === "SELL_ALL"
                    ? "전량"
                    : t.pctOfPortfolio === null
                      ? "-"
                      : `${t.action === "SELL_HALF" || t.action === "TREND_CUT" ? "-" : "+"}${(t.pctOfPortfolio * 100).toFixed(0)}%p`}
                </td>
                <td className="px-3 py-1 font-medium text-[#0b0b0b]">{(t.resultingWeight * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function KospiExperimentCard({ exp }: { exp: KospiExperiment }) {
  const label = priceLabel(exp);
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-black/10 p-4">
      <h3 className="text-base font-semibold text-[#0b0b0b]">{exp.label}</h3>
      <p className="text-xs text-[#52514e]">{exp.caveat}</p>
      <KospiSummaryTable exp={exp} />
      <KospiEquityChart exp={exp} />
      {exp.candidates.map((c, i) => (
        <KospiCandidatePanel
          key={c.id}
          candidate={c}
          color={CANDIDATE_COLOR_ORDER[i % CANDIDATE_COLOR_ORDER.length]}
          timeseries={exp.timeseries}
          label={label}
        />
      ))}
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
