from __future__ import annotations

from datetime import datetime, timezone
from typing import List
import pandas as pd
import gc

from apps.api.supabase_client import get_client
from apps.api.yahoo_client import fetch_yahoo_candles
from apps.api.strategies.indicators import add_core_indicators
from apps.api.strategies.engine import run_strategies, signal_quality_filter
from apps.api.signal_generator import ScoredSignal, score_signal, ensemble
from apps.api.model_weights import get_latest_strategy_weights


def is_overbought_oversold(df: pd.DataFrame) -> bool:
    """
    Check if current market conditions are overbought or oversold.
    Returns True if signals should be filtered out due to extreme conditions.
    """
    if df.empty or len(df) < 2:
        return False

    last = df.iloc[-1]

    # RSI extremes
    rsi = float(last.get("rsi14", 50))
    if rsi > 75 or rsi < 25:  # Extreme overbought/oversold
        return True

    # MACD extreme divergence
    macd = float(last.get("macd", 0))
    macd_signal = float(last.get("macd_signal", 0))
    macd_hist = float(last.get("macd_hist", 0))

    # MACD histogram showing extreme momentum (potential exhaustion)
    if abs(macd_hist) > abs(macd) * 0.8:  # Histogram very large relative to MACD
        return True

    # Bollinger Band extreme positioning
    bb_upper = float(last.get("bb_upper", last.get("close", 0)))
    bb_lower = float(last.get("bb_lower", last.get("close", 0)))
    close = float(last.get("close", 0))

    if bb_upper > 0:
        bb_position = (close - bb_lower) / (bb_upper - bb_lower)
        if bb_position > 0.95 or bb_position < 0.05:  # Price at extreme bands
            return True

    # ADX extreme trend strength (potential exhaustion)
    adx = float(last.get("adx14", 25))
    if adx > 60:  # Extremely strong trend may be exhausting
        return True

    return False


def get_existing_candle_info(symbol_id: str, tf: str) -> dict:
    """Get information about existing candle data"""
    try:
        sb = get_client()
        # Get the most recent candle
        latest_candle = sb.table('candles').select('ts').eq('symbol_id', symbol_id).eq('timeframe', tf).order('ts', desc=True).limit(1).execute().data

        if not latest_candle:
            return {'exists': False, 'latest_date': None}

        latest_date = latest_candle[0]['ts']

        # Get total count
        all_candles = sb.table('candles').select('ts').eq('symbol_id', symbol_id).eq('timeframe', tf).execute().data

        return {
            'exists': True,
            'latest_date': latest_date,
            'count': len(all_candles) if all_candles else 0
        }
    except Exception as e:
        print(f"❌ Error checking existing candle data: {e}")
        return {'exists': False, 'latest_date': None}

