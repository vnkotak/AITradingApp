from datetime import datetime, timedelta, timezone
from typing import Literal, List, Dict
import requests
import pandas as pd


TF_TO_YF = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '1h': '60m',
    '1d': '1d',
}


def map_symbol_to_yf(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE') -> str:
    # Yahoo uses .NS for NSE and .BO for BSE
    if ticker.startswith('%'):
        return ticker

    suffix = '.NS' if exchange == 'NSE' else '.BO'
    return f"{ticker}{suffix}"


def get_val(row, *keys):
    for k in keys:
        if k in row and not pd.isnull(row[k]):
            v = row[k]
            # If it's a Series, get the first value
            if isinstance(v, pd.Series):
                v = v.iloc[0]
            return v
    return 0.0


def fetch_yahoo_candles(
    ticker: str,
    exchange: Literal['NSE','BSE'],
    timeframe: str = '1m',
    lookback_days: int = 5
) -> List[Dict]:
    yf_symbol = map_symbol_to_yf(ticker, exchange)
    interval = TF_TO_YF.get(timeframe, '1d')

    print(f"📊 Fetching {timeframe} data for {yf_symbol}, lookback: {lookback_days} days")

    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{yf_symbol}"

    # Fix: Use period1 and period2 with appropriate limits based on timeframe
    now = int(datetime.now(timezone.utc).timestamp())

    # Yahoo Finance limitations for Indian stocks:
    # - 1m: NOT AVAILABLE for NSE/BSE stocks (only US stocks)
    # - 5m: Available, max 60 days
    # - 15m: Available, max 60 days
    # - 1h: Available, max 730 days
    # - 1d: Available, max 2 years
    max_days = {
        '1m': 7,      # Fallback to synthetic for Indian stocks
        '5m': 60,
        '15m': 60,
        '1h': 730,
        '1d': 365*2   # 2 years
    }

    actual_lookback = min(lookback_days, max_days.get(timeframe, 60))
    start_time = now - (actual_lookback * 24 * 60 * 60)

    print(f"⏰ Date range: {start_time} to {now} (using {actual_lookback} days for {timeframe})")

    params = {
        "period1": start_time,
        "period2": now,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        result = data["chart"]["result"][0]

        timestamps = result["timestamp"]
        indicators = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "time": pd.to_datetime(timestamps, unit="s", utc=True),
            "open": indicators.get("open", []),
            "high": indicators.get("high", []),
            "low": indicators.get("low", []),
            "close": indicators.get("close", []),
            "volume": indicators.get("volume", []),
        })

    except Exception as e:
        print(f"Exception during Yahoo API request: {e}")
        df = None

    if df is None or df.empty:
        print(f"❌ No data available for {yf_symbol} from Yahoo API")
        return []

    candles: List[Dict] = []
    for _, row in df.iterrows():
        ts = row["time"]
        if not isinstance(ts, datetime):
            continue
        candles.append({
            "ts": ts.isoformat(),
            "open": float(get_val(row, "open")),
            "high": float(get_val(row, "high")),
            "low": float(get_val(row, "low")),
            "close": float(get_val(row, "close")),
            "volume": float(get_val(row, "volume")),
        })

    print(f"Returning {len(candles)} candles for {yf_symbol}.")
    return candles

def fetch_real_time_quote(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE') -> float:
    """Fetch real-time quote for a stock from Yahoo Finance"""
    yf_symbol = map_symbol_to_yf(ticker, exchange)

    print(f"📊 Fetching real-time quote for {yf_symbol}")

    url = f"https://query1.finance.yahoo.com/v7/finance/quote"

    params = {
        "symbols": yf_symbol
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()

        if "quoteResponse" in data and "result" in data["quoteResponse"] and len(data["quoteResponse"]["result"]) > 0:
            quote = data["quoteResponse"]["result"][0]
            price = quote.get("regularMarketPrice") or quote.get("preMarketPrice") or quote.get("postMarketPrice")

            if price and price > 0:
                print(f"✅ Real-time price for {yf_symbol}: ₹{price}")
                return float(price)
            else:
                print(f"⚠️ No valid price found in quote for {yf_symbol}")
                return 0.0
        else:
            print(f"❌ No quote data available for {yf_symbol}")
            return 0.0

    except requests.exceptions.HTTPError as e:
        if r.status_code == 404:
            print(f"⚠️ Symbol {yf_symbol} not found on Yahoo Finance (404)")
            return 0.0
        else:
            print(f"❌ HTTP error fetching real-time quote for {yf_symbol}: {e}")
            return 0.0
    except Exception as e:
        print(f"❌ Error fetching real-time quote for {yf_symbol}: {e}")
        return 0.0

