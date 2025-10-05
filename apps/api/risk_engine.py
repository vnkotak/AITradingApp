from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Literal, Dict, Tuple
import time

import pandas as pd

from apps.api.supabase_client import get_client


@dataclass
class RiskLimitsCfg:
    max_capital_per_trade_pct: float
    max_daily_loss_pct: float
    max_portfolio_drawdown_pct: float
    max_sector_exposure_pct: float
    circuit_breaker_pct: float
    kelly_fraction: float


def get_limits() -> RiskLimitsCfg:
    sb = get_client()
    row = sb.table("risk_limits").select("* ").limit(1).execute().data
    if not row:
        # Defaults
        return RiskLimitsCfg(5, 3, 15, 25, 20, 0.5)
    r = row[0]
    return RiskLimitsCfg(
        float(r.get("max_capital_per_trade_pct", 5)),
        float(r.get("max_daily_loss_pct", 3)),
        float(r.get("max_portfolio_drawdown_pct", 15)),
        float(r.get("max_sector_exposure_pct", 25)),
        float(r.get("circuit_breaker_pct", 20)),
        float(r.get("kelly_fraction", 0.5)),
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


def suggest_position_size(ticker: str, exchange: str, price: float, atr: float | None = None, sector: str | None = None, timeframe: str = '1m', limits: RiskLimitsCfg | None = None) -> float:
    print(f"🔍 [RISK_ENGINE] suggest_position_size called for {ticker}.{exchange}, price={price}")
    start_time = time.time()

    if not price or price <= 0:
        print(f"⚠️ [RISK_ENGINE] Invalid price: {price}, returning 1.0")
        return 1.0

    # Primary logic: Adjust target trade value based on timeframe
    base_target_value = 10000.0

    # Timeframe-based position sizing multipliers
    timeframe_multipliers = {
        '1m': 0.3,   # 30% of base - very conservative for fast timeframe
        '5m': 0.5,   # 50% of base - moderate for 5min
        '15m': 0.8,  # 80% of base - higher for 15min
        '1h': 1.0,   # 100% of base - full size for hourly
        '1d': 1.2    # 120% of base - largest for daily
    }

    multiplier = timeframe_multipliers.get(timeframe, 0.5)  # Default to 50% if unknown
    target_value = base_target_value * multiplier

    suggested_qty = target_value / price
    print(f"💰 [RISK_ENGINE] Timeframe: {timeframe}, multiplier: {multiplier}, target value: ₹{target_value}, calculated qty: {suggested_qty}")

    # Round to reasonable precision (max 4 decimal places for low-priced stocks)
    if suggested_qty >= 100:
        suggested_qty = round(suggested_qty)  # Round to whole numbers for qty >= 100
        print(f"🔢 [RISK_ENGINE] Rounded to whole number: {suggested_qty}")
    elif suggested_qty >= 10:
        suggested_qty = round(suggested_qty, 1)  # Round to 1 decimal for qty 10-99
        print(f"🔢 [RISK_ENGINE] Rounded to 1 decimal: {suggested_qty}")
    elif suggested_qty >= 1:
        suggested_qty = round(suggested_qty, 2)  # Round to 2 decimals for qty 1-9
        print(f"🔢 [RISK_ENGINE] Rounded to 2 decimals: {suggested_qty}")
    else:
        suggested_qty = round(suggested_qty, 4)  # Round to 4 decimals for fractional qty
        print(f"🔢 [RISK_ENGINE] Rounded to 4 decimals: {suggested_qty}")

    # Apply lot size constraints if available
    sb = get_client()
    if sb:
        try:
            print(f"📊 [RISK_ENGINE] Looking up lot size for {ticker}.{exchange}")
            lot_start = time.time()
            sym = sb.table("symbols").select("lot_size").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
            lot_end = time.time()
            lot_size = int(sym.get("lot_size") or 1) if sym else 1
            print(f"✅ [RISK_ENGINE] Lot size lookup completed in {lot_end-lot_start:.2f}s: {lot_size}")

            if lot_size > 1:
                original_qty = suggested_qty
                suggested_qty = (int(suggested_qty) // lot_size) * lot_size
                print(f"📊 [RISK_ENGINE] Applied lot size {lot_size}: {original_qty} -> {suggested_qty}")
        except Exception as e:
            print(f"⚠️ [RISK_ENGINE] Lot size lookup failed: {e}")
            pass  # If lot size lookup fails, use calculated quantity

    # Fallback to risk management if suggested quantity seems unreasonable
    if suggested_qty <= 0 or suggested_qty > 10000:
        print(f"⚠️ [RISK_ENGINE] Quantity {suggested_qty} seems unreasonable, using fallback risk management")
        # Fallback to original risk management logic
        limits = limits or get_limits()
        print(f"📊 [RISK_ENGINE] Getting portfolio snapshot for fallback calculation")
        snap_start = time.time()
        snap = portfolio_snapshot()
        snap_end = time.time()
        print(f"✅ [RISK_ENGINE] Portfolio snapshot completed in {snap_end-snap_start:.2f}s")

        equity = float(snap["equity"]) or 0.0
        per_trade_cap = equity * (limits.max_capital_per_trade_pct / 100.0)
        risk_per_share = atr if (atr and atr > 0) else price * 0.01
        k_fraction = max(0.1, min(1.0, limits.kelly_fraction))
        risk_budget = per_trade_cap * k_fraction
        qty = max(1.0, risk_budget / max(1e-6, risk_per_share))
        print(f"📊 [RISK_ENGINE] Fallback calculation: equity={equity}, per_trade_cap={per_trade_cap}, qty={qty}")

        # Apply lot size to fallback quantity too
        sb = get_client()
        if sb:
            try:
                sym = sb.table("symbols").select("lot_size").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
                lot = int(sym.get("lot_size") or 1) if sym else 1
                qty = (int(qty) // lot) * lot
                print(f"📊 [RISK_ENGINE] Applied lot size to fallback: {qty}")
            except:
                pass

        suggested_qty = qty

    end_time = time.time()
    print(f"✅ [RISK_ENGINE] suggest_position_size completed in {end_time-start_time:.2f}s, returning: {suggested_qty}")
    return float(max(1, suggested_qty))


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


