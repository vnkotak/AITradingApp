from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Literal, Dict, Tuple

import pandas as pd

from .supabase_client import get_client


@dataclass
class RiskLimitsCfg:
    max_capital_per_trade_pct: float
    max_daily_loss_pct: float
    max_portfolio_drawdown_pct: float
    max_sector_exposure_pct: float
    circuit_breaker_pct: float
    kelly_fraction: float
    pause_all: bool


def get_limits() -> RiskLimitsCfg:
    sb = get_client()
    row = sb.table("risk_limits").select("* ").limit(1).execute().data
    if not row:
        # Defaults
        return RiskLimitsCfg(5, 3, 15, 25, 20, 0.5, False)
    r = row[0]
    return RiskLimitsCfg(
        float(r.get("max_capital_per_trade_pct", 5)),
        float(r.get("max_daily_loss_pct", 3)),
        float(r.get("max_portfolio_drawdown_pct", 15)),
        float(r.get("max_sector_exposure_pct", 25)),
        float(r.get("circuit_breaker_pct", 20)),
        float(r.get("kelly_fraction", 0.5)),
        bool(r.get("pause_all", False)),
    )


def portfolio_snapshot() -> Dict:
    sb = get_client()
    positions = sb.table("positions").select("symbol_id,avg_price,qty,realized_pnl").execute().data or []
    total_unreal = 0.0
    total_exposure = 0.0
    # attach latest prices
    for p in positions:
        sid = p["symbol_id"]
        last = sb.table("candles").select("close").eq("symbol_id", sid).eq("timeframe", "1m").order("ts", desc=True).limit(1).execute().data
        price = float(last[0]["close"]) if last else float(p.get("avg_price", 0) or 0)
        qty = float(p.get("qty", 0) or 0)
        avg = float(p.get("avg_price", 0) or 0)
        unreal = (price - avg) * (qty if qty >= 0 else -qty) * (1 if qty >= 0 else -1)
        total_unreal += unreal
        total_exposure += abs(price * qty)
    # equity approximation
    start = sb.table("pnl_daily").select("equity").order("trade_date", desc=True).limit(1).execute().data
    last_equity = float(start[0]["equity"]) if start else 1000000.0  # default virtual capital 10L
    realized_today = 0.0
    today = date.today()
    today_row = sb.table("pnl_daily").select("realized_pnl,unrealized_pnl").eq("trade_date", today.isoformat()).limit(1).execute().data
    if today_row:
        realized_today = float(today_row[0].get("realized_pnl", 0) or 0)
    equity_now = last_equity + realized_today + total_unreal
    return {"equity": equity_now, "exposure": total_exposure, "unrealized": total_unreal, "realized_today": realized_today}


def circuit_breaker_triggered(ticker: str, exchange: str, threshold_pct: float) -> bool:
    sb = get_client()
    sym = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
    if not sym:
        return False
    sid = sym["id"]
    # Previous daily close vs latest price
    daily = sb.table("candles").select("ts,close").eq("symbol_id", sid).eq("timeframe", "1d").order("ts", desc=True).limit(2).execute().data
    last_min = sb.table("candles").select("close").eq("symbol_id", sid).eq("timeframe", "1m").order("ts", desc=True).limit(1).execute().data
    if not daily or not last_min:
        return False
    prev_close = float(daily[1]["close"]) if len(daily) >= 2 else float(daily[0]["close"])
    ltp = float(last_min[0]["close"]) if last_min else prev_close
    change_pct = abs((ltp - prev_close) / prev_close) * 100.0 if prev_close else 0.0
    return change_pct >= threshold_pct


