from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal
from apps.api.supabase_client import get_client
from apps.api.yahoo_client import fetch_yahoo_candles, fetch_real_time_quote
from apps.api.execution import simulate_order, apply_trade_updates
from apps.api.risk_engine import get_limits, suggest_position_size, should_block_order, apply_trailing_stops
from apps.api.analytics import pnl_summary
import random
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
    if not sb:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available. Please configure SUPABASE_URL and SUPABASE_SERVICE_KEY."
        )

    try:
        q = sb.table("symbols").select("ticker,exchange,name,sector,is_fno,lot_size")
        if active:
            q = q.eq("is_active", True)
        data = q.execute().data
        if not data:
            raise HTTPException(
                status_code=404,
                detail="No symbols found. Please add symbols to the database manually or through external data sources."
            )
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


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

@router.post("/candles/fetch")
def fetch_and_store_candles(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE', tf: str = '1m', lookback_days: int = 5):
    print("hello")
    sb = get_client()
    if not sb:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available. Please configure SUPABASE_URL and SUPABASE_SERVICE_KEY."
        )

    try:
        sym = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
        print (sym)
        if not sym:
            raise HTTPException(status_code=404, detail="Symbol not found")
        candles = fetch_yahoo_candles(ticker, exchange, timeframe=tf, lookback_days=lookback_days)
        if not candles:
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
        sb.table("candles").upsert(rows, on_conflict="symbol_id,timeframe,ts").execute()
        return {"ingested": len(rows)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/candles/ticker/{ticker}")
def get_candles(
    ticker: str,
    exchange: Literal['NSE', 'BSE'] = 'NSE',
    tf: str = '1m',
    limit: int = 500,
    fresh: bool = False,  # Legacy parameter - kept for compatibility
    auto_fetch: bool = False  # New smart auto-fetch parameter
):
    sb = get_client()
    if not sb:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available. Please configure SUPABASE_URL and SUPABASE_SERVICE_KEY."
        )

    try:
        # Fetch symbol row(s) safely
        res = (
            sb.table("symbols")
            .select("id")
            .eq("ticker", ticker)
            .eq("exchange", exchange)
            .execute()
        )

        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=404, detail=f"Symbol {ticker} not found in {exchange}")

        sym = res.data[0]

        # Smart auto-fetch logic: only fetch fresh data if it's stale
        if auto_fetch or fresh:
            try:
                # Check if we need fresh data (only if data is > 2 hours old)
                latest_candle = sb.table('candles').select('ts').eq('symbol_id', sym['id']).eq('timeframe', tf).order('ts', desc=True).limit(1).execute().data

                needs_fresh = True
                if latest_candle:
                    from datetime import datetime, timezone
                    latest_ts = datetime.fromisoformat(latest_candle[0]['ts'].replace('Z', '+00:00'))
                    hours_old = (datetime.now(timezone.utc) - latest_ts).total_seconds() / 3600
                    needs_fresh = hours_old > 2  # Only fetch if > 2 hours old

                if needs_fresh:
                    # Fetch fresh data from Yahoo Finance
                    fresh_candles = fetch_yahoo_candles(ticker, exchange, tf, lookback_days=2)

                    if fresh_candles and len(fresh_candles) > 0:
                        # Filter out zero-value candles before storing
                        valid_candles = [c for c in fresh_candles if c.get("open", 0) > 0 and c.get("close", 0) > 0]
                        zero_candles = len(fresh_candles) - len(valid_candles)

                        if zero_candles > 0:
                            print(f"⚠️ Filtered out {zero_candles} zero-value candles from Yahoo data")

                        # Store only valid candles in database
                        rows = [{
                            "symbol_id": sym["id"],
                            "timeframe": tf,
                            "ts": c["ts"],
                            "open": c["open"],
                            "high": c["high"],
                            "low": c["low"],
                            "close": c["close"],
                            "volume": c.get("volume"),
                        } for c in valid_candles]

                        if rows:
                            sb.table("candles").upsert(rows, on_conflict="symbol_id,timeframe,ts").execute()
            except Exception as e:
                # Don't fail the request if auto-fetch fails - just log and continue
                print(f"⚠️ Auto-fetch failed for {ticker} {tf}: {e}")

        # Fetch candles from database
        candles_res = (
            sb.table("candles")
            .select("ts,open,high,low,close,volume,vwap")
            .eq("symbol_id", sym["id"])
            .eq("timeframe", tf)
            .order("ts", desc=True)
            .limit(limit)
            .execute()
        )

        return list(reversed(candles_res.data or []))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Symbols sync endpoint removed - requires manual symbol management through database


