from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
import math
import pandas as pd

from apps.api.supabase_client import get_client


def _daily_prices(symbol_id: str, days: int = 90) -> pd.DataFrame:
    sb = get_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    data = (
        sb.table("candles").select("ts,close").eq("symbol_id", symbol_id).eq("timeframe", "1d").gte("ts", since).order("ts").execute().data
    )
    df = pd.DataFrame(data or [])
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["date"] = df["ts"].dt.date
    return df[["date","close"]]


def _equity_curve(days: int = 90) -> pd.Series:
    sb = get_client()
    # base equity from last pnl_daily or default 10L
    start_equity = 1000000.0
    base = sb.table("pnl_daily").select("trade_date,equity").order("trade_date", desc=True).limit(1).execute().data
    if base:
        start_equity = float(base[0]["equity"]) or start_equity
    # build daily map for symbols held
    positions = sb.table("positions").select("symbol_id,avg_price,qty").execute().data or []
    symbol_ids = list({p["symbol_id"] for p in positions})
    if not symbol_ids:
        # No positions → equity flat
        dates = pd.date_range(end=datetime.now(timezone.utc).date(), periods=min(days, 30))
        return pd.Series([start_equity]*len(dates), index=dates)
    # combine daily close for each symbol
    frames: List[pd.DataFrame] = []
    for sid in symbol_ids:
        df = _daily_prices(sid, days)
        if df.empty:
            continue
        frames.append(df.rename(columns={"close": sid}).set_index("date")[[sid]])
    if not frames:
        dates = pd.date_range(end=datetime.now(timezone.utc).date(), periods=min(days, 30))
        return pd.Series([start_equity]*len(dates), index=dates)
    prices = pd.concat(frames, axis=1).fillna(method='ffill')
    # position vector
    qty_map = {p["symbol_id"]: float(p.get("qty",0) or 0) for p in positions}
    # compute portfolio value over time (sum price * qty)
    port_vals = prices.apply(lambda row: sum(row.get(col, 0.0) * qty_map.get(col, 0.0) for col in prices.columns), axis=1)
    equity = start_equity + (port_vals - port_vals.iloc[0])
    equity.name = 'equity'
    return equity


def compute_sharpe(equity: pd.Series, rf_daily: float = 0.0) -> float:
    if equity.empty or len(equity) < 3:
        return 0.0
    returns = equity.pct_change().dropna()
    excess = returns - rf_daily
    mu = excess.mean()
    sigma = excess.std()
    if sigma == 0 or math.isnan(sigma):
        return 0.0
    # Annualize (252 trading days)
    sharpe = (mu / sigma) * math.sqrt(252)
    return float(sharpe)


def compute_max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    return float(dd.min() * 100.0)


def pnl_summary(days: int = 90) -> Dict:
    equity = _equity_curve(days)
    if equity.empty:
        return {"equity": [], "sharpe": 0.0, "max_drawdown_pct": 0.0, "start_equity": 0.0, "end_equity": 0.0, "return_pct": 0.0}
    sharpe = compute_sharpe(equity)
    mdd = compute_max_drawdown(equity)
    start = float(equity.iloc[0]); end = float(equity.iloc[-1])
    ret = (end - start) / start * 100.0 if start else 0.0
    series = [{"date": str(idx), "equity": float(val)} for idx, val in equity.items()]
    return {"equity": series, "sharpe": sharpe, "max_drawdown_pct": mdd, "start_equity": start, "end_equity": end, "return_pct": ret}