def suggest_position_size(ticker: str, exchange: str, price: float, atr: float | None, sector: str | None, limits: RiskLimitsCfg | None = None) -> float:
    limits = limits or get_limits()
    snap = portfolio_snapshot()
    equity = float(snap["equity"]) or 0.0
    per_trade_cap = equity * (limits.max_capital_per_trade_pct / 100.0)
    risk_per_share = atr if (atr and atr > 0) else price * 0.01
    # Kelly-style scaling with cap
    k_fraction = max(0.1, min(1.0, limits.kelly_fraction))
    risk_budget = per_trade_cap * k_fraction
    qty = max(0.0, risk_budget / max(1e-6, risk_per_share))
    # round down to lot size if exists
    sb = get_client()
    sym = sb.table("symbols").select("lot_size").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
    lot = int(sym.get("lot_size") or 1) if sym else 1
    qty = (int(qty) // lot) * lot
    return float(max(0, qty))


def daily_drawdown_exceeded(limits: RiskLimitsCfg | None = None) -> bool:
    limits = limits or get_limits()
    snap = portfolio_snapshot()
    equity_now = snap["equity"]
    sb = get_client()
    prev = sb.table("pnl_daily").select("equity").order("trade_date", desc=True).limit(1).execute().data
    start_equity = float(prev[0]["equity"]) if prev else equity_now
    dd = (equity_now - start_equity) / start_equity * 100.0 if start_equity else 0.0
    return dd <= -limits.max_daily_loss_pct


def should_block_order(ticker: str, exchange: str, side: Literal['BUY','SELL']) -> Tuple[bool, str | None]:
    limits = get_limits()
    if limits.pause_all:
        return True, "Trading paused"
    if daily_drawdown_exceeded(limits):
        return True, "Daily drawdown limit exceeded"
    if circuit_breaker_triggered(ticker, exchange, limits.circuit_breaker_pct):
        return True, f"Circuit breaker {limits.circuit_breaker_pct}% triggered"
    return False, None


def trailing_stop_price(entry_price: float, atr: float, side: Literal['LONG','SHORT'], multiple: float = 2.0, highest_close: float | None = None, lowest_close: float | None = None) -> float:
    if side == 'LONG':
        base = (highest_close if highest_close is not None else entry_price)
        return float(base - multiple * atr)
    else:
        base = (lowest_close if lowest_close is not None else entry_price)
        return float(base + multiple * atr)


def apply_trailing_stops(timeframe: str = '1m') -> int:
    sb = get_client()
    positions = sb.table("positions").select("id,symbol_id,avg_price,qty").execute().data or []
    exited = 0
    for p in positions:
        qty = float(p["qty"] or 0)
        if qty == 0:
            continue
        sid = p["symbol_id"]
        df = sb.table("candles").select("ts,close,high,low").eq("symbol_id", sid).eq("timeframe", timeframe).order("ts", desc=True).limit(100).execute().data
        df = pd.DataFrame(df or [])
        if df.empty:
            continue
        df = df.sort_values("ts").reset_index(drop=True)
        atr = float(pd.concat([
            (df['high'].astype(float) - df['low'].astype(float)),
            (df['high'].astype(float) - df['close'].astype(float).shift(1)).abs(),
            (df['low'].astype(float) - df['close'].astype(float).shift(1)).abs(),
        ], axis=1).max(axis=1).rolling(14).mean().iloc[-1])
        last_close = float(df.iloc[-1]['close'])
        entry = float(p["avg_price"]) or last_close
        side = 'LONG' if qty > 0 else 'SHORT'
        if side == 'LONG':
            highest = float(df['close'].astype(float).rolling(20).max().iloc[-1])
            tsl = trailing_stop_price(entry, atr, 'LONG', multiple=2.0, highest_close=highest)
            if last_close <= tsl:
                # market exit
                sb.table("orders").insert({"symbol_id": sid, "side": "SELL", "type": "MARKET", "price": last_close, "qty": abs(qty), "status": "FILLED"}).execute()
                sb.table("trades").insert({"symbol_id": sid, "side": "SELL", "price": last_close, "qty": abs(qty)}).execute()
                # update position
                remaining = 0.0
                realized = (last_close - entry) * abs(qty)
                sb.table("positions").update({"qty": remaining, "realized_pnl": (float(p.get('realized_pnl',0)) + realized), "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", p["id"]).execute()
                exited += 1
        else:
            lowest = float(df['close'].astype(float).rolling(20).min().iloc[-1])
            tsl = trailing_stop_price(entry, atr, 'SHORT', multiple=2.0, lowest_close=lowest)
            if last_close >= tsl:
                sb.table("orders").insert({"symbol_id": sid, "side": "BUY", "type": "MARKET", "price": last_close, "qty": abs(qty), "status": "FILLED"}).execute()
                sb.table("trades").insert({"symbol_id": sid, "side": "BUY", "price": last_close, "qty": abs(qty)}).execute()
                remaining = 0.0
                realized = (entry - last_close) * abs(qty)
                sb.table("positions").update({"qty": remaining, "realized_pnl": (float(p.get('realized_pnl',0)) + realized), "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", p["id"]).execute()
                exited += 1
    return exited


