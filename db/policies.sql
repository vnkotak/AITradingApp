-- Enable Row Level Security and add read-only policies for public data

alter table public.symbols enable row level security;
alter table public.candles enable row level security;
alter table public.signals enable row level security;
alter table public.positions enable row level security;
alter table public.orders enable row level security;
alter table public.trades enable row level security;
alter table public.pnl_daily enable row level security;

do $$ begin
  create policy "Public read symbols" on public.symbols for select using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "Public read candles" on public.candles for select using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "Public read signals" on public.signals for select using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "Public read positions" on public.positions for select using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "Public read orders" on public.orders for select using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "Public read trades" on public.trades for select using (true);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "Public read pnl_daily" on public.pnl_daily for select using (true);
exception when duplicate_object then null; end $$;

-- Writes are intended via service role (bypasses RLS). No public write policies added.


