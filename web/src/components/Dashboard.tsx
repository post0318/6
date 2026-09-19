"use client";

import type { DashboardData } from "@/lib/types";
import { FearGreedChart, Sp500Chart } from "@/components/charts/TimeSeriesCharts";
import { BucketSummaryCharts } from "@/components/charts/BucketSummaryCharts";
import { CorrelationChart } from "@/components/charts/CorrelationChart";
import { Hypothesis1Chart, Hypothesis2Chart } from "@/components/charts/HypothesisCharts";
import { BacktestChart } from "@/components/charts/BacktestChart";
import { GradualStrategyChart } from "@/components/charts/GradualStrategyChart";

const REPO_URL = "https://github.com/post0318/6";

export function Dashboard({ data }: { data: DashboardData }) {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <header className="mb-10">
        <h1 className="text-2xl font-semibold text-[#0b0b0b] sm:text-3xl">
          Fear &amp; Greed 역발상 투자 리서치 — Project 6
        </h1>
        <p className="mt-2 text-sm text-[#52514e]">
          CNN Fear &amp; Greed Index가 S&amp;P 500 인덱스 투자의 역발상(contrarian) 신호로
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
        <h2 className="mb-3 text-lg font-semibold text-[#0b0b0b]">시계열: 지수 vs S&amp;P 500</h2>
        <div className="flex flex-col gap-4">
          <Sp500Chart data={data.timeseries} />
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
          시작일에 지수와 무관하게 30%를 편입하고, FG가 65 밑으로 내려가면 매수 진행 모드가
          켜져 매주 수요일 5%p씩 비중을 늘립니다(65를 다시 넘어도 계속). FG가 75를 넘으면
          전량매도 후 재트리거(65 하회)를 기다리고, 매수 진행 중 FG가 25 밑으로 가면 즉시
          전량매수로 전환합니다.
        </p>
        <GradualStrategyChart backtest={data.backtestGradual} />
      </section>

      <footer className="border-t border-black/10 pt-6 text-xs text-[#898781]">
        <p className="mb-1">
          데이터 출처: CNN Fear &amp; Greed Index(비공식 graphdata 엔드포인트), Yahoo Finance
          (^GSPC). 생성 시각: {new Date(data.meta.generatedAt).toLocaleString("ko-KR")}
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