@router.get("/signals")
def list_signals(ticker: str | None = None, exchange: Literal['NSE','BSE'] | None = None, tf: str | None = None, limit: int = 50):
    sb = get_client()
    if not sb:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available. Please configure SUPABASE_URL and SUPABASE_SERVICE_KEY."
        )

    try:
        q = sb.table("signals").select("ts, strategy, action, entry, stop, target, confidence, rationale, symbol_id, timeframe").order("ts", desc=True)
        if limit:
            q = q.limit(limit)

        # Apply filters - handle individual and combined parameters
        if ticker and exchange:
            # Both ticker and exchange provided - find specific symbol
            sym = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
            if not sym:
                return []  # No symbols found with this ticker and exchange
            q = q.eq("symbol_id", sym["id"])
        elif ticker:
            # Only ticker provided - find symbol_id for the ticker (works with any exchange)
            sym = sb.table("symbols").select("id").eq("ticker", ticker).single().execute().data
            if not sym:
                return []  # No symbols found with this ticker
            q = q.eq("symbol_id", sym["id"])
        elif exchange:
            # Only exchange provided - filter by exchange
            exchange_symbols = sb.table("symbols").select("id").eq("exchange", exchange).execute().data
            if not exchange_symbols:
                return []  # No symbols found for this exchange
            symbol_ids = [s["id"] for s in exchange_symbols]
            q = q.in_("symbol_id", symbol_ids)

        if tf:
            q = q.eq("timeframe", tf)

        data = q.execute().data or []

        # Attach symbol information
        for d in data:
            if d.get("symbol_id"):
                s = sb.table("symbols").select("ticker,exchange").eq("id", d["symbol_id"]).single().execute().data
                d["ticker"] = s["ticker"]
                d["exchange"] = s["exchange"]
                d.pop("symbol_id", None)

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


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
        apply_trade_updates(symbol_id, req.side, fill.fill_price, fill.filled_qty)
    return order


@router.get("/orders")
def list_orders(ticker: str | None = None, exchange: Literal['NSE','BSE'] | None = None, limit: int = 50, offset: int = 0):
    sb = get_client()
    # Get orders with symbol information, with pagination
    query = sb.table("orders").select("id,ts,side,type,price,qty,status,slippage_bps,simulator_notes,symbol_id").order("ts", desc=True)

    # Apply pagination
    if limit > 0:
        query = query.limit(limit)
    if offset > 0:
        query = query.range(offset, offset + limit - 1)

    orders = query.execute().data or []

    # Attach symbol information to each order
    orders_with_symbols = []
    for order in orders:
        if order.get("symbol_id"):
            try:
                symbol_info = sb.table("symbols").select("ticker,exchange").eq("id", order["symbol_id"]).single().execute().data
                if symbol_info:
                    order["ticker"] = symbol_info["ticker"]
                    order["exchange"] = symbol_info["exchange"]
                    order.pop("symbol_id", None)  # Remove symbol_id from response
                    orders_with_symbols.append(order)
            except:
                # If symbol lookup fails, still include the order
                order.pop("symbol_id", None)
                orders_with_symbols.append(order)
        else:
            orders_with_symbols.append(order)

    return orders_with_symbols


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
    print(f"📊 [RISK_SIZE] Request for {ticker}.{exchange}, price={price}")
    start_time = time.time()

    try:
        qty = suggest_position_size(ticker, exchange, price, atr, sector)
        end_time = time.time()
        print(f"✅ [RISK_SIZE] Success for {ticker}.{exchange}: qty={qty}, duration={end_time-start_time:.2f}s")
        return {"qty": qty}
    except Exception as e:
        end_time = time.time()
        print(f"❌ [RISK_SIZE] Error for {ticker}.{exchange}: {e}, duration={end_time-start_time:.2f}s")
        raise HTTPException(status_code=500, detail=f"Risk calculation error: {str(e)}")


@router.post("/risk/apply_trailing")
def risk_apply_trailing(tf: str = '1m'):
    closed = apply_trailing_stops(tf)
    return {"exited": closed}




