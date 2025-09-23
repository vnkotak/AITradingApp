from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Dict, List

from supabase import create_client
import os


def supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE env")
    return create_client(url, key)


def fetch_recent_signals(limit: int = 500):
    sb = supabase_client()
    data = sb.table('signals').select('ts,strategy,action,confidence').order('ts', desc=True).limit(limit).execute().data
    return data or []


def reward_from_orders(limit: int = 500):
    sb = supabase_client()
    trades = sb.table('trades').select('ts,price,qty,side').order('ts', desc=True).limit(limit).execute().data
    # naive reward: sign of pnl per trade; placeholder ties signals to outcomes indirectly by time proximity
    rewards = 0.0
    for t in trades:
        side = t['side']
        qty = float(t['qty'] or 0)
        # assume profitable trades in recent window count positive
        rewards += (1.0 if side == 'SELL' else 1.0) * (qty>0)
    return rewards / max(1, len(trades))


def update_weights_online(weights: Dict[str, float]) -> Dict[str, float]:
    # simple stochastic adjustment as placeholder for bandit/online logistic
    signals = fetch_recent_signals(300)
    if not signals:
        return weights
    # tally per strategy by average confidence
    strat_conf: Dict[str, float] = {}
    strat_cnt: Dict[str, int] = {}
    for s in signals:
        st = s['strategy']
        strat_conf[st] = strat_conf.get(st, 0.0) + float(s.get('confidence') or 0)
        strat_cnt[st] = strat_cnt.get(st, 0) + 1
    for st, total in strat_conf.items():
        avg = total / max(1, strat_cnt.get(st,1))
        delta = (avg - 0.5) * 0.05  # push weights up if avg conf > 0.5
        weights[st] = max(0.0, weights.get(st, 0.5) + delta)
    # normalize
    s = sum(weights.values()) or 1.0
    weights = {k: v/s for k,v in weights.items()}
    return weights


def main():
    sb = supabase_client()
    latest = sb.table('ai_models').select('*').order('created_at', desc=True).limit(1).execute().data
    if latest:
        params = latest[0]['params'] or {}
        weights = params.get('weights') or {"trend_follow":0.33,"mean_reversion":0.33,"momentum":0.34}
    else:
        weights = {"trend_follow":0.33,"mean_reversion":0.33,"momentum":0.34}
    new_weights = update_weights_online(weights)
    # register new model version
    import requests
    version = 'rl-' + str(random.randint(100000,999999))
    payload = {"version": version, "params": {"weights": new_weights}, "metrics": {"method": "online_adjust"}}
    api = os.environ.get('API_BASE')
    token = os.environ.get('SCANNER_TOKEN')
    if api and token:
        try:
            requests.post(f"{api}/ai/models/register", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload, timeout=30)
        except Exception:
            print(json.dumps(payload))
    else:
        print(json.dumps(payload))


if __name__ == '__main__':
    main()