def calculate_candle_delta_days(tf: str, existing_info: dict, max_lookback: int = 7) -> int:
    """Calculate how many additional days of candle data we need"""
    if not existing_info['exists']:
        # No existing data, fetch full period
        return max_lookback

    latest_date = existing_info['latest_date']

    # Handle both string and datetime objects
    if isinstance(latest_date, str):
        try:
            from datetime import datetime, timezone
            if latest_date.endswith('Z'):
                latest_date = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
            else:
                latest_date = datetime.fromisoformat(latest_date)
        except:
            print(f"  ⚠️ Could not parse date: {latest_date}")
            return 1

    if isinstance(latest_date, datetime):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Convert to IST for market hours check
        ist_hour = (now.hour + 5) % 24
        ist_min = now.minute + 30
        if ist_min >= 60:
            ist_min -= 60
            ist_hour = (ist_hour + 1) % 24

        # Check if it's a weekday (1-5 = Monday-Friday)
        is_weekday = 1 <= now.weekday() + 1 <= 5

        # Check if within market hours (IST 9:15 AM - 3:30 PM)
        is_market_hours = False
        if is_weekday:
            if ist_hour > 9 and ist_hour < 15:
                is_market_hours = True
            elif ist_hour == 9 and ist_min >= 15:
                is_market_hours = True
            elif ist_hour == 15 and ist_min <= 30:
                is_market_hours = True

        days_since_latest = (now - latest_date).days
        hours_since_latest = (now - latest_date).total_seconds() / 3600

        print(f"  📊 Debug: Current={now.strftime('%Y-%m-%d %H:%M')} UTC, Latest={latest_date.strftime('%Y-%m-%d %H:%M')} UTC")
        print(f"  📊 Debug: Days diff={days_since_latest}, Hours diff={hours_since_latest:.1f}")

        # Check if latest data is from today or yesterday (Friday if today is Saturday)
        latest_is_today = latest_date.date() == now.date()
        latest_is_yesterday = (now.date() - latest_date.date()).days == 1

        # If outside market hours, be smart about data freshness
        if not is_market_hours:
            if latest_is_today:
                print(f"  📊 Outside market hours - data is from today (latest: {latest_date.strftime('%Y-%m-%d %H:%M:%S')})")
                return 0
            elif latest_is_yesterday and now.weekday() == 5:  # Saturday, data from Friday
                print(f"  📊 Weekend - data is from Friday (latest: {latest_date.strftime('%Y-%m-%d %H:%M:%S')})")
                return 0
            elif latest_is_yesterday and now.weekday() == 6:  # Sunday, data from Friday
                print(f"  📊 Weekend - data is from Friday (latest: {latest_date.strftime('%Y-%m-%d %H:%M:%S')})")
                return 0
            elif days_since_latest >= 3:
                print(f"  📊 Outside market hours but data is {days_since_latest} days old, fetching minimal update")
                return min(2, max_lookback)  # Fetch max 2 days outside hours
            else:
                print(f"  📊 Outside market hours - data is {days_since_latest} day(s) old but markets closed")
                return 0

        # During market hours - check if we need fresh data
        if days_since_latest <= 0:
            print(f"  📊 Candle data is up to date (latest: {latest_date.strftime('%Y-%m-%d %H:%M:%S')})")
            return 0

        # Special handling: If data is from yesterday but markets just opened, fetch today's data
        if latest_is_yesterday and is_market_hours and ist_hour <= 10:  # Early morning session
            print(f"  📊 Fresh trading session - data from yesterday, fetching today's data")
            return min(2, max_lookback)  # Fetch 1-2 days to get current session

        # Calculate delta based on timeframe
        if tf in ['1m', '5m', '15m']:
            # For intraday timeframes, always try to fetch recent data during market hours
            if hours_since_latest > 4:
                delta_days = min(max_lookback, max(1, int(hours_since_latest / 24) + 1))
                print(f"  📊 Intraday data is {hours_since_latest:.1f} hours old, fetching {delta_days} additional days")
                return delta_days
            else:
                print(f"  📊 Intraday data is up to date ({hours_since_latest:.1f} hours old)")
                return 0
        else:
            # For other timeframes, use days but be more conservative during market hours
            if days_since_latest <= 1:
                print(f"  📊 {tf} data is recent ({days_since_latest} day old)")
                return 0
            delta_days = min(max_lookback, max(1, days_since_latest))

        print(f"  📊 During market hours - data is {days_since_latest} days old, fetching {delta_days} additional days")
        return delta_days

    return 1

