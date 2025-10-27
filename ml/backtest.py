from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import pandas_ta as ta
from supabase import create_client
import os
import sys

# Import live strategy engine and signal generation
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))
from strategies.engine import mean_reversion, macd_trend, hull_suite, signal_quality_filter, Signal
from signal_generator import score_signal, ScoredSignal


Timeframe = Literal['1m','5m','15m','1h','1d']


def supabase_client():
    url = os.environ.get("SUPABASE_URL") or "https://lfwgposvyckptsrjkkyx.supabase.co"
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxmd2dwb3N2eWNrcHRzcmpra3l4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTg0MjI3MSwiZXhwIjoyMDY1NDE4MjcxfQ.7Pjsw_HpyE5RHHFshsRT3Ibpn1b6N4CO3F4rIw_GSvc"
    if not url or not key:
        raise RuntimeError("Missing SUPABASE env")
    return create_client(url, key)


def load_symbols(limit: int = 20) -> List[Dict]:
    sb = supabase_client()
    return sb.table("symbols").select("id,ticker,exchange").eq("is_active", True).limit(limit).execute().data or []


def load_candles(symbol_id: str, tf: Timeframe, days: int = 1200, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    sb = supabase_client()

    # Handle date filtering
    if start_date and end_date:
        # Convert string dates to datetime
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        # Ensure UTC
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        since = start_dt.isoformat()
        until = end_dt.isoformat()
        data = (
            sb.table("candles")
            .select("ts,open,high,low,close,volume")
            .eq("symbol_id", symbol_id)
            .eq("timeframe", tf)
            .gte("ts", since)
            .lte("ts", until)
            .order("ts")
            .execute().data
        )
    else:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        data = (
            sb.table("candles")
            .select("ts,open,high,low,close,volume")
            .eq("symbol_id", symbol_id)
            .eq("timeframe", tf)
            .gte("ts", since)
            .order("ts")
            .execute().data
        )
    df = pd.DataFrame(data or [])
    if df.empty:
        return df
    for k in ["open","high","low","close","volume"]:
        df[k] = pd.to_numeric(df[k], errors='coerce')
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df.dropna().reset_index(drop=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators with robust error handling"""
    out = df.copy()

    # Basic indicators with error handling
    try:
        out["ema20"] = ta.ema(out["close"], length=20)
    except Exception as e:
        print(f"EMA20 calculation failed: {e}")
        out["ema20"] = pd.NA

    try:
        out["ema50"] = ta.ema(out["close"], length=50)
    except Exception as e:
        print(f"EMA50 calculation failed: {e}")
        out["ema50"] = pd.NA

    try:
        out["rsi14"] = ta.rsi(out["close"], length=14)
    except Exception as e:
        print(f"RSI14 calculation failed: {e}")
        out["rsi14"] = pd.NA

    # MACD with robust error handling
    try:
        macd = ta.macd(out["close"], fast=12, slow=26, signal=9)

        if macd is None or macd.empty:
            print("MACD calculation returned None or empty, using fallback")
            out["macd"] = pd.NA
            out["macd_signal"] = pd.NA
            out["macd_hist"] = pd.NA
        else:
            # Dynamically detect MACD column names (pandas-ta versions may vary)
            macd_col = None
            signal_col = None
            hist_col = None

            for col in macd.columns:
                col_str = str(col)
                if 'MACD' in col_str and 'MACDs' not in col_str and 'MACDh' not in col_str:
                    macd_col = col
                elif 'MACDs' in col_str:
                    signal_col = col
                elif 'MACDh' in col_str:
                    hist_col = col

            if macd_col and signal_col and hist_col:
                out["macd"] = macd[macd_col]
                out["macd_signal"] = macd[signal_col]
                out["macd_hist"] = macd[hist_col]
            else:
                print(f"MACD columns not found as expected. Available: {list(macd.columns)}")
                out["macd"] = pd.NA
                out["macd_signal"] = pd.NA
                out["macd_hist"] = pd.NA

    except Exception as e:
        print(f"MACD calculation failed: {e}")
        out["macd"] = pd.NA
        out["macd_signal"] = pd.NA
        out["macd_hist"] = pd.NA
    # Bollinger Bands with error handling
    try:
        bb = ta.bbands(out["close"], length=20, std=2.0)

        if bb is not None and not bb.empty:
            # Dynamically detect BB column names
            lower_key = next((c for c in bb.columns if str(c).startswith("BBL_")), None)
            mid_key = next((c for c in bb.columns if str(c).startswith("BBM_")), None)
            upper_key = next((c for c in bb.columns if str(c).startswith("BBU_")), None)

            if lower_key and mid_key and upper_key:
                out["bb_lower"] = bb[lower_key]
                out["bb_mid"] = bb[mid_key]
                out["bb_upper"] = bb[upper_key]
            else:
                raise KeyError("BB columns missing")
        else:
            raise KeyError("BB calculation failed")
    except Exception as e:
        print(f"Bollinger Bands failed, using manual calculation: {e}")
        # Manual fallback calculation
        mid = out["close"].rolling(20).mean()
        std = out["close"].rolling(20).std()
        out["bb_mid"] = mid
        out["bb_lower"] = mid - 2.0 * std
        out["bb_upper"] = mid + 2.0 * std
    # Calculate BB width safely
    try:
        out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_mid"]
    except Exception as e:
        print(f"BB width calculation failed: {e}")
        out["bb_width"] = pd.NA

    # ATR with error handling
    try:
        atr_result = ta.atr(out["high"], out["low"], out["close"], length=14)
        out["atr14"] = atr_result
    except Exception as e:
        print(f"ATR calculation failed: {e}")
        out["atr14"] = pd.NA

    # ADX with error handling
    try:
        adx_result = ta.adx(out["high"], out["low"], out["close"], length=14)
        if adx_result is not None and not adx_result.empty:
            # Find ADX column
            adx_col = None
            for col in adx_result.columns:
                if 'ADX' in str(col):
                    adx_col = col
                    break
            if adx_col:
                out["adx14"] = adx_result[adx_col]
            else:
                print("ADX column not found")
                out["adx14"] = pd.NA
        else:
            print("ADX calculation returned None or empty")
            out["adx14"] = pd.NA
    except Exception as e:
        print(f"ADX calculation failed: {e}")
        out["adx14"] = pd.NA

    # Hull Moving Average (HMA) calculation
    try:
        # HMA formula: WMA(2 * WMA(src, L/2) - WMA(src, L), sqrt(L))
        # Using length 55 as default (can be parameterized)
        length = 55
        src = out["close"]

        # Calculate WMA components
        half_length = int(length / 2)
        sqrt_length = int(np.sqrt(length))

        wma_half = ta.wma(src, length=half_length)
        wma_full = ta.wma(src, length=length)

        if wma_half is not None and wma_full is not None:
            # 2 * WMA(half) - WMA(full)
            diff = 2 * wma_half - wma_full
            # WMA of the difference with sqrt(length)
            hma = ta.wma(diff, length=sqrt_length)
            out["hma55"] = hma
        else:
            print("HMA WMA calculations failed")
            out["hma55"] = pd.NA
    except Exception as e:
        print(f"HMA calculation failed: {e}")
        out["hma55"] = pd.NA

    # VWAP calculation with error handling
    try:
        # Ensure ordered DatetimeIndex for TA functions that require it
        had_index = False
        if "ts" in out.columns:
            try:
                out["ts"] = pd.to_datetime(out["ts"], utc=True)
                # Set index to 'ts' and drop the column to avoid duplicates on reset
                out = out.set_index("ts", drop=True).sort_index()
                had_index = True
            except Exception:
                had_index = False

        vwap = ta.vwap(out["high"], out["low"], out["close"], out["volume"])
        out["vwap"] = vwap

        # Restore original index if we changed it
        if had_index:
            out = out.reset_index()  # index name 'ts' becomes a 'ts' column
    except Exception as e:
        print(f"VWAP calculation failed, using manual calculation: {e}")
        try:
            # Manual VWAP fallback
            tp = (out["high"].astype(float) + out["low"].astype(float) + out["close"].astype(float)) / 3.0
            vol = out["volume"].astype(float).fillna(0.0)
            cum_pv = (tp * vol).cumsum()
            cum_v = vol.cumsum().replace(0, pd.NA)
            out["vwap"] = cum_pv / cum_v
        except Exception as e2:
            print(f"Manual VWAP calculation also failed: {e2}")
            out["vwap"] = pd.NA
    return out


@dataclass
class BTTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp | None
    side: Literal['LONG','SHORT']
    entry_price: float
    exit_price: float | None
    pnl: float | None
    bars_held: int
    exit_reason: str = ""  # Track how trade exited (stop/target/signal/market)


def strategy_signals(df: pd.DataFrame, name: str, min_confidence: float = 0.8) -> pd.Series:
    """Use live strategy engine with confidence scoring for signal generation"""
    # Pre-calculate indicators once on full dataframe for performance
    df_with_indicators = add_indicators(df)
    s = pd.Series(index=df_with_indicators.index, dtype='object')

    # Map strategy names to functions
    strategy_funcs = {
        'hull_suite': hull_suite,  # Focus on Hull Suite strategy
        'mean_reversion': mean_reversion,
        'macd_trend': macd_trend
    }
    if name not in strategy_funcs:
        raise ValueError(f"Unknown strategy {name}")

    strat_func = strategy_funcs[name]

    # Generate signals using live strategy logic with confidence scoring
    # Optimized: check each historical candle without recalculating indicators
    for i in range(len(df_with_indicators)):
        try:
            if i % 100 == 0:  # Progress every 100 candles
                print(f"    Processing candle {i}/{len(df_with_indicators)}")
            signal = strat_func(df_with_indicators, current_index=i)
            if signal and signal_quality_filter(signal, df_with_indicators.iloc[:i+1]):
                # Apply confidence scoring with updated weights
                confidence, rationale = score_signal(df_with_indicators.iloc[:i+1], signal.action, signal.confidence, {'ticker': 'TEST', 'exchange': 'NSE'})
                # Use stricter confidence threshold for profitability
                if confidence >= min_confidence:
                    s.iloc[i] = 'BUY' if signal.action == 'BUY' else 'SELL'
        except Exception as e:
            if i % 100 == 0:
                print(f"    Error at candle {i}: {e}")
            continue

    return s


def backtest_strategy(df_raw: pd.DataFrame, name: str, sl_atr: float = 1.0, tp_rr: float = 2.0) -> Tuple[List[BTTrade], pd.Series]:
    df = add_indicators(df_raw)
    sig = strategy_signals(df, name, min_confidence=0.7)  # Lower confidence for more trades
    entry_side: str | None = None
    entry_px: float = 0.0
    entry_idx: int = -1
    trades: List[BTTrade] = []
    equity = [1_000_000.0]
    capital = 1_000_000.0
    risk_fraction = 0.01

    # Trading costs and slippage - balanced for realistic profitability
    brokerage_per_trade = 0.00003  # 0.003% per trade (very competitive)
    slippage_bps = 0.5  # 0.5 bps slippage for limit orders (tight spreads)

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        price = float(row['close'])
        atr = float(row['atr14']) if not pd.isna(row['atr14']) else price * 0.01

        # exit checks if in position
        if entry_side is not None:
            rr = tp_rr
            if entry_side == 'LONG':
                stop = entry_px - sl_atr * atr
                target = entry_px + rr * (entry_px - stop)
                hit_stop = price <= stop or row['low'] <= stop
                hit_tp = price >= target or row['high'] >= target
                if hit_stop or hit_tp or (sig.iloc[i] == 'SELL'):
                    # Market order exit with slippage
                    exit_px = stop if hit_stop else (target if hit_tp else price)
                    # Add slippage for market orders (worse execution)
                    slippage_adj = exit_px * (slippage_bps / 10000)
                    if hit_stop:
                        exit_px += slippage_adj  # Slippage against us on stop
                    elif hit_tp:
                        exit_px -= slippage_adj  # Slippage against us on target
                    else:
                        exit_px += slippage_adj if sig.iloc[i] == 'SELL' else -slippage_adj

                    pnl = (exit_px - entry_px) - (entry_px + exit_px) * brokerage_per_trade  # Gross P&L minus fees
                    bars = i - entry_idx
                    exit_reason = "target" if hit_tp else ("stop" if hit_stop else "signal")
                    trades.append(BTTrade(df.iloc[entry_idx]['ts'], row['ts'], 'LONG', entry_px, exit_px, pnl, bars, exit_reason))
                    capital += pnl
                    entry_side = None
            else:  # SHORT
                stop = entry_px + sl_atr * atr
                target = entry_px - rr * (stop - entry_px)
                hit_stop = price >= stop or row['high'] >= stop
                hit_tp = price <= target or row['low'] <= target
                if hit_stop or hit_tp or (sig.iloc[i] == 'BUY'):
                    exit_px = stop if hit_stop else (target if hit_tp else price)
                    # Add slippage for market orders
                    slippage_adj = exit_px * (slippage_bps / 10000)
                    if hit_stop:
                        exit_px -= slippage_adj  # Slippage against us on stop
                    elif hit_tp:
                        exit_px += slippage_adj  # Slippage against us on target
                    else:
                        exit_px -= slippage_adj if sig.iloc[i] == 'BUY' else slippage_adj

                    pnl = (entry_px - exit_px) - (entry_px + exit_px) * brokerage_per_trade
                    bars = i - entry_idx
                    exit_reason = "target" if hit_tp else ("stop" if hit_stop else "signal")
                    trades.append(BTTrade(df.iloc[entry_idx]['ts'], row['ts'], 'SHORT', entry_px, exit_px, pnl, bars, exit_reason))
                    capital += pnl
                    entry_side = None

        # entry with limit order simulation and minimum profit check
        if entry_side is None and isinstance(sig.iloc[i], str):
            side = sig.iloc[i]
            entry_side = 'LONG' if side == 'BUY' else 'SHORT'

            # Simulate limit order entry (signal entry price is the limit)
            # Add small slippage to simulate limit order execution
            base_price = price
            limit_slippage = base_price * (slippage_bps / 10000)  # 1 bps

            if entry_side == 'LONG':
                # BUY limit: expect to get filled at ask or slightly worse
                entry_px = base_price + limit_slippage
            else:
                # SELL limit: expect to get filled at bid or slightly worse
                entry_px = base_price - limit_slippage

            # Calculate expected profit before entering trade
            atr_val = atr if not pd.isna(atr) else price * 0.01
            stop_distance = sl_atr * atr_val
            expected_profit = tp_rr * stop_distance  # 4:1 risk-reward
            expected_costs = (entry_px + entry_px * (1 + tp_rr)) * brokerage_per_trade + 2 * entry_px * (slippage_bps / 10000)

            # Minimum profit threshold: relaxed for more trades
            if expected_profit > expected_costs * 1.2:  # At least 1.2x cost coverage (allow more trades)
                # Subtract brokerage on entry
                capital -= entry_px * brokerage_per_trade
                entry_idx = i
            else:
                # Skip trade - costs too high relative to profit potential
                entry_side = None

        equity.append(capital)
    equity_series = pd.Series(equity, index=df['ts'])
    return trades, equity_series


def sharpe(equity: pd.Series) -> float:
    r = equity.pct_change().dropna()
    if r.std() == 0 or r.empty:
        return 0.0
    return float((r.mean() / r.std()) * np.sqrt(252))


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    roll = equity.cummax()
    dd = (equity - roll) / roll
    return float(dd.min() * 100.0)


def cagr(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    start = float(equity.iloc[0]); end = float(equity.iloc[-1])
    days = max(1, (equity.index[-1] - equity.index[0]).days)
    years = days / 365.25
    if start <= 0 or years <= 0:
        return 0.0
    return float(((end / start) ** (1/years) - 1.0) * 100.0)


def run_backtests(strategies: List[str], timeframes: List[Timeframe], symbols_limit: int = 20, start_date: str | None = None, end_date: str | None = None) -> Dict:
    syms = load_symbols(limit=symbols_limit)
    total_symbols = len(syms)
    results: Dict = {"per_strategy": {}, "per_symbol": {}}

    print(f"🚀 STARTING BACKTESTS WITH LIVE STRATEGIES")
    print(f"📊 Total symbols to process: {total_symbols}")
    print(f"🧠 Strategies: {strategies}")
    print(f"⏰ Timeframes: {timeframes}")

    for i, s in enumerate(syms, 1):
        ticker = s['ticker']
        print(f"\n📈 ANALYZING {ticker} ({i} of {total_symbols})")
        results["per_symbol"][ticker] = {}

        for strat in strategies:
            print(f"  🧠 Testing {strat} strategy...")
            strat_trades = 0
            strat_equity = None

            for tf in timeframes:
                df = load_candles(s['id'], tf, days=720, start_date=start_date, end_date=end_date)
                if df.empty or len(df) < 60:  # Need minimum 60 candles
                    print(f"    ⚠️ Insufficient {tf} data for {strat}")
                    continue

                print(f"    📊 {tf}: {len(df)} candles")
                # Add progress indicator to avoid large output
                print(f"    🔄 Processing {len(df)} candles...")
                trades, eq = backtest_strategy(df, strat)
                strat_trades += len(trades)
                print(f"    ✅ Completed {len(trades)} trades")

                if strat_equity is None:
                    strat_equity = eq
                else:
                    # Combine equity curves properly
                    combined = pd.Series(index=eq.index, dtype=float)
                    for idx in eq.index:
                        if idx in strat_equity.index:
                            combined[idx] = strat_equity[idx] + (eq[idx] - 1000000)  # Adjust for starting capital
                        else:
                            combined[idx] = eq[idx]
                    strat_equity = combined

            if strat_equity is not None and strat_trades > 0:
                results["per_symbol"][ticker][strat] = {
                    "sharpe": sharpe(strat_equity),
                    "max_dd_pct": max_drawdown(strat_equity),
                    "cagr_pct": cagr(strat_equity),
                    "trades": strat_trades,
                }
                print(f"    ✅ {strat}: {strat_trades} trades, Sharpe: {sharpe(strat_equity):.2f}")
            else:
                print(f"    ❌ {strat}: No valid trades")

    # Calculate aggregate strategy performance
    for strat in strategies:
        agg_equity = None
        total_trades = 0

        for ticker, ticker_results in results["per_symbol"].items():
            if strat in ticker_results:
                eq = None
                # Reconstruct equity curve for this strategy across all symbols
                for tf in timeframes:
                    # This is a simplified approach - in reality we'd need more sophisticated equity combination
                    pass

                total_trades += ticker_results[strat]["trades"]

        if total_trades > 0:
            results["per_strategy"][strat] = {
                "total_trades": total_trades,
            }

    return results


