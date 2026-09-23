"use client";

import type { DashboardData } from "@/lib/types";
import { FearGreedChart, NasdaqChart } from "@/components/charts/TimeSeriesCharts";
import { BucketSummaryCharts } from "@/components/charts/BucketSummaryCharts";
import { CorrelationChart } from "@/components/charts/CorrelationChart";
import { Hypothesis1Chart, Hypothesis2Chart } from "@/components/charts/HypothesisCharts";
import { BacktestChart } from "@/components/charts/BacktestChart";
import { GradualStrategyChart } from "@/components/charts/GradualStrategyChart";
import { WindowEquityChart, WindowSummaryTable } from "@/components/charts/WindowAnalysisChart";
import { CandidatesEquityChart, CandidatePanel } from "@/components/charts/SignalCandidates";
import { RollingReturnsChart } from "@/components/charts/RollingReturnsChart";

const REPO_URL = "https://github.com/post0318/6";

export function Dashboard({ data }: { data: DashboardData }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <header className="mb-10">
        <h1 className="text-2xl font-semibold text-[#0b0b0b] sm:text-3xl">
          Fear &amp; Greed 역발상 투자 리서치 — Project 6
        </h1>
        <p className="mt-2 text-sm text-[#52514e]">
          CNN Fear &amp; Greed Index가 나스닥 종합지수 투자의 역발상(contrarian) 신호로
          쓸모가 있는지 살펴보는 개인 리서치 대시보드입니다.
        </p>
        <div className="mt-4 rounded-lg border border-[#e34948]/30 bg-[#e34948]/5 p-3 text-xs text-[#52514e]">
          <span className="font-medium text-[#0b0b0b]">⚠ 표본 한계 안내: </span>
          {data.meta.sampleCaveat}
        </div>
        <p className="mt-3 text-xs text-[#898781]">
          데이터 기간: {data.meta.dateRange.start} ~ {data.meta.dateRange.end} · {" "}
          <a href={REPO_URL} className="underline hover:text-[#2a78d6]" target="_blank" rel="noreferrer">
            GitHub 저장소
          </a>
        </p>
      </header>

      <section className="mb-12">
        <h2 className="mb-3 text-lg font-semibold text-[#0b0b0b]">시계열: FG 지수 vs 나스닥</h2>
        <div className="flex flex-col gap-4">
          <NasdaqChart data={data.timeseries} />
          <FearGreedChart data={data.timeseries} />
        </div>
      </section>

      <section className="mb-12">
        <h2 className="mb-1 text-lg font-semibold text-[#0b0b0b]">
          FG 등급별 이후 평균 수익률
        </h2>
        <p className="mb-3 text-xs text-[#898781]">
          진입 시점의 FG 등급에 따라 이후 각 기간의 평균 forward return이 어떻게 다른지 (막대에
          마우스를 올리면 표본 수 n 확인 가능)
        </p>
        <BucketSummaryCharts
          bucketSummary={data.bucketSummary}
          ratingOrder={data.ratingOrder}
          horizons={data.horizons}
        />
      </section>

      <section className="mb-12">
        <h2 className="mb-1 text-lg font-semibold text-[#0b0b0b]">
          FG 수준 vs 이후 수익률 상관계수
        </h2>
        <p className="mb-3 text-xs text-[#898781]">
          기간별로 FG 지수 수준과 forward return의 상관계수. 음수면 &quot;공포일수록 이후 수익률이
          높다&quot;는 역발상 가설과 방향이 일치합니다.
        </p>
        <CorrelationChart correlation={data.correlation} horizons={data.horizons} />
      </section>

      <section className="mb-12">
        <h2 className="mb-3 text-lg font-semibold text-[#0b0b0b]">가설 검증</h2>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Hypothesis1Chart data={data.hypothesis1} horizons={data.horizons} />
          <Hypothesis2Chart data={data.hypothesis2} horizons={data.horizons} />
        </div>
      </section>

      <div className="mb-8 rounded-lg border border-[#eda100]/30 bg-[#eda100]/5 p-3 text-xs text-[#52514e]">
        <span className="font-medium text-[#0b0b0b]">⚠ 신호-체결 타이밍 안내: </span>
        CNN Fear &amp; Greed 지수는 통계적으로 그날 당일 종가 움직임과 강하게 연동되어
        있음이 확인됐습니다(당일 수익률과의 상관계수 0.56, 전날·다음날과는 거의 무관).
        즉 FG(D)의 최종값은 D일 종가 데이터가 있어야 확정되므로, 아래 모든 백테스트는
        보수적으로 <strong>하루 지연</strong>을 두어 &quot;FG(D-1)로 판단하고 D일 종가에
        체결&quot;하도록 계산합니다(신호를 안 순간과 체결 가능한 순간을 동일시하지
        않기 위함).
      </div>

      <section className="mb-12">
        <h2 className="mb-1 text-lg font-semibold text-[#0b0b0b]">
          백테스트 ①: FG 임계값 전략 vs Buy&amp;Hold
        </h2>
        <p className="mb-3 text-xs text-[#898781]">
          &quot;공포지수 20 이하 전량매수, 70 이상 전량매도&quot;를 실제로 반복했다면 동일기간
          지수 대비 어땠을지 시뮬레이션. 이 표본 기간은 강한 상승장이 대부분이라, 시장에 계속
          머무르는 Buy&amp;Hold에 유리하게 작용했을 수 있습니다.
        </p>
        <BacktestChart backtest={data.backtestThreshold} />
      </section>

      <section className="mb-12">
        <h2 className="mb-1 text-lg font-semibold text-[#0b0b0b]">
          백테스트 ②: 30% 초기편입 + 계단식 매수 전략 vs Buy&amp;Hold
        </h2>
        <p className="mb-3 text-xs text-[#898781]">
          첫 5거래일 동안 매일 6%p씩(지수 무관) 편입해 30%까지 채우고, 이후 FG가 70 이상이면
          전량매도, 70 밑이면 매주 수요일 5%p씩 비중을 늘리는 사이클을 반복합니다. 매수 진행
          중 FG가 20 밑으로 가면 즉시 전량매수 후 다음 매도 신호까지 보유합니다.
        </p>
        <GradualStrategyChart backtest={data.backtestGradual} />
      </section>

      <section className="mb-12">
        <h2 className="mb-1 text-lg font-semibold text-[#0b0b0b]">
          백테스트 ③: 파라미터 최적화 + 실제 약세장 구간 검증
        </h2>
        <p className="mb-3 text-xs text-[#898781]">
          초기편입 {(data.windowAnalysis.optimalParams.initial_allocation * 100).toFixed(0)}%
          ({data.windowAnalysis.optimalParams.ramp_days}거래일) &middot; 추가매수{" "}
          {(data.windowAnalysis.optimalParams.buy_step * 100).toFixed(0)}%씩{" "}
          {data.windowAnalysis.optimalParams.buy_interval_days}거래일마다 &middot; 재진입/매도{" "}
          {data.windowAnalysis.optimalParams.resell_level} &middot; 급락전량매수{" "}
          {data.windowAnalysis.optimalParams.crash_level} — 전체기간 집계 지표만으로는 &quot;거의
          모든 조합이 이긴다&quot;는 착시가 생겨서, 실제 나스닥 약세장(2021-11~2022-12,
          -36.4%) 구간에서 각 전략이 실제로 어떻게 버텼는지를 따로 확인했습니다.
        </p>
        <div className="flex flex-col gap-4">
          <WindowSummaryTable data={data.windowAnalysis} />
          <WindowEquityChart data={data.windowAnalysis} />
        </div>
      </section>

      <section className="mb-12">
        <h2 className="mb-1 text-lg font-semibold text-[#0b0b0b]">
          백테스트 ④: 후보 A~J 비교 &amp; 실전 매매 시그널
        </h2>
        <p className="mb-3 text-xs text-[#898781]">
          위험조정 최적점 근방의 열 후보를 비교합니다 — A: 초기 50%/추가매수 20%(21일) ·
          B: 초기 40%/추가매수 10%(21일, 분할 없음) · C: B를 2거래일에 나눠 편입 · D/E: B를
          5거래일에 나눠 편입(21일/14일 주기) · F/G: B를 10거래일에 나눠 편입(21일/14일
          주기) · H: F 구조에 트리거만 79/31로 바꾼 최근 5년 수익률 최고 설정(점선 표시) · I: H에서 매도만 보유분의 50%씩 하는 설정(짧은 점선 표시, 2011년 이후 전체 표본에서 더 나은 편) · J: 최종 추천안 — 매도 77에서 보유분 50%, FG 30 미만 급락 전량매수, 나스닥이 175일선보다 3% 아래로 내려가면 비중 25%로 줄이고 175일선 회복 시 복원하는 추세 보험(굵은 실선, 2011~2026 Sharpe 0.944 · MDD -19.5%로 Buy&Hold 0.815 · -36.4%보다 우수하나 총수익률은 낮음, session 22~26). 각 후보 아래에는 나스닥 종가·FG 지수 위에 실제 매수(파랑)·매도(주황) 신호를
          겹쳐 그린 차트와, 신호별 결과 포지션(비중)을 보여주는 표가 있습니다 — 실제로 이
          규칙대로 투자했다면 언제 얼마를 사고팔았을지 그대로 재현한 것입니다.
        </p>
        <div className="flex flex-col gap-4">
          <CandidatesEquityChart candidates={data.signalCandidates} buyHold={data.windowAnalysis.equityCurve} />
          <RollingReturnsChart series={data.rollingSeries["1y"]} horizonLabel="1년" />
          <RollingReturnsChart series={data.rollingSeries["2y"]} horizonLabel="2년" />
          {data.signalCandidates.map((c) => (
            <CandidatePanel key={c.id} candidate={c} timeseries={data.timeseries} />
          ))}
        </div>
      </section>

      <footer className="border-t border-black/10 pt-6 text-xs text-[#898781]">
        <p className="mb-1">
          데이터 출처: CNN Fear &amp; Greed Index(비공식 graphdata 엔드포인트), Yahoo Finance
          (^IXIC, 나스닥 종합지수). 생성 시각: {new Date(data.meta.generatedAt).toLocaleString("ko-KR")}
        </p>
        <p className="mb-1">
          다음 단계: overlapping window 문제를 다루는 정식 회귀분석(Newey-West/HAC), 표본 기간
          확장, 백테스트 파라미터(임계값) 민감도 분석.
        </p>
        <a href={REPO_URL} className="underline hover:text-[#2a78d6]" target="_blank" rel="noreferrer">
          {REPO_URL}
        </a>
      </footer>
    </main>
  );
}
