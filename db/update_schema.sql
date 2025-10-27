ALTER TABLE public.strategy_runs DROP CONSTRAINT strategy_runs_mode_check;
ALTER TABLE public.strategy_runs ADD CONSTRAINT strategy_runs_mode_check CHECK (mode IN ('1m','5m','15m','1h','1d'));
