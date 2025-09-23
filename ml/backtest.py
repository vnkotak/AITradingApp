from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import pandas_ta as ta
from supabase import create_client
import os


Timeframe = Literal['1m','5m','15m','1h','1d']


def supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE env")
    return create_client(url, key)


def load_symbols(limit: int = 20) -> List[Dict]:
    sb = supabase_client()
    return sb.table("symbols").select("id,ticker,exchange").eq("is_active", True).limit(limit).execute().data or []


def load_candles(symbol_id: str, tf: Timeframe, days: int = 1200) -> pd.DataFrame:
    sb = supabase_client()
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
    out = df.copy()
    out["ema20"] = ta.ema(out["close"], length=20)
    out["ema50"] = ta.ema(out["close"], length=50)
    out["rsi14"] = ta.rsi(out["close"], length=14)
    macd = ta.macd(out["close"], fast=12, slow=26, signal=9)
    out["macd"] = macd["MACD_12_26_9"]
    out["macd_signal"] = macd["MACDs_12_26_9"]
    out["macd_hist"] = macd["MACDh_12_26_9"]
    bb = ta.bbands(out["close"], length=20, std=2.0)
    out["bb_lower"] = bb["BBL_20_2.0"]
    out["bb_mid"] = bb["BBM_20_2.0"]
    out["bb_upper"] = bb["BBU_20_2.0"]
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_mid"]
    out["atr14"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    out["adx14"] = ta.adx(out["high"], out["low"], out["close"], length=14)["ADX_14"]
    try:
        out["vwap"] = ta.vwap(out["high"], out["low"], out["close"], out["volume"])  # type: ignore
    except Exception:
        out["vwap"] = np.nan
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


def strategy_signals(df: pd.DataFrame, name: str) -> pd.Series:
    s = pd.Series(index=df.index, dtype='object')
    if name == 'trend_follow':
        cross_up = (df['ema20'] > df['ema50']) & (df['ema20'].shift(1) <= df['ema50'].shift(1)) & (df['adx14'] > 20)
        cross_dn = (df['ema20'] < df['ema50']) & (df['ema20'].shift(1) >= df['ema50'].shift(1)) & (df['adx14'] > 20)
        s[cross_up] = 'BUY'
        s[cross_dn] = 'SELL'
    elif name == 'mean_reversion':
        s[(df['rsi14'] < 25) & (df['close'] < df['bb_lower'])] = 'BUY'
        s[(df['rsi14'] > 75) & (df['close'] > df['bb_upper'])] = 'SELL'
    elif name == 'momentum':
        vol_ma = df['volume'].rolling(20).mean()
        vol_z = (df['volume'] - vol_ma) / (df['volume'].rolling(20).std() + 1e-9)
        buy = (df['close'] > df['vwap']) & (df['ema20'] > df['ema50']) & (vol_z > 1.5)
        sell = (df['close'] < df['vwap']) & (df['ema20'] < df['ema50']) & (vol_z > 1.5)
        s[buy] = 'BUY'
        s[sell] = 'SELL'
    else:
        raise ValueError(f"Unknown strategy {name}")
    # shift to avoid lookahead (signal acts on next bar)
    return s.shift(1)


def backtest_strategy(df_raw: pd.DataFrame, name: str, sl_atr: float = 1.5, tp_rr: float = 2.0) -> Tuple[List[BTTrade], pd.Series]:
    df = add_indicators(df_raw)
    sig = strategy_signals(df, name)
    entry_side: str | None = None
    entry_px: float = 0.0
    entry_idx: int = -1
    trades: List[BTTrade] = []
    equity = [1_000_000.0]
    capital = 1_000_000.0
    risk_fraction = 0.01
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
                    exit_px = stop if hit_stop else (target if hit_tp else price)
                    pnl = (exit_px - entry_px)
                    bars = i - entry_idx
                    trades.append(BTTrade(df.iloc[entry_idx]['ts'], row['ts'], 'LONG', entry_px, exit_px, pnl, bars))
                    capital += pnl
                    entry_side = None
            else:
                stop = entry_px + sl_atr * atr
                target = entry_px - rr * (stop - entry_px)
                hit_stop = price >= stop or row['high'] >= stop
                hit_tp = price <= target or row['low'] <= target
                if hit_stop or hit_tp or (sig.iloc[i] == 'BUY'):
                    exit_px = stop if hit_stop else (target if hit_tp else price)
                    pnl = (entry_px - exit_px)
                    bars = i - entry_idx
                    trades.append(BTTrade(df.iloc[entry_idx]['ts'], row['ts'], 'SHORT', entry_px, exit_px, pnl, bars))
                    capital += pnl
                    entry_side = None
        # entry
        if entry_side is None and isinstance(sig.iloc[i], str):
            side = sig.iloc[i]
            entry_side = 'LONG' if side == 'BUY' else 'SHORT'
            entry_px = price
            entry_idx = i
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


def run_backtests(strategies: List[str], timeframes: List[Timeframe], symbols_limit: int = 20) -> Dict:
    syms = load_symbols(limit=symbols_limit)
    results: Dict = {"per_strategy": {}, "per_symbol": {}}
    for strat in strategies:
        agg_equity = None
        strat_trades = 0
        for s in syms:
            per_tf_equity = []
            for tf in timeframes:
                df = load_candles(s['id'], tf, days=720)
                if df.empty or len(df) < 200:
                    continue
                trades, eq = backtest_strategy(df, strat)
                strat_trades += len(trades)
                per_tf_equity.append(eq)
            if per_tf_equity:
                # align indexes
                eq_merged = per_tf_equity[0]
                for eq in per_tf_equity[1:]:
                    eq_merged = eq_merged.add(eq.reindex_like(eq_merged).fillna(method='ffill'), fill_value=0)
                results["per_symbol"].setdefault(s['ticker'], {})[strat] = {
                    "sharpe": sharpe(eq_merged),
                    "max_dd_pct": max_drawdown(eq_merged),
                    "cagr_pct": cagr(eq_merged),
                    "trades": strat_trades,
                }
                agg_equity = eq_merged if agg_equity is None else agg_equity.add(eq_merged.reindex_like(agg_equity).fillna(method='ffill'), fill_value=0)
        if agg_equity is not None:
            results["per_strategy"][strat] = {
                "sharpe": sharpe(agg_equity),
                "max_dd_pct": max_drawdown(agg_equity),
                "cagr_pct": cagr(agg_equity),
                "trades": strat_trades,
            }
    return results