@router.get("/pnl/summary")
def pnl(range_days: int = 90):
    return pnl_summary(range_days)


@router.get("/portfolio/performance")
def get_portfolio_performance_endpoint():
    """Get comprehensive portfolio performance with realized and unrealized P&L"""
    from apps.api.analytics import get_portfolio_performance
    return get_portfolio_performance()


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


# Mock data generation functions removed - requires real database connection


# ===== MARKET DATA FUNCTIONS =====

def get_indian_market_status() -> tuple[str, str]:
    """Check if Indian markets are open and return status with market time"""
    from datetime import datetime
    import pytz

    # Indian Timezone
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    # Market hours: 9:15 AM - 3:30 PM IST, Monday-Friday
    market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)

    # Check if today is a weekday (0=Monday, 4=Friday)
    if now.weekday() >= 5:  # Saturday or Sunday
        return "CLOSED", "Market closed (Weekend)"

    # Check if current time is within market hours
    if market_open_time <= now <= market_close_time:
        return "OPEN", now.strftime("%H:%M")

    # Before market opens
    if now < market_open_time:
        return "PRE_OPEN", f"Opens at {market_open_time.strftime('%H:%M')}"

    # After market closes
    return "CLOSED", f"Closed at {market_close_time.strftime('%H:%M')}"


