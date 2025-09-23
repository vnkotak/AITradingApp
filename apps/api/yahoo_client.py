from datetime import datetime, timedelta, timezone
from typing import Literal, List, Dict
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
    df = yf.download(yf_symbol, interval=interval, start=start, end=end, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return []
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
                continue
        candles.append({
            'ts': ts.isoformat(),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': float(row.get('Volume', 0) or 0),
        })
    return candles


