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
  sp500: number | null;
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
  backtest: BacktestData;
}
