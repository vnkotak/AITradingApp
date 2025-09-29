from __future__ import annotations

from datetime import datetime, timezone
from typing import List
import pandas as pd

from apps.api.supabase_client import get_client
from apps.api.yahoo_client import fetch_yahoo_candles
from apps.api.strategies.indicators import add_core_indicators
from apps.api.strategies.engine import run_strategies
from apps.api.signal_generator import ScoredSignal, score_signal, ensemble
from apps.api.model_weights import get_latest_strategy_weights


def fetch_history_df(symbol_id: str, ticker: str, exchange: str, tf: str, lookback_days: int = 7) -> pd.DataFrame:
    sb = get_client()
    # Try DB first
    data = (
        sb.table("candles").select("ts,open,high,low,close,volume")
        .eq("symbol_id", symbol_id).eq("timeframe", tf)
        .order("ts", desc=True).limit(1000).execute().data
    )
    if not data:
        candles = fetch_yahoo_candles(ticker, exchange, tf, lookback_days=lookback_days)
        rows = [{
            "symbol_id": symbol_id,
            "timeframe": tf,
            "ts": c["ts"],
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c.get("volume"),
        } for c in candles]
        if rows:
            sb.table("candles").upsert(rows, on_conflict="symbol_id,timeframe,ts").execute()
            data = rows
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    df = df[["ts","open","high","low","close","volume"]]
    return df


def scan_once(mode: str, force: bool = False) -> dict:
    sb = get_client()
    # Record run
    print("Mode ", mode)
    run = sb.table("strategy_runs").insert({"mode": mode}).execute().data[0]
    run_id = run["id"]
    symbols = sb.table("symbols").select("id,ticker,exchange").eq("is_active", True).limit(50).execute().data
    total_signals = 0
    for s in symbols:
        sid = s["id"]; ticker = s["ticker"]; exch = s["exchange"]
        df = fetch_history_df(sid, ticker, exch, tf=mode)
        if df.empty or len(df) < 60:
            continue
        df = add_core_indicators(df)
        raw_signals = run_strategies(df)
        if not raw_signals and force:
            # deterministic forced signal for testing
            last = df.iloc[-1]
            prev = df.iloc[-2]
            entry = float(last["close"]) 
            atr = float(pd.concat([
                (df['high'].astype(float) - df['low'].astype(float)),
                (df['high'].astype(float) - df['close'].astype(float).shift(1)).abs(),
                (df['low'].astype(float) - df['close'].astype(float).shift(1)).abs(),
            ], axis=1).max(axis=1).rolling(14).mean().iloc[-1] or (entry*0.01))
            stop = float(min(prev["low"], entry - 1.0 * atr))
            target = float(entry + 2.0 * (entry - stop))
            from apps.api.strategies.engine import Signal as StratSignal
            raw_signals = [StratSignal("BUY", entry, stop, target, 0.6, "forced_test", {"reason": "force=true"})]
        if not raw_signals:
            continue
        last_ts = df.iloc[-1]["ts"]
        rows = []
        scored: List[ScoredSignal] = []
        for sig in raw_signals:
            conf, rationale = score_signal(df, sig.action, sig.confidence, context={"ticker": ticker, "exchange": exch})
            scored.append(ScoredSignal(
                action=sig.action,
                entry=sig.entry,
                stop=sig.stop,
                target=sig.target,
                confidence=conf,
                strategy=sig.strategy,
                rationale={"rationale": sig.rationale, "scoring": rationale},
            ))
            rows.append({
                "symbol_id": sid,
                "timeframe": mode,
                "ts": datetime.now(timezone.utc).isoformat(),
                "strategy": sig.strategy,
                "action": sig.action,
                "entry": sig.entry,
                "stop": sig.stop,
                "target": sig.target,
                "confidence": conf,
                "rationale": {"rationale": sig.rationale, "scoring": rationale},
            })
        if rows:
            sb.table("signals").insert(rows).execute()
        # Ensemble decision using latest model weights
        weights = get_latest_strategy_weights(defaults={"trend_follow":1,"mean_reversion":1,"momentum":1})
        ens = ensemble(scored, strategy_weights=weights)
        # Map decision to DB enum
        raw_decision = ens.get("decision")
        if raw_decision in ("BUY", "ENTER_LONG"):
            decision_val = "ENTER_LONG"
        elif raw_decision in ("SELL", "ENTER_SHORT"):
            decision_val = "ENTER_SHORT"
        elif raw_decision in ("EXIT", "EXIT_LONG", "EXIT_SHORT"):
            decision_val = "EXIT"
        else:
            decision_val = "PASS"
        try:
            model = sb.table("ai_models").insert({"version":"v0", "params": {"type": "linear-blend"}}).execute().data[0]
        except Exception:
            model = sb.table("ai_models").select("id").order("created_at", desc=True).limit(1).execute().data[0]
        sb.table("ai_decisions").insert({
            "model_id": model["id"],
            "weights": ens["weights"],
            "decision": decision_val,
            "rationale": {"mode": mode, "symbol": ticker},
        }).execute()
        total_signals += len(rows)
    sb.table("strategy_runs").update({"symbols_scanned": len(symbols or []), "signals_generated": total_signals, "completed_at": datetime.now(timezone.utc).isoformat()}).eq("id", run_id).execute()
    return {"run_id": run_id, "signals": total_signals, "symbols_scanned": len(symbols or [])}


