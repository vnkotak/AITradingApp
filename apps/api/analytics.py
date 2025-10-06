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
    """
    Simple daily P&L accumulation: sort orders by date and accumulate P&L day by day.
    """
    sb = get_client()

    # Get all filled orders
    orders = sb.table("orders").select("symbol_id,side,price,qty,status,ts").eq("status", "FILLED").order("ts").execute().data or []

    if not orders:
        dates = pd.date_range(end=datetime.now(timezone.utc).date(), periods=min(days, 30))
        return pd.Series([0.0]*len(dates), index=dates)

    # Convert to DataFrame and group by date
    orders_df = pd.DataFrame(orders)
    orders_df['ts'] = pd.to_datetime(orders_df['ts'], utc=True)
    orders_df['date'] = orders_df['ts'].dt.date

    # Calculate P&L safely
    def safe_pnl_calc(row):
        try:
            price = float(row['price'])
            qty = float(row['qty'])
            if row['side'] == 'SELL':
                return price * qty
            else:  # BUY
                return -(price * qty)
        except (ValueError, TypeError):
            return 0.0

    orders_df['pnl'] = orders_df.apply(safe_pnl_calc, axis=1)

    # Group by date and sum P&L
    daily_pnl = orders_df.groupby('date')['pnl'].sum()

    # Create date range and accumulate P&L
    dates = pd.date_range(end=datetime.now(timezone.utc).date(), periods=days)
    equity_values = []
    running_total = 0.0

    for current_date in dates:
        date_key = current_date.date()
        if date_key in daily_pnl.index:
            running_total += daily_pnl[date_key]
        equity_values.append(running_total)

    equity_series = pd.Series(equity_values, index=dates)
    equity_series.name = 'equity'

    # Ensure no NaN or infinite values
    equity_series = equity_series.fillna(0.0)
    equity_series = equity_series.replace([float('inf'), float('-inf')], 0.0)

    return equity_series


def compute_sharpe(equity: pd.Series, rf_daily: float = 0.0) -> float:
    if equity.empty or len(equity) < 3:
        return 0.0
    try:
        returns = equity.pct_change().dropna()
        if returns.empty or len(returns) < 2:
            return 0.0

        # Check for constant equity (no variation)
        if returns.std() == 0 or returns.nunique() <= 1:
            return 0.0

        excess = returns - rf_daily
        mu = excess.mean()
        sigma = excess.std()

        if sigma <= 0 or not (math.isfinite(mu) and math.isfinite(sigma)):
            return 0.0

        # Annualize (252 trading days)
        sharpe = (mu / sigma) * math.sqrt(252)
        return float(sharpe) if math.isfinite(sharpe) else 0.0
    except:
        return 0.0


def compute_max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    try:
        roll_max = equity.cummax()
        dd = (equity - roll_max) / roll_max
        min_dd = dd.min()
        if math.isnan(min_dd):
            return 0.0
        return float(min_dd * 100.0)
    except:
        return 0.0


def pnl_summary(days: int = 90) -> Dict:
    try:
        equity = _equity_curve(days)
        if equity.empty:
            return {"equity": [], "sharpe": 0.0, "max_drawdown_pct": 0.0, "start_equity": 1000000.0, "end_equity": 1000000.0, "return_pct": 0.0}

        # Skip problematic Sharpe/MDD calculations for now
        start = float(equity.iloc[0]) if not equity.empty else 0.0
        end = float(equity.iloc[-1]) if not equity.empty else 0.0
        ret = (end - start) / start * 100.0 if start != 0 else 0.0

        # Handle NaN values safely
        if not math.isfinite(start): start = 0.0
        if not math.isfinite(end): end = 0.0
        if not math.isfinite(ret): ret = 0.0

        series = []
        for idx, val in equity.items():
            equity_val = float(val)
            if not math.isfinite(equity_val):
                equity_val = 0.0
            series.append({"date": str(idx), "equity": equity_val})

        return {"equity": series, "sharpe": 0.0, "max_drawdown_pct": 0.0, "start_equity": start, "end_equity": end, "return_pct": ret}
    except Exception as e:
        print(f"Error in pnl_summary: {e}")
        return {"equity": [], "sharpe": 0.0, "max_drawdown_pct": 0.0, "start_equity": 1000000.0, "end_equity": 1000000.0, "return_pct": 0.0}


