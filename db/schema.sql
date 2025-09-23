-- Supabase schema for AITradingApp
-- Run this in Supabase SQL editor

-- Extensions (for gen_random_uuid)
create extension if not exists pgcrypto;

-- core reference
create table if not exists public.symbols (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  exchange text not null check (exchange in ('NSE','BSE')),
  name text,
  sector text,
  is_fno boolean default false,
  lot_size int,
  is_active boolean default true,
  unique (ticker, exchange)
);

create table if not exists public.candles (
  symbol_id uuid references public.symbols(id) on delete cascade,
  timeframe text not null check (timeframe in ('1m','5m','15m','1h','1d')),
  ts timestamptz not null,
  open numeric not null,
  high numeric not null,
  low numeric not null,
  close numeric not null,
  volume numeric,
  vwap numeric,
  primary key (symbol_id, timeframe, ts)
);

create table if not exists public.signals (
  id uuid primary key default gen_random_uuid(),
  symbol_id uuid references public.symbols(id) on delete cascade,
  timeframe text not null,
  ts timestamptz not null default now(),
  strategy text not null,
  action text not null check (action in ('BUY','SELL','EXIT_LONG','EXIT_SHORT')),
  entry numeric not null,
  stop numeric not null,
  target numeric,
  confidence numeric check (confidence between 0 and 1),
  rationale jsonb
);

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  symbol_id uuid references public.symbols(id) on delete cascade,
  ts timestamptz not null default now(),
  side text not null check (side in ('BUY','SELL')),
  type text not null check (type in ('MARKET','LIMIT')),
  price numeric,
  qty numeric not null,
  status text not null check (status in ('NEW','PARTIAL','FILLED','CANCELLED','REJECTED')),
  time_in_force text default 'DAY',
  client_tag text,
  slippage_bps numeric,
  simulator_notes jsonb
);

create table if not exists public.trades (
  id uuid primary key default gen_random_uuid(),
  order_id uuid references public.orders(id) on delete set null,
  symbol_id uuid references public.symbols(id) on delete cascade,
  ts timestamptz not null default now(),
  side text not null,
  price numeric not null,
  qty numeric not null,
  fees numeric default 0
);

create table if not exists public.positions (
  id uuid primary key default gen_random_uuid(),
  symbol_id uuid references public.symbols(id) on delete cascade,
  avg_price numeric not null default 0,
  qty numeric not null default 0,
  realized_pnl numeric not null default 0,
  unrealized_pnl numeric not null default 0,
  exposure numeric not null default 0,
  updated_at timestamptz not null default now()
);

create table if not exists public.pnl_daily (
  trade_date date primary key,
  equity numeric not null,
  realized_pnl numeric not null,
  unrealized_pnl numeric not null,
  max_drawdown numeric not null,
  sharpe numeric,
  cagr numeric
);

create table if not exists public.risk_limits (
  id uuid primary key default gen_random_uuid(),
  max_capital_per_trade_pct numeric not null default 5,
  max_daily_loss_pct numeric not null default 3,
  max_portfolio_drawdown_pct numeric not null default 15,
  max_sector_exposure_pct numeric not null default 25,
  circuit_breaker_pct numeric not null default 20,
  kelly_fraction numeric not null default 0.5,
  pause_all boolean not null default false,
  updated_at timestamptz not null default now()
);

create table if not exists public.strategy_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  mode text not null check (mode in ('1m','5m','15m')),
  symbols_scanned int,
  signals_generated int,
  metadata jsonb
);

create table if not exists public.ai_models (
  id uuid primary key default gen_random_uuid(),
  version text not null,
  created_at timestamptz not null default now(),
  params jsonb not null,
  metrics jsonb,
  notes text
);

create table if not exists public.ai_decisions (
  id uuid primary key default gen_random_uuid(),
  model_id uuid references public.ai_models(id) on delete set null,
  signal_id uuid references public.signals(id) on delete set null,
  weights jsonb not null,
  decision text not null check (decision in ('PASS','ENTER_LONG','ENTER_SHORT','EXIT')),
  rationale jsonb,
  created_at timestamptz not null default now()
);

-- Sentiment storage
create table if not exists public.sentiment (
  symbol_id uuid references public.symbols(id) on delete cascade,
  ts timestamptz not null default now(),
  source text,
  title text,
  url text,
  score numeric not null,
  primary key (symbol_id, ts)
);


