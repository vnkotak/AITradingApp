import os
import json
from datetime import datetime
from backtest import run_backtests

def main():
    version = f"bt-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    res = run_backtests(["trend_follow","mean_reversion","momentum"], ["1m","5m","15m"], symbols_limit=20)
    # Simple ensemble weights proportional to Sharpe
    weights = {}
    for name, m in res.get("per_strategy", {}).items():
        w = max(0.0, float(m.get("sharpe", 0.0)))
        weights[name] = w
    s = sum(weights.values()) or 1.0
    weights = {k: v/s for k,v in weights.items()}
    metrics = {"per_strategy": res.get("per_strategy", {}), "generated_at": version}
    params = {"weights": weights}
    print(json.dumps({"version": version, "params": params, "metrics": metrics}))

if __name__ == "__main__":
    main()