def fetch_real_market_indices():
    """Fetch real market indices data from Yahoo Finance"""
    from apps.api.yahoo_client import fetch_yahoo_candles

    # Correct Yahoo Finance symbols for Indian indices
    indices_data = [
        {"symbol": "%5ENSEI", "name": "NIFTY 50", "yf_symbol": "^NSEI", "exchange": "NSE"},
        {"symbol": "%5EBSESN", "name": "SENSEX", "yf_symbol": "^BSESN", "exchange": "BSE"},
        {"symbol": "%5ENSEBANK", "name": "NIFTY BANK", "yf_symbol": "^NSEBANK", "exchange": "NSE"},
        {"symbol": "%5ECNXIT", "name": "NIFTY IT", "yf_symbol": "^CNXIT", "exchange": "NSE"},
    ]

    real_indices = []

    for index_info in indices_data:
        try:
            # Fetch latest data (1 day lookback, 1d timeframe)
            candles = fetch_yahoo_candles(index_info["symbol"], "NSE", "1d", 1)

            if candles and len(candles) > 0:
                latest = candles[-1]
                previous_close = candles[-2]["close"] if len(candles) > 1 else latest["close"]

                change = latest["close"] - previous_close
                change_percent = (change / previous_close) * 100 if previous_close > 0 else 0

                real_indices.append({
                    "name": index_info["name"],
                    "value": round(latest["close"], 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "source": "yahoo"
                })
            else:
                # Fallback to mock data if Yahoo fails
                print(f"⚠️ Failed to fetch {index_info['name']} from Yahoo, using mock data")
                mock_values = {
                    "NIFTY 50": {"value": 22150.75, "change": 125.30, "changePercent": 0.57},
                    "SENSEX": {"value": 72850.20, "change": 380.45, "changePercent": 0.52},
                    "NIFTY BANK": {"value": 47500.85, "change": 220.75, "changePercent": 0.47},
                    "NIFTY IT": {"value": 38500.40, "change": -85.25, "changePercent": -0.22},
                }

                mock = mock_values.get(index_info["name"], {"value": 22000, "change": 0, "changePercent": 0})
                real_indices.append({
                    "name": index_info["name"],
                    "value": mock["value"],
                    "change": mock["change"],
                    "changePercent": mock["changePercent"],
                    "source": "mock"
                })

        except Exception as e:
            print(f"❌ Error fetching {index_info['name']}: {e}")
            # Use mock data as fallback
            real_indices.append({
                "name": index_info["name"],
                "value": 22000 + len(real_indices) * 1000,
                "change": 100 + len(real_indices) * 50,
                "changePercent": 0.5 + len(real_indices) * 0.1,
                "source": "error"
            })

    return real_indices


def fetch_market_performance_data(limit: int = 100):
    """Fetch comprehensive market performance data from database symbols for heatmap and top movers"""
    from apps.api.yahoo_client import fetch_yahoo_candles

    sb = get_client()
    if not sb:
        print("⚠️ Database not connected, returning empty market data")
        return []

    try:
        # Fetch active symbols from database (limit to avoid too many API calls)
        symbols = sb.table("symbols").select("ticker,exchange,name,sector").eq("is_active", True).limit(limit).execute().data or []

        if not symbols:
            print("⚠️ No active symbols found in database")
            return []

        print(f"📊 Fetching performance data for {len(symbols)} active symbols from database")

        # Fetch real performance data for all symbols
        stocks_with_data = []

        for symbol in symbols:
            try:
                ticker = symbol["ticker"]
                exchange = symbol["exchange"]
                name = symbol["name"] or ticker
                sector = symbol["sector"] or "Unknown"

                # Fetch 2 days of data to calculate daily change
                candles = fetch_yahoo_candles(ticker, exchange, "1d", 2)
                if candles and len(candles) >= 2:
                    current = candles[-1]
                    previous = candles[-2]

                    change = current["close"] - previous["close"]
                    change_percent = (change / previous["close"]) * 100 if previous["close"] > 0 else 0

                    stocks_with_data.append({
                        "ticker": ticker,
                        "name": name,
                        "sector": sector,
                        "exchange": exchange,
                        "price": round(current["close"], 2),
                        "change": round(change, 2),
                        "changePercent": round(change_percent, 2),
                        "performance": round(change_percent, 2),
                        "volume": int(current.get("volume", 1000000))
                    })
            except Exception as e:
                print(f"⚠️ Error fetching data for {symbol['ticker']}: {e}")
                continue

        print(f"✅ Successfully fetched data for {len(stocks_with_data)}/{len(symbols)} symbols")
        return stocks_with_data

    except Exception as e:
        print(f"❌ Error fetching market performance data: {e}")
        return []


def fetch_comprehensive_market_heatmap():
    """Fetch comprehensive market heatmap using database symbols"""
    stocks_data = fetch_market_performance_data(limit=100)

    if not stocks_data:
        return []

    # Group by sectors for heatmap organization
    sector_performance = {}
    for stock in stocks_data:
        sector = stock.get("sector", "Unknown")
        if sector not in sector_performance:
            sector_performance[sector] = []
        sector_performance[sector].append(stock)

    # Select top performers from each sector for heatmap
    heatmap_stocks = []
    for sector, stocks in sector_performance.items():
        # Sort by absolute performance and take top performers
        stocks.sort(key=lambda x: abs(x["performance"]), reverse=True)
        heatmap_stocks.extend(stocks[:3])  # Top 3 from each sector

    # Sort final selection by performance for color distribution
    heatmap_stocks.sort(key=lambda x: x["performance"], reverse=True)

    # Limit to reasonable size for UI
    heatmap_stocks = heatmap_stocks[:25]

    print(f"📊 Heatmap: {len(heatmap_stocks)} stocks from {len(sector_performance)} sectors")
    for stock in heatmap_stocks[:5]:  # Show top 5 in logs
        print(f"  {stock['ticker']}: {stock['performance']:+.2f}% ({stock['sector']})")

    return heatmap_stocks

    stocks_with_changes = []

    for stock in major_stocks:
        try:
            candles = fetch_yahoo_candles(stock["ticker"], "NSE", "1d", 2)
            if candles and len(candles) >= 2:
                current = candles[-1]
                previous = candles[-2]

                change = current["close"] - previous["close"]
                change_percent = (change / previous["close"]) * 100 if previous["close"] > 0 else 0

                stocks_with_changes.append({
                    "ticker": stock["ticker"],
                    "name": stock["name"],
                    "price": round(current["close"], 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2)
                })
        except Exception as e:
            print(f"❌ Error fetching {stock['ticker']}: {e}")
            continue

    # Sort by change percentage and separate gainers/losers
    gainers = [s for s in stocks_with_changes if s["changePercent"] > 0]
    losers = [s for s in stocks_with_changes if s["changePercent"] < 0]

    # Sort by absolute change percentage
    gainers.sort(key=lambda x: x["changePercent"], reverse=True)
    losers.sort(key=lambda x: x["changePercent"])  # More negative first

    return {
        "gainers": gainers[:5],  # Top 5 gainers
        "losers": losers[:5]     # Top 5 losers (most negative)
    }


# ===== HOME PAGE API ENDPOINTS =====

@router.get("/home/overview")
def get_home_overview():
    """Get comprehensive home page overview data"""
    sb = get_client()
    data_source = "real"  # Track if we're using real or mock data

    # Initialize variables before try block
    real_indices = []
    top_gainers = []
    top_losers = []
    market_status = "CLOSED"
    market_time = datetime.now().strftime("%H:%M")
    sentiment_score = 0
    portfolio_value = 1000000  # Default fallback
    portfolio_pnl = 0
    cash_balance = 1000000
    active_positions = 0
    total_signals_today = 0
    data_source = "mock"

    # Always try to fetch real market indices data, regardless of database connection
    try:
        print("📊 Fetching real market indices from Yahoo Finance...")
        real_indices = fetch_real_market_indices()
        print(f"✅ Successfully fetched {len(real_indices)} indices")

        # Get comprehensive market performance data (single API call for all data)
        print("📊 Fetching comprehensive market performance data...")
        market_performance_data = fetch_market_performance_data(limit=50)  # Smaller limit for overview

        # For top gainers/losers, filter and sort the comprehensive data
        gainers = [s for s in market_performance_data if s["performance"] > 0]
        losers = [s for s in market_performance_data if s["performance"] < 0]

        gainers.sort(key=lambda x: x["performance"], reverse=True)
        losers.sort(key=lambda x: x["performance"])  # Most negative first

        top_gainers = gainers[:5]
        top_losers = losers[:5]
        print(f"✅ Successfully processed {len(market_performance_data)} stocks for top movers")

        # Get real market status
        market_status, market_time = get_indian_market_status()
        print(f"🏛️ Market status: {market_status} at {market_time}")

        # Set data source to real since we got real data
        data_source = "real"

    except Exception as e:
        print(f"❌ Error fetching real market data: {e}")
        # Fall back to mock indices data if Yahoo Finance fails
        print("⚠️ Using mock indices data as fallback")
        real_indices = [
            {"name": "NIFTY 50", "value": 22150.75, "change": 125.30, "changePercent": 0.57, "source": "mock"},
            {"name": "SENSEX", "value": 72850.20, "change": 380.45, "changePercent": 0.52, "source": "mock"},
            {"name": "NIFTY BANK", "value": 47500.85, "change": 220.75, "changePercent": 0.47, "source": "mock"},
            {"name": "NIFTY IT", "value": 38500.40, "change": -85.25, "changePercent": -0.22, "source": "mock"}
        ]
        top_gainers = [
            {"ticker": "RELIANCE", "name": "Reliance Industries", "price": 2456.75, "change": 45.20, "changePercent": 1.87},
            {"ticker": "TCS", "name": "Tata Consultancy", "price": 3421.30, "change": 38.15, "changePercent": 1.13},
            {"ticker": "INFY", "name": "Infosys", "price": 1687.45, "change": 25.80, "changePercent": 1.55},
            {"ticker": "HDFCBANK", "name": "HDFC Bank", "price": 1654.90, "change": 18.75, "changePercent": 1.15},
            {"ticker": "ICICI", "name": "ICICI Bank", "price": 987.65, "change": 15.40, "changePercent": 1.58}
        ]
        top_losers = [
            {"ticker": "YESBANK", "name": "Yes Bank", "price": 18.45, "change": -0.85, "changePercent": -4.40},
            {"ticker": "IDEA", "name": "Vodafone Idea", "price": 8.90, "change": -0.35, "changePercent": -3.78},
            {"ticker": "SUZLON", "name": "Suzlon Energy", "price": 45.20, "change": -1.65, "changePercent": -3.52},
            {"ticker": "GMRAIRPORT", "name": "GMR Infra", "price": 38.75, "change": -1.20, "changePercent": -3.00}
        ]

    # Only try database operations if we have a database connection
    if sb:
        try:
            # Get market indices data (using top symbols as proxy)
            print("🔍 Fetching symbols from database...")
            symbols = sb.table("symbols").select("ticker,exchange").eq("is_active", True).limit(10).execute().data or []
            print(f"📊 Found {len(symbols)} symbols in database")

            # Get recent signals for market sentiment
            print("🔍 Fetching recent signals...")
            recent_signals = sb.table("signals").select("action,confidence,ts").order("ts", desc=True).limit(50).execute().data or []
            print(f"📊 Found {len(recent_signals)} signals in database")

            # Calculate market sentiment based on MULTIPLE factors
            bullish_signals = sum(1 for s in recent_signals if s["action"] == "BUY")
            bearish_signals = sum(1 for s in recent_signals if s["action"] == "SELL")
            total_signals = len(recent_signals)

            # Calculate AI sentiment from signals
            ai_sentiment_score = 0
            if total_signals > 0:
                ai_sentiment_score = ((bullish_signals - bearish_signals) / total_signals) * 100

            # Get portfolio metrics
            print("🔍 Fetching positions...")
            positions = sb.table("positions").select("qty,avg_price,unrealized_pnl").execute().data or []
            print(f"📊 Found {len(positions)} positions in database")

            cash = 1000000  # Default cash balance since cash_available column doesn't exist in schema
            portfolio_value = cash
            unrealized_pnl = 0
            for pos in positions:
                portfolio_value += abs(float(pos.get("qty", 0))) * float(pos.get("avg_price", 0))
                unrealized_pnl += float(pos.get("unrealized_pnl", 0))

            # Calculate market sentiment from actual market data
            market_sentiment_score = 0
            if real_indices:
                # Average the performance of major indices
                total_performance = sum(index.get("changePercent", 0) for index in real_indices)
                market_sentiment_score = total_performance / len(real_indices) if real_indices else 0

            # Combine AI sentiment with market reality (weighted average)
            # 60% market data + 40% AI signals for balanced view
            combined_sentiment = (market_sentiment_score * 0.6) + (ai_sentiment_score * 0.4)
            sentiment_score = combined_sentiment

            return {
                "market_status": market_status,
                "market_time": market_time,
                "sentiment_score": sentiment_score,
                "portfolio_value": portfolio_value,
                "portfolio_pnl": unrealized_pnl,
                "cash_balance": cash,
                "active_positions": len(positions),
                "total_signals_today": total_signals,
                "data_source": data_source,
                "debug_info": f"Market: {market_status}, Indices: {len(real_indices)}, Gainers: {len(top_gainers)}, Losers: {len(top_losers)}, AI Signals: {total_signals}",
                "sentiment_components": {
                    "ai_sentiment": round(ai_sentiment_score, 1),
                    "market_sentiment": round(market_sentiment_score, 1),
                    "combined_sentiment": round(sentiment_score, 1),
                    "total_signals": total_signals
                },
                "top_gainers": top_gainers,
                "top_losers": top_losers,
                "indices": real_indices
            }
        except Exception as e:
            print(f"❌ Database error: {e}")
            # Even if database fails, return the real market data we fetched
            data_source = "hybrid"

    # Return the data we fetched (either real or fallback mock data)
    return {
        "market_status": market_status,
        "market_time": market_time,
        "sentiment_score": sentiment_score,
        "portfolio_value": portfolio_value,
        "portfolio_pnl": portfolio_pnl,
        "cash_balance": cash_balance,
        "active_positions": active_positions,
        "total_signals_today": total_signals_today,
        "data_source": data_source,
        "debug_info": f"Market: {market_status}, Indices: {len(real_indices)}, Gainers: {len(top_gainers)}, Losers: {len(top_losers)}",
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "indices": real_indices
    }


@router.get("/home/recent-signals")
def get_recent_signals(limit: int = 6):
    """Get recent trading signals for home page display"""
    sb = get_client()
    if not sb:
        # Return mock signals if database not available
        return [
            {"ts": datetime.now().isoformat(), "strategy": "RSI_Momentum", "action": "BUY", "entry": 2450, "stop": 2400, "target": 2550, "confidence": 0.85, "ticker": "RELIANCE", "exchange": "NSE"},
            {"ts": (datetime.now() - timedelta(minutes=15)).isoformat(), "strategy": "MACD_Signal", "action": "SELL", "entry": 1680, "stop": 1720, "target": 1620, "confidence": 0.72, "ticker": "INFY", "exchange": "NSE"},
            {"ts": (datetime.now() - timedelta(minutes=30)).isoformat(), "strategy": "Breakout", "action": "BUY", "entry": 3420, "stop": 3380, "target": 3500, "confidence": 0.91, "ticker": "TCS", "exchange": "NSE"},
            {"ts": (datetime.now() - timedelta(minutes=45)).isoformat(), "strategy": "Mean_Reversion", "action": "BUY", "entry": 1650, "stop": 1620, "target": 1700, "confidence": 0.68, "ticker": "HDFCBANK", "exchange": "NSE"}
        ][:limit]

    try:
        signals_data = sb.table("signals").select("ts,strategy,action,entry,stop,target,confidence,symbol_id").order("ts", desc=True).limit(limit).execute().data or []

        # Attach symbol information to each signal
        signals_with_symbols = []
        for signal in signals_data:
            if signal.get("symbol_id"):
                try:
                    symbol_info = sb.table("symbols").select("ticker,exchange").eq("id", signal["symbol_id"]).single().execute().data
                    if symbol_info:
                        signal["ticker"] = symbol_info["ticker"]
                        signal["exchange"] = symbol_info["exchange"]
                        signal.pop("symbol_id", None)  # Remove the symbol_id as it's not needed in the response
                        signals_with_symbols.append(signal)
                except:
                    # If symbol lookup fails, skip this signal
                    continue

        return signals_with_symbols
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent signals: {str(e)}")


@router.get("/home/market-heatmap")
def get_market_heatmap(limit: int = 20):
    """Get comprehensive market heatmap with sector-wise stock selection"""
    sb = get_client()

    try:
        # Get comprehensive market heatmap with real data
        print("📊 Fetching comprehensive market heatmap...")
        heatmap_stocks = fetch_comprehensive_market_heatmap()

        # Limit to requested number and ensure we have data
        if len(heatmap_stocks) > limit:
            # Prioritize by performance magnitude for better visualization
            heatmap_stocks.sort(key=lambda x: abs(x["performance"]), reverse=True)
            heatmap_stocks = heatmap_stocks[:limit]

        print(f"📊 Heatmap: Returning {len(heatmap_stocks)} stocks from multiple sectors")
        return heatmap_stocks

    except Exception as e:
        print(f"❌ Heatmap error: {e}")
        # Ultimate fallback to sector-based mock data
        return generate_mock_sector_heatmap(limit)


def generate_mock_sector_heatmap(limit: int = 20):
    """Generate realistic mock heatmap data organized by sectors"""
    sector_data = {
        "🏦 Banking": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
        "💻 IT": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
        "🛢️ Energy": ["RELIANCE", "ONGC", "BPCL", "IOC"],
        "🚗 Auto": ["MARUTI", "M&M", "TATAMOTORS", "BAJAJ-AUTO"],
        "🏗️ Infra": ["LT", "ULTRACEMCO", "ADANIPORTS"],
        "🛍️ FMCG": ["HINDUNILVR", "NESTLEIND", "ASIANPAINT"],
        "💊 Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA"],
        "⚡ Power": ["POWERGRID", "NTPC", "TATAPOWER"]
    }

    heatmap_data = []
    stock_index = 0

    for sector, stocks in sector_data.items():
        for stock in stocks:
            if len(heatmap_data) >= limit:
                break

            # Generate realistic performance data
            performance = round(random.uniform(-4, 4), 2)
            volume = random.randint(500000, 50000000)

            heatmap_data.append({
                "ticker": stock,
                "exchange": "NSE",
                "performance": performance,
                "volume": volume,
                "price": round(100 + random.randint(50, 2000), 2),
                "sector": sector.split()[1],  # Remove emoji
                "sector_group": sector,
                "source": "mock"
            })

            stock_index += 1

        if len(heatmap_data) >= limit:
            break

    return heatmap_data