def fetch_history_df(symbol_id: str, ticker: str, exchange: str, tf: str, lookback_days: int = 7) -> pd.DataFrame:
    sb = get_client()

    # Check existing data and calculate delta needed
    existing_info = get_existing_candle_info(symbol_id, tf)
    delta_days = calculate_candle_delta_days(tf, existing_info, lookback_days)

    # Always fetch some recent data during market hours for intraday timeframes
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Convert to IST for market hours check
    ist_hour = (now.hour + 5) % 24
    ist_min = now.minute + 30
    if ist_min >= 60:
        ist_min -= 60
        ist_hour = (ist_hour + 1) % 24

    # Check if within market hours (IST 9:15 AM - 3:30 PM) and weekday
    is_weekday = 1 <= now.weekday() + 1 <= 5
    is_market_hours = False
    if is_weekday:
        if ist_hour > 9 and ist_hour < 15:
            is_market_hours = True
        elif ist_hour == 9 and ist_min >= 15:
            is_market_hours = True
        elif ist_hour == 15 and ist_min <= 30:
            is_market_hours = True

    # Determine if we need to fetch new data
    if (tf in ['1m', '5m', '15m'] and is_market_hours) or delta_days > 0:
        # Fetch data from Yahoo
        fetch_days = max(delta_days, 1) if (tf in ['1m', '5m', '15m'] and is_market_hours) else delta_days
        print(f"📊 Fetching {fetch_days} days of {tf} data for {ticker}")
        candles = fetch_yahoo_candles(ticker, exchange, tf, lookback_days=fetch_days)

        if not candles:
            print(f"⚠️ No new {tf} data available for {ticker}")
            # Fetch existing data from DB - reduced limit for memory
            data = (
                sb.table("candles").select("ts,open,high,low,close,volume")
                .eq("symbol_id", symbol_id).eq("timeframe", tf)
                .order("ts", desc=True).limit(300).execute().data
            )
        else:
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

            # Insert only new candles (upsert handles duplicates)
            if rows:
                sb.table("candles").upsert(rows, on_conflict="symbol_id,timeframe,ts").execute()
                print(f"💾 Stored {len(rows)} new {tf} candles for {ticker}")

            # Fetch all data (including newly inserted) - reduced limit for memory
            data = (
                sb.table("candles").select("ts,open,high,low,close,volume")
                .eq("symbol_id", symbol_id).eq("timeframe", tf)
                .order("ts", desc=True).limit(300).execute().data
            )
    else:
        # Data is up to date, just use existing data - reduced limit for memory
        print(f"📊 Data is current for {ticker} {tf}")
        data = (
            sb.table("candles").select("ts,open,high,low,close,volume")
            .eq("symbol_id", symbol_id).eq("timeframe", tf)
            .order("ts", desc=True).limit(300).execute().data
        )

    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    df = df[["ts","open","high","low","close","volume"]]
    return df


def scan_once(mode: str, force: bool = False, max_symbols: int = 200) -> dict:
    sb = get_client()
    # Record run
    print(f"Mode {mode} - Memory optimized (max {max_symbols} symbols)")
    run = sb.table("strategy_runs").insert({"mode": mode}).execute().data[0]
    run_id = run["id"]
    symbols = sb.table("symbols").select("id,ticker,exchange").eq("is_active", True).limit(max_symbols).execute().data
    total_signals = 0
    delta_updates = 0
    full_refreshes = 0
    for s in symbols:
        sid = s["id"]; ticker = s["ticker"]; exch = s["exchange"]
        print(f"🔍 Scanning {ticker}...")
        df = fetch_history_df(sid, ticker, exch, tf=mode)

        # Track if this was a delta update or full refresh
        existing_info = get_existing_candle_info(sid, mode)
        if existing_info['exists']:
            delta_updates += 1
        else:
            full_refreshes += 1
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
        # Use the same quality filtering as backtest - just apply signal_quality_filter
        quality_signals = []
        for sig in raw_signals:
            # Apply the same filter used in backtest
            if signal_quality_filter(sig, df):
                quality_signals.append(sig)

        if quality_signals:
            # Convert to database format
            rows = []
            for sig in quality_signals:
                rows.append({
                    "symbol_id": sid,
                    "timeframe": mode,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "strategy": sig.strategy,
                    "action": sig.action,
                    "entry": sig.entry,
                    "stop": sig.stop,
                    "target": sig.target,
                    "confidence": sig.confidence,
                    "rationale": {"rationale": sig.rationale, "quality_filtered": True},
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

        # Memory cleanup after each symbol
        del df, raw_signals, scored, ens, weights
        gc.collect()
    sb.table("strategy_runs").update({"symbols_scanned": len(symbols or []), "signals_generated": total_signals, "completed_at": datetime.now(timezone.utc).isoformat()}).eq("id", run_id).execute()

    print("\n📋 SCAN SUMMARY:")
    print(f"  Total symbols processed: {len(symbols or [])}")
    print(f"  Delta updates: {delta_updates}")
    print(f"  Full refreshes: {full_refreshes}")
    print(f"  Total signals generated: {total_signals}")
    print(f"  Efficiency: {delta_updates/(delta_updates+full_refreshes)*100:.1f}% delta updates")

    return {
        "run_id": run_id,
        "signals": total_signals,
        "symbols_scanned": len(symbols or []),
        "delta_updates": delta_updates,
        "full_refreshes": full_refreshes
    }


