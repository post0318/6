"use client";

import type { DashboardData } from "@/lib/types";
import { FearGreedChart, Sp500Chart } from "@/components/charts/TimeSeriesCharts";
import { BucketSummaryCharts } from "@/components/charts/BucketSummaryCharts";
import { CorrelationChart } from "@/components/charts/CorrelationChart";
import { Hypothesis1Chart, Hypothesis2Chart } from "@/components/charts/HypothesisCharts";

const REPO_URL = "https://github.com/post0318/project-6-fear-greed";

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

      <footer className="border-t border-black/10 pt-6 text-xs text-[#898781]">
        <p className="mb-1">
          데이터 출처: CNN Fear &amp; Greed Index(비공식 graphdata 엔드포인트), Yahoo Finance
          (^GSPC). 생성 시각: {new Date(data.meta.generatedAt).toLocaleString("ko-KR")}
        </p>
        <p className="mb-1">
          다음 단계: overlapping window 문제를 다루는 정식 회귀분석(Newey-West/HAC), 표본 기간
          확장, 백테스트 시뮬레이터.
        </p>
        <a href={REPO_URL} className="underline hover:text-[#2a78d6]" target="_blank" rel="noreferrer">
          {REPO_URL}
        </a>
      </footer>
    </main>
  );
}