@router.get("/home/news")
def get_market_news(limit: int = 5):
    """Get recent market news (mock data for now)"""
    news_items = [
        {
            "id": 1,
            "headline": "RBI Maintains Repo Rate at 6.5%, Signals Potential Cuts in Q2",
            "source": "Economic Times",
            "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "sentiment": "positive",
            "impact": "high"
        },
        {
            "id": 2,
            "headline": "Foreign Investors Pour ₹12,500 Cr into Indian Equities This Month",
            "source": "Moneycontrol",
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "sentiment": "positive",
            "impact": "medium"
        },
        {
            "id": 3,
            "headline": "IT Sector Faces Headwinds as US Recession Fears Grow",
            "source": "Business Standard",
            "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
            "sentiment": "negative",
            "impact": "medium"
        },
        {
            "id": 4,
            "headline": "Crude Oil Prices Surge 3% on Supply Concerns",
            "source": "Reuters",
            "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
            "sentiment": "negative",
            "impact": "low"
        },
        {
            "id": 5,
            "headline": "Banking Sector Shows Strong Q4 Results, NPA Levels Decline",
            "source": "Financial Express",
            "timestamp": (datetime.now() - timedelta(hours=8)).isoformat(),
            "sentiment": "positive",
            "impact": "high"
        }
    ]
    return news_items[:limit]


