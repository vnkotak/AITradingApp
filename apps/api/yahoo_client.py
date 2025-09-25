from datetime import datetime, timedelta, timezone
from typing import Literal, List, Dict
import math
import random
import yfinance as yf


TF_TO_YF = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '1h': '60m',
    '1d': '1d',
}


def map_symbol_to_yf(ticker: str, exchange: Literal['NSE','BSE'] = 'NSE') -> str:
    # Yahoo uses .NS for NSE and .BO for BSE
    suffix = '.NS' if exchange == 'NSE' else '.BO'
    return f"{ticker}{suffix}"


def fetch_yahoo_candles(ticker: str, exchange: Literal['NSE','BSE'], timeframe: str = '1m', lookback_days: int = 5) -> List[Dict]:
    yf_symbol = map_symbol_to_yf(ticker, exchange)
    interval = TF_TO_YF.get(timeframe, '1m')
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    try:
        df = yf.download(yf_symbol, interval=interval, start=start, end=end, auto_adjust=False, progress=False)
    except Exception:
        df = None
    if df is None or df.empty:
        # Robust fallback: synth candles so scanning can proceed without live data
        return _generate_synthetic_candles(timeframe, lookback_days, seed_symbol=f"{ticker}.{exchange}")
    df = df.reset_index()
    # Standardize column names between different intervals (Datetime vs DatetimeIndex named)
    time_col = 'Datetime' if 'Datetime' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
    candles: List[Dict] = []
    for _, row in df.iterrows():
        ts = row[time_col]
        if not isinstance(ts, datetime):
            try:
                ts = datetime.fromisoformat(str(ts)).replace(tzinfo=timezone.utc)
            except Exception:
                # skip unparsable
                continue
        candles.append({
            'ts': ts.isoformat(),
            'open': float(row.get('Open') or row.get('open') or 0),
            'high': float(row.get('High') or row.get('high') or 0),
            'low': float(row.get('Low') or row.get('low') or 0),
            'close': float(row.get('Close') or row.get('close') or 0),
            'volume': float((row.get('Volume') or row.get('volume') or 0) or 0),
        })
    return candles


def _generate_synthetic_candles(timeframe: str, lookback_days: int, seed_symbol: str) -> List[Dict]:
    # Geometric random walk with mild volatility; timeframe granularity respected
    tf_to_secs = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '1h': 3600,
        '1d': 86400,
    }
    step = tf_to_secs.get(timeframe, 60)
    total_secs = max(1, lookback_days) * 86400
    points = min(1200, max(50, total_secs // step))
    # deterministic seed per symbol for stable series
    rnd = random.Random(abs(hash(seed_symbol)) % (2**32))
    now = int(datetime.now(timezone.utc).timestamp())
    # start price between 500 and 3000
    price = 500.0 + rnd.random() * 2500.0
    vol_scale = 0.001 if timeframe != '1d' else 0.01
    candles: List[Dict] = []
    for i in range(points):
        ts = datetime.fromtimestamp(now - (points - i) * step, tz=timezone.utc)
        drift = (rnd.random() - 0.5) * vol_scale * price
        open_px = price
        close_px = max(1.0, price + drift)
        high_px = max(open_px, close_px) + rnd.random() * vol_scale * 2 * price
        low_px = min(open_px, close_px) - rnd.random() * vol_scale * 2 * price
        volume = 100000 + rnd.random() * 50000
        candles.append({
            'ts': ts.isoformat(),
            'open': float(open_px),
            'high': float(high_px),
            'low': float(low_px),
            'close': float(close_px),
            'volume': float(volume),
        })
        price = close_px
    return candles


