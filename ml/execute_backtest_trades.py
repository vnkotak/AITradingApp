import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Literal
import pandas as pd

# Import the backtest logic
from backtest import backtest_strategy, load_candles, strategy_signals, add_indicators, supabase_client, load_symbols
from strategies.engine import trend_follow, mean_reversion, momentum, signal_quality_filter

Timeframe = Literal['1m','5m','15m','1h','1d']

def execute_backtest_trades(start_date: str = "2025-09-20", end_date: str = "2025-10-04"):
    """
    Run comprehensive backtest for all strategies and timeframes from start_date to end_date.
    """
    print("🚀 EXECUTING COMPREHENSIVE BACKTEST TRADES")
    print(f"📅 Date range: {start_date} to {end_date}")
    print("🧠 Strategies: trend_follow, mean_reversion, momentum")
    print("⏰ Timeframes: 1m, 5m, 15m, 1h, 1d")

    # Initialize Supabase client
    sb = supabase_client()

    # All strategies and timeframes to test - reduced for testing
    strategies = ['trend_follow', 'mean_reversion', 'momentum']
    timeframes = ['5m', '15m', '1h']  # Reduced for testing

    # Load symbols - reduced for testing
    symbols = load_symbols(limit=5)  # Reduced for testing
    print(f"📊 Loaded {len(symbols)} symbols for backtesting")

    total_trades_executed = 0
    total_combinations = len(symbols) * len(strategies) * len(timeframes)

    print(f"🎯 Total combinations to process: {total_combinations}")

    combination_count = 0

    for strategy in strategies:
        for tf in timeframes:
            for i, symbol in enumerate(symbols, 1):
                combination_count += 1
                symbol_id = symbol['id']
                ticker = symbol['ticker']
                exchange = symbol['exchange']

                print(f"\n📈 [{combination_count}/{total_combinations}] {strategy} | {tf} | {ticker}.{exchange}")

                try:
                    # Check if we have data for this symbol and timeframe in our date range
                    data_check = sb.table("candles").select("ts").eq("symbol_id", symbol_id).eq("timeframe", tf).gte("ts", f"{start_date}T00:00:00Z").lte("ts", f"{end_date}T23:59:59Z").limit(1).execute()

                    if not data_check.data or len(data_check.data) == 0:
                        print(f"  ⚠️ No {tf} data for {ticker} in date range")
                        continue

                    # Load candle data for this timeframe
                    candles_data = sb.table("candles").select("ts,open,high,low,close,volume").eq("symbol_id", symbol_id).eq("timeframe", tf).gte("ts", f"{start_date}T00:00:00Z").lte("ts", f"{end_date}T23:59:59Z").order("ts").execute().data

                    if not candles_data or len(candles_data) < 10:
                        print(f"  ⚠️ Insufficient {tf} data for {ticker} (found {len(candles_data) if candles_data else 0} candles)")
                        continue

                    # Convert to DataFrame
                    df = pd.DataFrame(candles_data)
                    for k in ["open","high","low","close","volume"]:
                        df[k] = pd.to_numeric(df[k], errors='coerce')
                    df["ts"] = pd.to_datetime(df["ts"], utc=True)
                    df = df.dropna().reset_index(drop=True)

                    print(f"  📊 {len(df)} {tf} candles loaded for {ticker}")

                    # Add indicators
                    df_with_indicators = add_indicators(df)

                    # Generate signals
                    signals = strategy_signals(df_with_indicators, strategy)

                    # Count signals
                    buy_signals = (signals == 'BUY').sum()
                    sell_signals = (signals == 'SELL').sum()

                    if buy_signals + sell_signals == 0:
                        print(f"  🎯 No signals generated for {strategy} on {tf}")
                        continue

                    print(f"  🎯 Signals generated: {buy_signals} BUY, {sell_signals} SELL")

                    # Execute trades based on signals with historical timestamps and prices
                    executed_trades = execute_signals_as_trades_historical(
                        sb, symbol_id, ticker, exchange, df_with_indicators, signals, strategy, tf
                    )

                    total_trades_executed += executed_trades
                    print(f"  ✅ Executed {executed_trades} trades for {ticker} ({strategy} on {tf})")

                except Exception as e:
                    print(f"  ❌ Error processing {ticker} {strategy} {tf}: {e}")
                    continue

    print("\n🎯 COMPREHENSIVE BACKTEST EXECUTION COMPLETE")
    print(f"  Total combinations processed: {combination_count}")
    print(f"  Total symbols tested: {len(symbols)}")
    print(f"  Total strategies tested: {len(strategies)}")
    print(f"  Total timeframes tested: {len(timeframes)}")
    print(f"  Total trades executed: {total_trades_executed}")