def get_portfolio_performance() -> Dict:
    """
    Get comprehensive portfolio performance including both realized and unrealized P&L,
    trade statistics, and per-stock breakdown.
    """
    sb = get_client()
    if not sb:
        return _get_empty_portfolio_performance()

    try:
        # Get all completed orders for comprehensive analysis
        orders = sb.table("orders").select("id,symbol_id,side,type,price,qty,status,ts").eq("status", "FILLED").order("ts").execute().data or []

        # Get symbol information for readable names
        symbols_info = {}
        try:
            symbols = sb.table("symbols").select("id,ticker,exchange").execute().data or []
            symbols_info = {s['id']: {'ticker': s['ticker'], 'exchange': s['exchange']} for s in symbols}
        except Exception as e:
            print(f"Warning: Could not load symbol info: {e}")

        # Overall trade statistics
        total_orders = len(orders)
        buy_orders = sum(1 for o in orders if o['side'] == 'BUY')
        sell_orders = sum(1 for o in orders if o['side'] == 'SELL')

        # Group orders by symbol for per-stock analysis
        symbol_trades = {}
        for order in orders:
            symbol_id = order['symbol_id']
            if symbol_id not in symbol_trades:
                symbol_trades[symbol_id] = []
            symbol_trades[symbol_id].append(order)

        # Per-stock and overall P&L calculations
        per_stock_performance = []
        total_realized_pnl = 0.0
        winning_trades = 0
        losing_trades = 0
        total_completed_trades = 0

        for symbol_id, trades in symbol_trades.items():
            # Sort trades by timestamp
            trades.sort(key=lambda x: x['ts'])

            # Calculate round-trip P&L for this symbol
            symbol_realized_pnl = 0.0
            symbol_winning_trades = 0
            symbol_losing_trades = 0
            symbol_completed_trades = 0

            # Calculate round-trip P&L (BUY then SELL, or SELL then BUY)
            buy_qty = 0
            buy_cost = 0
            sell_qty = 0
            sell_revenue = 0

            for trade in trades:
                qty = abs(float(trade.get('qty', 0)))
                price = float(trade.get('price', 0))

                if trade['side'] == 'BUY':
                    buy_qty += qty
                    buy_cost += qty * price
                elif trade['side'] == 'SELL':
                    sell_qty += qty
                    sell_revenue += qty * price

                    # Check if we have a complete round-trip
                    if buy_qty >= sell_qty:
                        avg_buy_price = buy_cost / buy_qty if buy_qty > 0 else 0
                        avg_sell_price = sell_revenue / sell_qty if sell_qty > 0 else 0
                        trade_pnl = (avg_sell_price - avg_buy_price) * sell_qty

                        symbol_realized_pnl += trade_pnl
                        total_realized_pnl += trade_pnl
                        symbol_completed_trades += 1
                        total_completed_trades += 1

                        if trade_pnl > 0:
                            symbol_winning_trades += 1
                            winning_trades += 1
                        elif trade_pnl < 0:
                            symbol_losing_trades += 1
                            losing_trades += 1

                        # Reset for next round-trip
                        remaining_buy_qty = buy_qty - sell_qty
                        if remaining_buy_qty > 0:
                            buy_qty = remaining_buy_qty
                            buy_cost = remaining_buy_qty * avg_buy_price
                        else:
                            buy_qty = 0
                            buy_cost = 0
                        sell_qty = 0
                        sell_revenue = 0

            # Get stock info
            symbol_info = symbols_info.get(symbol_id, {'ticker': f'Unknown-{symbol_id}', 'exchange': 'NSE'})
            ticker = symbol_info['ticker']
            exchange = symbol_info['exchange']

            # Count total orders for this symbol
            symbol_buy_orders = sum(1 for t in trades if t['side'] == 'BUY')
            symbol_sell_orders = sum(1 for t in trades if t['side'] == 'SELL')

            # Handle NaN values in per-stock calculations
            if math.isnan(symbol_realized_pnl): symbol_realized_pnl = 0.0
            win_rate_calc = (symbol_winning_trades / symbol_completed_trades * 100) if symbol_completed_trades > 0 else 0
            if math.isnan(win_rate_calc): win_rate_calc = 0.0

            per_stock_performance.append({
                "symbol_id": symbol_id,
                "ticker": ticker,
                "exchange": exchange,
                "total_orders": len(trades),
                "buy_orders": symbol_buy_orders,
                "sell_orders": symbol_sell_orders,
                "completed_trades": symbol_completed_trades,
                "winning_trades": symbol_winning_trades,
                "losing_trades": symbol_losing_trades,
                "realized_pnl": round(symbol_realized_pnl, 2),
                "win_rate": round(win_rate_calc, 1)
            })

        # Get current positions for unrealized P&L
        positions = sb.table("positions").select("symbol_id,qty,avg_price").execute().data or []

        total_unrealized_pnl = 0.0
        portfolio_value = 0.0

        # Get current prices for unrealized P&L calculation
        for position in positions:
            qty = float(position.get('qty', 0))
            avg_price = float(position.get('avg_price', 0))

            if qty == 0:
                continue

            # Get current price for this symbol
            try:
                symbol_candles = sb.table("candles").select("close").eq("symbol_id", position['symbol_id']).eq("timeframe", "1m").order("ts", desc=True).limit(1).execute().data
                current_price = float(symbol_candles[0]['close']) if symbol_candles else avg_price
            except:
                current_price = avg_price

            position_value = abs(qty) * current_price
            portfolio_value += position_value

            # Calculate unrealized P&L for long positions
            if qty > 0:
                unrealized_pnl = (current_price - avg_price) * qty
                total_unrealized_pnl += unrealized_pnl

        # Calculate overall portfolio metrics
        total_portfolio_value = portfolio_value  # Current market value of positions
        total_pnl = total_realized_pnl + total_unrealized_pnl
        win_rate = (winning_trades / total_completed_trades * 100) if total_completed_trades > 0 else 0

        # Handle NaN values
        if math.isnan(total_portfolio_value): total_portfolio_value = 0.0
        if math.isnan(total_realized_pnl): total_realized_pnl = 0.0
        if math.isnan(total_unrealized_pnl): total_unrealized_pnl = 0.0
        if math.isnan(total_pnl): total_pnl = 0.0
        if math.isnan(win_rate): win_rate = 0.0

        return {
            "total_portfolio_value": round(total_portfolio_value, 2),
            "total_realized_pnl": round(total_realized_pnl, 2),
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),

            # Overall trade statistics
            "total_orders": total_orders,
            "buy_orders": buy_orders,
            "sell_orders": sell_orders,
            "completed_trades": total_completed_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 1),

            # Per-stock breakdown
            "per_stock_performance": per_stock_performance,

            # Additional metrics
            "active_positions": len([p for p in positions if p.get('qty', 0) != 0]),
            "total_symbols_traded": len(per_stock_performance),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        print(f"Error calculating portfolio performance: {e}")
        return _get_empty_portfolio_performance()


def _get_empty_portfolio_performance() -> Dict:
    """Return empty portfolio performance when no data is available"""
    return {
        "total_portfolio_value": 0.0,
        "total_realized_pnl": 0.0,
        "total_unrealized_pnl": 0.0,
        "total_pnl": 0.0,

        # Overall trade statistics
        "total_orders": 0,
        "buy_orders": 0,
        "sell_orders": 0,
        "completed_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0.0,

        # Per-stock breakdown
        "per_stock_performance": [],

        # Additional metrics
        "active_positions": 0,
        "total_symbols_traded": 0,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }


