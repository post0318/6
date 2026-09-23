export type HorizonKey = "1w" | "1m" | "3m" | "6m" | "12m";

export interface HorizonMeta {
  key: HorizonKey;
  ko: string;
}

export interface RatingMeta {
  key: string;
  ko: string;
}

export interface TimeseriesPoint {
  date: string;
  fg: number | null;
  nasdaq: number | null;
}

export interface BucketHorizonStat {
  mean: number | null;
  n: number | null;
}

export interface BucketSummaryEntry {
  rating: string;
  ratingKo: string;
  byHorizon: Record<HorizonKey, BucketHorizonStat>;
}

export interface Hypothesis1Stat {
  reboundingMean: number | null;
  reboundingN: number | null;
  stillFallingMean: number | null;
  stillFallingN: number | null;
}

export interface Hypothesis2Stat {
  persistentMean: number | null;
  persistentN: number | null;
  restMean: number | null;
  restN: number | null;
}

export interface BacktestPerfStats {
  total_return: number;
  cagr: number;
  max_drawdown: number;
  annualized_vol: number;
  sharpe_like: number;
}

export interface BacktestTrade {
  date: string;
  action: "BUY" | "SELL";
  fg: number;
  price: number;
}

export interface BacktestEquityPoint {
  date: string;
  strategy: number | null;
  benchmark: number | null;
  inStock: boolean;
}

export interface BacktestData {
  params: { buyThreshold: number; sellThreshold: number; cashInterest: number };
  strategy: BacktestPerfStats;
  benchmark: BacktestPerfStats;
  pctDaysInMarket: number;
  numTrades: number;
  trades: BacktestTrade[];
  equityCurve: BacktestEquityPoint[];
}

export interface GradualEquityPoint {
  date: string;
  strategy: number | null;
  benchmark: number | null;
  weight: number | null;
  buyingActive: boolean;
}

export interface GradualBacktestData {
  params: {
    rampDays: number;
    rampDailyStep: number;
    resellLevel: number;
    crashFullBuy: number;
    weeklyStep: number;
    cashInterest: number;
  };
  strategy: BacktestPerfStats;
  benchmark: BacktestPerfStats;
  finalWeight: number;
  numTrades: number;
  tradeCounts: Record<string, number>;
  equityCurve: GradualEquityPoint[];
}

export interface WindowStat extends BacktestPerfStats {
  peakToTrough: number;
  peakToRecovery: number;
}

export interface WindowEquityPoint {
  date: string;
  buyHold: number | null;
  v1: number | null;
  v2Default: number | null;
  v2Optimal: number | null;
}

export interface WindowAnalysisData {
  window: { peakDate: string; troughDate: string; recoveryDate: string };
  optimalParams: {
    initial_allocation: number;
    ramp_days: number;
    buy_interval_days: number;
    buy_step: number;
    resell_level: number;
    crash_level: number;
  };
  summary: {
    buyHold: WindowStat;
    v1: WindowStat;
    v2Default: WindowStat;
    v2Optimal: WindowStat;
  };
  equityCurve: WindowEquityPoint[];
}

export interface SignalTrade {
  date: string;
  action:
    | "RAMP_BUY"
    | "WEEKLY_BUY"
    | "CRASH_FULL_BUY"
    | "SELL_ALL"
    | "SELL_HALF"
    | "CRASH_HALF_BUY"
    | "TREND_CUT"
    | "TREND_RESTORE";
  fg: number;
  price: number;
  pctOfPortfolio: number | null;
  resultingWeight: number;
}

export interface RollingSummary {
  mean: number;
  median: number;
  worst: number;
  best: number;
  pctNegative: number;
  winRateVsBenchmark: number;
}

export interface SignalCandidate {
  id: string;
  label: string;
  params: {
    initial_allocation: number;
    ramp_days: number;
    buy_interval_days: number;
    buy_step: number;
    resell_level: number;
    crash_level: number;
    sell_fraction?: number;
    trend_ma?: number;
    trend_buffer?: number;
    trend_cap?: number;
  };
  currentStatus: {
    currentWeight: number;
    buyingActive: boolean;
    lastTrade: SignalTrade | null;
    hint: string;
  };
  summary: {
    original: BacktestPerfStats;
    rolling1y: RollingSummary;
    rolling2y: RollingSummary;
  };
  trades: SignalTrade[];
  equityCurve: { date: string; equity: number }[];
}

export interface DashboardData {
  meta: {
    generatedAt: string;
    dateRange: { start: string; end: string };
    sampleCaveat: string;
  };
  horizons: HorizonMeta[];
  ratingOrder: RatingMeta[];
  timeseries: TimeseriesPoint[];
  bucketSummary: Record<string, BucketSummaryEntry>;
  correlation: Record<HorizonKey, number | null>;
  hypothesis1: Record<HorizonKey, Hypothesis1Stat>;
  hypothesis2: Record<HorizonKey, Hypothesis2Stat>;
  backtestThreshold: BacktestData;
  backtestGradual: GradualBacktestData;
  windowAnalysis: WindowAnalysisData;
  signalCandidates: SignalCandidate[];
  rollingSeries: {
    "1y": RollingSeriesPoint[];
    "2y": RollingSeriesPoint[];
  };
  kospi: KospiSection;
}

export interface KospiCandidate {
  id: string;
  label: string;
  params: SignalCandidate["params"];
  summary: BacktestPerfStats;
  equityCurve: { date: string; equity: number }[];
}

export interface KospiExperiment {
  id: string;
  label: string;
  dateRange: { start: string; end: string };
  caveat: string;
  buyHoldEquityCurve: { date: string; equity: number }[];
  candidates: KospiCandidate[];
}

export interface KospiSection {
  experiments: KospiExperiment[];
}

export interface RollingSeriesPoint {
  date: string;
  buyHold: number;
  A: number;
  B: number;
  C: number;
  D: number;
  E: number;
  F: number;
  G: number;
  H: number;
  I: number;
  J: number;
}