def execute_signals_as_trades_historical(sb, symbol_id: str, ticker: str, exchange: str, df: pd.DataFrame, signals: pd.Series, strategy: str, timeframe: str) -> int:
    """
    Execute BUY/SELL signals as actual trades in the database with historical timestamps and prices.
    Each signal creates an order with the exact timestamp and price when the signal was generated.
    Properly tracks position state to prevent invalid SELL orders.
    """
    trades_executed = 0
    current_position_qty = 0  # Track position locally for this symbol/strategy/timeframe combination
    current_avg_price = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        signal = signals.iloc[i]

        if pd.isna(signal) or signal not in ['BUY', 'SELL']:
            continue

        price = float(row['close'])
        timestamp = row['ts'].isoformat()

        # Validate order based on current position
        if signal == 'SELL' and current_position_qty <= 0:
            # Cannot sell if we don't have a position
            print(f"    ⚠️ Skipping SELL signal - no position in {ticker} (current qty: {current_position_qty})")
            continue
        elif signal == 'BUY' and current_position_qty < 0:
            # If we have a short position, buying would close it
            # For simplicity in backtest, we'll allow it but could add more complex logic
            pass

        try:
            # Create order with historical timestamp and price
            order_data = {
                "symbol_id": symbol_id,
                "ts": timestamp,  # Use historical timestamp when signal was generated
                "side": signal,  # BUY or SELL
                "type": "MARKET",
                "price": price,  # Use price from the candle where signal was generated
                "qty": 10,  # Small quantity for backtest
                "status": "FILLED",
                "simulator_notes": f"Backtest {strategy} {timeframe} {signal} order",
                "slippage_bps": 0.0
            }

            order_result = sb.table("orders").insert(order_data).execute()
            order_id = order_result.data[0]['id']

            # Update local position tracking
            if signal == 'BUY':
                if current_position_qty == 0:
                    current_avg_price = price
                    current_position_qty = 10
                else:
                    # Calculate new average price for additional position
                    current_position_qty += 10
                    current_avg_price = ((current_position_qty - 10) * current_avg_price + 10 * price) / current_position_qty
            else:  # SELL
                current_position_qty -= 10
                # Average price stays the same for sells

            # Update position in database for backtest results
            # This will show the final position state in the Portfolio tab for P&L calculation
            try:
                existing_positions = sb.table("positions").select("*").eq("symbol_id", symbol_id).execute().data

                if existing_positions:
                    # Update existing position with backtest results
                    pos = existing_positions[0]
                    sb.table("positions").update({
                        "qty": current_position_qty,
                        "avg_price": current_avg_price,
                        "updated_at": timestamp
                    }).eq("id", pos['id']).execute()
                    print(f"    📊 Position updated: {current_position_qty} shares @ ₹{current_avg_price:.2f}")
                else:
                    # Create new position record
                    position_data = {
                        "symbol_id": symbol_id,
                        "qty": current_position_qty,
                        "avg_price": current_avg_price,
                        "unrealized_pnl": 0.0,
                        "realized_pnl": 0.0,
                        "updated_at": timestamp
                    }
                    sb.table("positions").insert(position_data).execute()
                    print(f"    📊 Position created: {current_position_qty} shares @ ₹{current_avg_price:.2f}")

            except Exception as e:
                print(f"    ⚠️ Position update failed: {e}")
                print(f"    📊 Local position: {current_position_qty} shares @ ₹{current_avg_price:.2f}")

            print(f"    ✅ Created order {order_id[:8]}... for {signal} at ₹{price:.2f} on {row['ts'].strftime('%Y-%m-%d %H:%M')} (position: {current_position_qty})")
            trades_executed += 1

        except Exception as e:
            print(f"    ❌ Error executing trade at {timestamp}: {e}")
            continue

    print(f"    📊 Final position for {ticker} ({strategy} {timeframe}): {current_position_qty} shares")
    return trades_executed

if __name__ == "__main__":
    # Execute comprehensive backtest for all strategies and timeframes from Sep 20 to present
    execute_backtest_trades(
        start_date="2025-09-20",  # Extended date range from September 20
        end_date="2025-10-04"    # To present (October 4)
    )