@router.post("/auto-execute/run")
def run_auto_execution(
    timeframes: str = '1m',
    confidence_threshold: float = 0.7,
    dry_run: bool = False
):
    """Manually trigger automated paper trading execution for multiple timeframes"""
    from apps.api.auto_execute_signals import AutoExecutor

    try:
        executor = AutoExecutor()
        results = {}

        # Split timeframes and execute for each
        tf_list = [tf.strip() for tf in timeframes.split(',')]
        for tf in tf_list:
            logger.info(f"Processing timeframe: {tf}")
            result = executor.run_execution_cycle(
                timeframe=tf,
                confidence_threshold=confidence_threshold,
                dry_run=dry_run
            )
            results[tf] = result

        return {
            "timeframes_processed": tf_list,
            "results": results,
            "summary": {
                "total_executed": sum(r.get("executed", 0) for r in results.values()),
                "total_skipped": sum(r.get("skipped", 0) for r in results.values()),
                "total_errors": sum(r.get("errors", 0) for r in results.values())
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-execution error: {str(e)}")


@router.get("/prices/realtime")
def get_real_time_price(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE'):
    """Get real-time price for a stock from Yahoo Finance"""
    try:
        price = fetch_real_time_quote(ticker, exchange)
        if price > 0:
            return {"price": price, "ticker": ticker, "exchange": exchange, "source": "yahoo_realtime"}
        else:
            # Try fallback to stored candles
            fallback_price = get_latest_price_from_candles(ticker, exchange)
            if fallback_price > 0:
                return {"price": fallback_price, "ticker": ticker, "exchange": exchange, "source": "database_candles"}
            else:
                raise HTTPException(status_code=404, detail=f"No price available for {ticker}.{exchange}")
    except Exception as e:
        # Try fallback to stored candles even on error
        try:
            fallback_price = get_latest_price_from_candles(ticker, exchange)
            if fallback_price > 0:
                return {"price": fallback_price, "ticker": ticker, "exchange": exchange, "source": "database_candles_fallback"}
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error fetching real-time price: {str(e)}")


def get_latest_price_from_candles(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE') -> float:
    """Get the most recent price from stored candles as fallback"""
    sb = get_client()
    if not sb:
        return 0.0

    try:
        # Get symbol ID
        sym = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", exchange).single().execute().data
        if not sym:
            return 0.0

        symbol_id = sym["id"]

        # Try 1m candles first for most recent price
        for tf in ['1m', '5m', '15m', '1h', '1d']:
            candles = sb.table("candles").select("close").eq("symbol_id", symbol_id).eq("timeframe", tf).order("ts", desc=True).limit(1).execute().data
            if candles and len(candles) > 0:
                price = float(candles[0]["close"])
                if price > 0:
                    print(f"✅ Fallback price from {tf} candles for {ticker}: ₹{price}")
                    return price

        return 0.0

    except Exception as e:
        print(f"❌ Error fetching fallback price from candles for {ticker}: {e}")
        return 0.0


@router.get("/home/system-status")
def get_system_status():
    """Get system health and connection status"""
    sb = get_client()

    db_status = "disconnected"
    if sb:
        try:
            # Test database connection
            symbols_count = len(sb.table("symbols").select("id").limit(1).execute().data or [])
            db_status = "connected"
        except:
            db_status = "error"

    # Get current market status for refresh rate info
    market_status, _ = get_indian_market_status()

    return {
        "api_status": "healthy",
        "database_status": db_status,
        "market_data_status": "live",
        "market_status": market_status,
        "last_update": datetime.now().isoformat(),
        "uptime": "99.9%",
        "active_strategies": 5,
        "signals_per_hour": 12,
        "refresh_rate": "10s" if market_status == "OPEN" else "1m" if market_status == "PRE_OPEN" else "5m",
        "data_source": "mock" if db_status != "connected" else "real"
    }


