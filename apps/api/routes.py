from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal
from apps.api.supabase_client import get_client
from apps.api.yahoo_client import fetch_yahoo_candles
from apps.api.execution import simulate_order, apply_trade_updates
from apps.api.risk_engine import get_limits, suggest_position_size, should_block_order, apply_trailing_stops
from apps.api.analytics import pnl_summary

router = APIRouter()


class Symbol(BaseModel):
    ticker: str
    exchange: Literal['NSE', 'BSE']
    name: str | None = None
    sector: str | None = None
    is_fno: bool | None = None
    lot_size: int | None = None

@router.get("/test-cors")
def test_cors():
    return {"message": "CORS test"}

@router.get("/symbols", response_model=List[Symbol])
def list_symbols(active: bool = True):
    sb = get_client()
    q = sb.table("symbols").select("ticker,exchange,name,sector,is_fno,lot_size")
    if active:
        q = q.eq("is_active", True)
    data = q.execute().data
    return data or []


class CandleIngest(BaseModel):
    ticker: str
    exchange: Literal['NSE', 'BSE']
    timeframe: Literal['1m','5m','15m','1h','1d']
    candles: List[dict]


@router.post("/candles/ingest")
def ingest_candles(payload: CandleIngest):
    sb = get_client()
    sym = sb.table("symbols").select("id").eq("ticker", payload.ticker).eq("exchange", payload.exchange).single().execute().data
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")
    symbol_id = sym["id"]
    rows = []
    for c in payload.candles:
        rows.append({
            "symbol_id": symbol_id,
            "timeframe": payload.timeframe,
            "ts": c["ts"],
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c.get("volume"),
            "vwap": c.get("vwap"),
        })
    # upsert on primary key
    if rows:
        sb.table("candles").upsert(rows, on_conflict="symbol_id,timeframe,ts").execute()
    return {"ingested": len(rows)}


@router.get("/candles/{ticker}")
def get_candles(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE', tf: str = '1m', limit: int = 500):
    sb = get_client()
    sym = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")
    data = (
        sb.table("candles")
        .select("ts,open,high,low,close,volume,vwap")
        .eq("symbol_id", sym["id"])
        .eq("timeframe", tf)
        .order("ts", desc=True)
        .limit(limit)
        .execute().data
    )
    return list(reversed(data or []))


@router.post("/symbols/sync")
def symbols_sync():
    print("Symbols sync")
    from apps.api.symbols_sync import sync_symbols_from_seed
    count = sync_symbols_from_seed()
    return {"synced": count}


@router.post("/candles/fetch")
def fetch_and_store_candles(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE', tf: str = '1m', lookback_days: int = 5):
    print("Symbfetch_and_store_candles sync")
    sb = get_client()
    print(f"DEBUG: Fetching candles for ticker={ticker}, exchange={exchange}, tf={tf}, lookback_days={lookback_days}")
    sym = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
    print(f"DEBUG: Symbol lookup result: {sym}")
    if not sym:
        print("ERROR: Symbol not found in DB!")
        raise HTTPException(status_code=404, detail="Symbol not found")
    candles = fetch_yahoo_candles(ticker, exchange, timeframe=tf, lookback_days=lookback_days)
    if not candles:
        print("WARNING: No candles fetched from Yahoo!")
        return {"ingested": 0}
    rows = [{
        "symbol_id": sym["id"],
        "timeframe": tf,
        "ts": c["ts"],
        "open": c["open"],
        "high": c["high"],
        "low": c["low"],
        "close": c["close"],
        "volume": c.get("volume"),
    } for c in candles]
    print(f"DEBUG: Prepared {len(rows)} rows for upsert.")
    sb.table("candles").upsert(rows, on_conflict="symbol_id,timeframe,ts").execute()
    print(f"DEBUG: Upserted {len(rows)} rows into candles table.")
    return {"ingested": len(rows)}


@router.get("/signals")
def list_signals(ticker: str | None = None, exchange: Literal['NSE','BSE'] | None = None, tf: str | None = None, limit: int = 50):
    sb = get_client()
    q = sb.table("signals").select("ts, strategy, action, entry, stop, target, confidence, rationale, symbol_id, timeframe").order("ts", desc=True)
    if limit:
        q = q.limit(limit)
    if ticker and exchange:
        sym = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
        if not sym:
            return []
        q = q.eq("symbol_id", sym["id"])
    if tf:
        q = q.eq("timeframe", tf)
    data = q.execute().data or []
    # Attach symbol
    for d in data:
        if d.get("symbol_id"):
            s = sb.table("symbols").select("ticker,exchange").eq("id", d["symbol_id"]).single().execute().data
            d["ticker"] = s["ticker"]
            d["exchange"] = s["exchange"]
            d.pop("symbol_id", None)
    return data


class OrderRequest(BaseModel):
    ticker: str
    exchange: Literal['NSE','BSE'] = 'NSE'
    side: Literal['BUY','SELL']
    type: Literal['MARKET','LIMIT']
    price: float | None = None
    qty: float


@router.post("/orders")
def place_order(req: OrderRequest):
    sb = get_client()
    # Pause guard
    blocked, reason = should_block_order(req.ticker, req.exchange, req.side)
    if blocked:
        raise HTTPException(status_code=403, detail=reason or "Order blocked")
    sym = sb.table("symbols").select("id").eq("ticker", req.ticker).eq("exchange", req.exchange).single().execute().data
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")
    symbol_id = sym["id"]
    # Simulate
    fill = simulate_order(symbol_id, req.side, req.type, req.qty, req.price)
    order_row = {
        "symbol_id": symbol_id,
        "side": req.side,
        "type": req.type,
        "price": fill.fill_price if fill.fill_price is not None else req.price,
        "qty": req.qty,
        "status": fill.status,
        "slippage_bps": fill.slippage_bps,
        "simulator_notes": fill.notes,
    }
    order = sb.table("orders").insert(order_row).execute().data[0]
    if fill.status == 'FILLED' and fill.fill_price is not None and fill.filled_qty > 0:
        trade = sb.table("trades").insert({
            "order_id": order["id"],
            "symbol_id": symbol_id,
            "side": req.side,
            "price": fill.fill_price,
            "qty": fill.filled_qty,
        }).execute().data[0]
        apply_trade_updates(symbol_id, req.side, fill.fill_price, fill.filled_qty)
    return order


@router.get("/orders")
def list_orders(ticker: str | None = None, exchange: Literal['NSE','BSE'] | None = None):
    sb = get_client()
    q = sb.table("orders").select("*, symbols:ticker")
    # Simplified: return latest 50
    return sb.table("orders").select("id,ts,side,type,price,qty,status,slippage_bps").order("ts", desc=True).limit(50).execute().data


@router.get("/positions")
def get_positions():
    sb = get_client()
    positions = sb.table("positions").select("symbol_id,avg_price,qty,realized_pnl,unrealized_pnl,exposure,updated_at").execute().data
    # Attach tickers
    result = []
    for p in positions or []:
        sym = sb.table("symbols").select("ticker,exchange").eq("id", p["symbol_id"]).single().execute().data
        p.pop("symbol_id", None)
        p["ticker"] = sym["ticker"]
        p["exchange"] = sym["exchange"]
        result.append(p)
    return result


@router.get("/risk/limits")
def risk_limits():
    return get_limits().__dict__


@router.get("/risk/size")
def risk_size(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE', price: float = 0.0, atr: float | None = None, sector: str | None = None):
    qty = suggest_position_size(ticker, exchange, price, atr, sector)
    return {"qty": qty}


@router.post("/risk/apply_trailing")
def risk_apply_trailing(tf: str = '1m'):
    closed = apply_trailing_stops(tf)
    return {"exited": closed}


class PauseReq(BaseModel):
    pause_all: bool


@router.post("/risk/pause")
def risk_pause(req: PauseReq):
    sb = get_client()
    existing = sb.table("risk_limits").select("id").limit(1).execute().data
    if existing:
        sb.table("risk_limits").update({"pause_all": req.pause_all}).eq("id", existing[0]["id"]).execute()
    else:
        sb.table("risk_limits").insert({"pause_all": req.pause_all}).execute()
    return {"pause_all": req.pause_all}


@router.get("/pnl/summary")
def pnl(range_days: int = 90):
    return pnl_summary(range_days)


@router.get("/debug/scanner")
def debug_scanner():
    sb = get_client()
    # Latest run
    run = sb.table("strategy_runs").select("*").order("started_at", desc=True).limit(1).execute().data
    if not run:
        return {"message": "No runs found"}
    run = run[0]
    # Symbols scanned
    symbols = sb.table("symbols").select("ticker,exchange").eq("is_active", True).limit(10).execute().data
    # Recent signals
    signals = sb.table("signals").select("*").order("ts", desc=True).limit(10).execute().data
    return {
        "latest_run": run,
        "symbols_count": len(symbols),
        "recent_signals_count": len(signals),
        "sample_signals": signals[:3] if signals else []
    }


