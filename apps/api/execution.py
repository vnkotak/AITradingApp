from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple, Dict
from datetime import datetime, timezone

import pandas as pd

from .supabase_client import get_client


@dataclass
class FillResult:
    status: Literal['FILLED','PARTIAL','REJECTED']
    fill_price: float | None
    filled_qty: float
    slippage_bps: float | None
    notes: Dict


def _latest_candle(symbol_id: str, timeframe: str) -> dict | None:
    sb = get_client()
    data = (
        sb.table("candles").select("ts,open,high,low,close,volume")
        .eq("symbol_id", symbol_id).eq("timeframe", timeframe)
        .order("ts", desc=True).limit(1).execute().data
    )
    return data[0] if data else None


def _recent_df(symbol_id: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
    sb = get_client()
    data = (
        sb.table("candles").select("ts,open,high,low,close,volume")
        .eq("symbol_id", symbol_id).eq("timeframe", timeframe)
        .order("ts", desc=True).limit(limit).execute().data
    )
    df = pd.DataFrame(data or [])
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df.sort_values("ts").reset_index(drop=True)


def _synthetic_book_and_atr(symbol_id: str, timeframe: str = '1m') -> Tuple[float, float, float]:
    df = _recent_df(symbol_id, timeframe, limit=100)
    if df.empty:
        raise ValueError("No recent candles for price discovery")
    last = df.iloc[-1]
    close = float(last["close"])
    # ATR proxy from last 14 candles
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    closes = df["close"].astype(float)
    tr = pd.concat([
        (highs - lows),
        (highs - closes.shift(1)).abs(),
        (lows - closes.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1]) if len(tr) >= 14 else float(tr.mean())
    atr = atr or max(0.005 * close, 0.01)  # fallback
    # Spread as fraction of ATR
    spread = max(0.1 * atr, 0.0005 * close)
    bid = close - spread / 2
    ask = close + spread / 2
    return bid, ask, atr


def _slippage_bps(order_qty: float, close: float, atr: float, avg_vol: float | None) -> float:
    notional = abs(order_qty) * close
    base_bps = 5.0 * (atr / close) * 10000.0  # scales with volatility
    size_factor = 1.0
    if avg_vol and avg_vol > 0:
        size_factor += min(3.0, notional / (avg_vol * close))  # larger than typical per-bar volume hurts
    return float(min(150.0, base_bps * size_factor))


def simulate_order(symbol_id: str, side: Literal['BUY','SELL'], order_type: Literal['MARKET','LIMIT'], qty: float, limit_price: float | None = None, timeframe: str = '1m') -> FillResult:
    bid, ask, atr = _synthetic_book_and_atr(symbol_id, timeframe)
    mid = (bid + ask) / 2.0
    sb = get_client()
    # average recent volume
    vols = sb.table("candles").select("volume").eq("symbol_id", symbol_id).eq("timeframe", timeframe).order("ts", desc=True).limit(30).execute().data
    avg_vol = float(pd.DataFrame(vols)["volume"].astype(float).mean()) if vols else None
    # Determine execution price
    if order_type == 'MARKET':
        base_price = ask if side == 'BUY' else bid
        bps = _slippage_bps(qty, mid, atr, avg_vol)
        slip = base_price * (bps / 10000.0)
        fill_price = base_price + slip if side == 'BUY' else base_price - slip
        return FillResult('FILLED', float(fill_price), float(qty), float(bps), {"bid": bid, "ask": ask, "atr": atr})
    else:
        if limit_price is None:
            return FillResult('REJECTED', None, 0.0, None, {"reason": "Limit price required"})
        # Fill if price is marketable against book
        if side == 'BUY':
            if limit_price >= ask:
                bps = _slippage_bps(qty, mid, atr, avg_vol)
                slip = ask * (bps / 10000.0)
                return FillResult('FILLED', float(min(limit_price, ask + slip)), float(qty), float(bps), {"book": [bid, ask]})
            else:
                return FillResult('REJECTED', None, 0.0, None, {"reason": "Limit too low", "ask": ask})
        else:
            if limit_price <= bid:
                bps = _slippage_bps(qty, mid, atr, avg_vol)
                slip = bid * (bps / 10000.0)
                return FillResult('FILLED', float(max(limit_price, bid - slip)), float(qty), float(bps), {"book": [bid, ask]})
            else:
                return FillResult('REJECTED', None, 0.0, None, {"reason": "Limit too high", "bid": bid})


def apply_trade_updates(symbol_id: str, side: str, fill_price: float, qty: float) -> None:
    sb = get_client()
    # Load or create position
    pos = sb.table("positions").select("id,avg_price,qty,realized_pnl").eq("symbol_id", symbol_id).limit(1).execute().data
    if pos:
        pos = pos[0]
        curr_qty = float(pos["qty"]) or 0.0
        avg = float(pos["avg_price"]) or 0.0
        realized = float(pos["realized_pnl"]) or 0.0
        trade_qty = qty if side == 'BUY' else -qty
        new_qty = curr_qty + trade_qty
        if curr_qty == 0 or (curr_qty > 0 and trade_qty > 0) or (curr_qty < 0 and trade_qty < 0):
            # Adding to position: update weighted avg
            new_avg = (avg * abs(curr_qty) + fill_price * abs(trade_qty)) / (abs(new_qty) if new_qty != 0 else 1)
        else:
            # Reducing or flipping: realize P&L on closed portion
            closed_qty = min(abs(curr_qty), abs(trade_qty))
            pnl = (fill_price - avg) * (closed_qty if curr_qty > 0 else -closed_qty)
            realized += pnl
            # Remaining position and avg
            if abs(trade_qty) > abs(curr_qty):
                # flipped
                remaining = trade_qty + curr_qty
                new_avg = fill_price
            else:
                remaining = curr_qty + trade_qty
                new_avg = avg if remaining != 0 else 0.0
            new_qty = remaining
        sb.table("positions").update({
            "avg_price": new_avg,
            "qty": new_qty,
            "realized_pnl": realized,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pos["id"]).execute()
    else:
        sb.table("positions").insert({
            "symbol_id": symbol_id,
            "avg_price": fill_price,
            "qty": qty if side == 'BUY' else -qty,
            "realized_pnl": 0,
            "unrealized_pnl": 0,
            "exposure": fill_price * qty,
        }).execute()


