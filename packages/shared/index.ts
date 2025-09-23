export type Timeframe = '1m' | '5m' | '15m' | '1h' | '1d';

export interface TradeSignal {
  symbol: string;
  timeframe: Timeframe;
  strategy: string;
  action: 'BUY' | 'SELL' | 'EXIT_LONG' | 'EXIT_SHORT';
  entry: number;
  stop: number;
  target?: number;
  confidence?: number; // 0..1
  rationale?: Record<string, unknown>;
  ts?: string;
}

export interface OrderRequest {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  price?: number;
  qty: number;
}

export interface RiskLimits {
  maxCapitalPerTradePct: number;
  maxDailyLossPct: number;
  maxPortfolioDrawdownPct: number;
  maxSectorExposurePct: number;
  circuitBreakerPct: number;
  kellyFraction: number;
  pauseAll: boolean;
}


