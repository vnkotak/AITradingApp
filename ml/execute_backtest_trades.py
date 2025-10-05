import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Literal
import pandas as pd

# Import the backtest logic
from backtest import backtest_strategy, load_candles, strategy_signals, add_indicators, supabase_client, load_symbols
from strategies.engine import trend_follow, mean_reversion, momentum, signal_quality_filter

# Import common trade execution logic
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))
from trade_execution import TradeExecutor

Timeframe = Literal['1m','5m','15m','1h','1d']

def execute_backtest_trades(start_date: str = "2025-09-01", end_date: str = "2025-10-04"):
    """
    Run comprehensive backtest for all strategies and timeframes from start_date to end_date.
    Processes signals chronologically across all timeframes for realistic simulation.
    """
    print("🚀 EXECUTING COMPREHENSIVE CHRONOLOGICAL BACKTEST TRADES")
    print(f"📅 Date range: {start_date} to {end_date}")
    print("🧠 Strategies: trend_follow, mean_reversion, momentum")
    print("⏰ Timeframes: 1m, 5m, 15m, 1h, 1d")

    # Initialize Supabase client
    sb = supabase_client()

    # All strategies and timeframes to test - reduced for testing
    strategies = ['trend_follow', 'mean_reversion','momentum']
    timeframes = ['1m', '5m', '15m', '1h', '1d']

    # Load symbols - reduced for testing
    symbols = load_symbols(limit=50)  # Reduced for testing
    print(f"📊 Loaded {len(symbols)} symbols for backtesting")

    total_trades_executed = 0

    # Process each symbol chronologically across all timeframes
    for i, symbol in enumerate(symbols, 1):
        symbol_id = symbol['id']
        ticker = symbol['ticker']
        exchange = symbol['exchange']

        print(f"\n📈 [{i}/{len(symbols)}] {ticker}.{exchange} - Chronological Processing")

        try:
            # Collect all signals from all timeframes for this symbol
            all_signals = []

            for strategy in strategies:
                for tf in timeframes:
                    try:
                        # Check if we have data for this symbol and timeframe in our date range
                        data_check = sb.table("candles").select("ts").eq("symbol_id", symbol_id).eq("timeframe", tf).gte("ts", f"{start_date}T00:00:00Z").lte("ts", f"{end_date}T23:59:59Z").limit(1).execute()

                        if not data_check or not data_check.data or len(data_check.data) == 0:
                            continue

                        # Load candle data for this timeframe
                        candles_data = sb.table("candles").select("ts,open,high,low,close,volume").eq("symbol_id", symbol_id).eq("timeframe", tf).gte("ts", f"{start_date}T00:00:00Z").lte("ts", f"{end_date}T23:59:59Z").order("ts").execute().data

                        if not candles_data or len(candles_data) < 10:
                            continue

                        # Convert to DataFrame
                        df = pd.DataFrame(candles_data)
                        for k in ["open","high","low","close","volume"]:
                            df[k] = pd.to_numeric(df[k], errors='coerce')
                        df["ts"] = pd.to_datetime(df["ts"], utc=True)
                        df = df.dropna().reset_index(drop=True)

                        # Add indicators
                        df_with_indicators = add_indicators(df)

                        # Generate signals
                        signals = strategy_signals(df_with_indicators, strategy)

                        # Collect signals with metadata
                        for idx, signal_action in signals.items():
                            if pd.notna(signal_action) and signal_action in ['BUY', 'SELL']:
                                all_signals.append({
                                    'timestamp': df_with_indicators.iloc[idx]['ts'],
                                    'price': df_with_indicators.iloc[idx]['close'],
                                    'action': signal_action,
                                    'timeframe': tf,
                                    'strategy': strategy,
                                    'df_index': idx,
                                    'candle_data': df_with_indicators.iloc[idx]
                                })

                    except Exception as e:
                        print(f"  ⚠️ Error processing {strategy} {tf}: {e}")
                        continue

            # Sort all signals chronologically
            all_signals.sort(key=lambda x: x['timestamp'])

            print(f"  📊 Collected {len(all_signals)} total signals across all timeframes")

            # Count signals by type
            buy_signals = sum(1 for s in all_signals if s['action'] == 'BUY')
            sell_signals = sum(1 for s in all_signals if s['action'] == 'SELL')
            print(f"  🎯 Signals: {buy_signals} BUY, {sell_signals} SELL")

            if not all_signals:
                print(f"  ⏭️ No signals for {ticker}, skipping")
                continue

            # Execute signals chronologically
            print(symbol_id)
            executed_trades = execute_signals_chronologically(
                sb, symbol_id, ticker, exchange, all_signals
            )

            total_trades_executed += executed_trades
            print(f"  ✅ Executed {executed_trades} trades for {ticker}")

        except Exception as e:
            print(f"  ❌ Error processing {ticker}: {e}")
            continue

    print("\n🎯 CHRONOLOGICAL BACKTEST EXECUTION COMPLETE")
    print(f"  Total symbols processed: {len(symbols)}")
    print(f"  Total trades executed: {total_trades_executed}")

def aggregate_signals(signals: list, symbol_id: str, time_window_minutes: int = 5) -> list:
    """
    Aggregate signals within time windows to prevent multiple small orders.
    Combines signals of the same action within the time window.
    """
    if not signals:
        return []

    # Sort signals by timestamp
    from datetime import datetime
    sorted_signals = sorted(signals, key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')) if isinstance(x['timestamp'], str) else x['timestamp'])
    aggregated = []

    current_group = None

    for signal in sorted_signals:
        # Create group key based on symbol, action, and time window
        signal_time = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00')) if isinstance(signal['timestamp'], str) else signal['timestamp']
        group_key = f"{symbol_id}_{signal['action']}"

        # Check if this signal can be grouped with the current group
        if (current_group and
            current_group['group_key'] == group_key and
            abs((signal_time - current_group['last_time']).total_seconds()) <= time_window_minutes * 60):

            # Add to existing group
            current_group['signals'].append(signal)
            current_group['last_time'] = signal_time
            current_group['total_qty'] += signal.get('qty', 10)
        else:
            # Start new group
            if current_group:
                aggregated.append(current_group)

            current_group = {
                'group_key': group_key,
                'symbol_id': symbol_id,
                'action': signal['action'],
                'timestamp': signal_time,
                'last_time': signal_time,
                'signals': [signal],
                'total_qty': signal.get('qty', 10),
                'avg_price': signal['price'],
                'timeframe': signal['timeframe'],
                'strategy': signal['strategy'],
                'candle_data': signal['candle_data']
            }

    # Add the last group
    if current_group:
        aggregated.append(current_group)

    # Convert back to signal format with aggregated quantities
    final_signals = []
    for group in aggregated:
        # Use the first signal as base, but with aggregated quantity
        base_signal = group['signals'][0].copy()
        base_signal['qty'] = group['total_qty']
        # Use average price across the group
        avg_price = sum(s['price'] for s in group['signals']) / len(group['signals'])
        base_signal['price'] = avg_price
        final_signals.append(base_signal)

    return final_signals


def execute_signals_chronologically(sb, symbol_id: str, ticker: str, exchange: str, all_signals: list) -> int:
    """
    Execute signals in chronological order across all timeframes for realistic backtesting.
    Now with signal aggregation to prevent multiple small orders.
    """
    if not sb or not all_signals:
        return 0

    # Aggregate signals to prevent multiple small orders within time windows
    aggregated_signals = aggregate_signals(all_signals, symbol_id, time_window_minutes=5)

    print(f"  📊 Aggregated {len(all_signals)} raw signals into {len(aggregated_signals)} orders")

    # Use common trade executor with backtest settings
    trade_executor = TradeExecutor(
        enable_advanced_exits=False,  # Pure signal testing for backtest
        enable_timeframe_precedence=True  # Respect timeframe hierarchy
    )

    trades_executed = 0
    current_position = {'qty': 0, 'avg_price': 0.0}
    position_timeframe = None
    entry_indicators = None  # Store indicators from position entry

    # Load existing position from database (should be clean for fresh backtest)
    try:
        existing_pos_result = sb.table("positions").select("qty", "avg_price").eq("symbol_id", symbol_id).execute()
        if existing_pos_result and existing_pos_result.data and len(existing_pos_result.data) > 0:
            pos = existing_pos_result.data[0]
            current_position = {
                'qty': float(pos.get('qty', 0)),
                'avg_price': float(pos.get('avg_price', 0))
            }
            print(f"    📊 Starting with existing position: {current_position['qty']} shares")
    except Exception as e:
        print(f"    ⚠️ Could not load position: {e}")

    # Process each aggregated signal in chronological order
    for signal_data in aggregated_signals:
        try:
            timestamp = signal_data['timestamp']
            price = signal_data['price']
            action = signal_data['action']
            timeframe = signal_data['timeframe']
            strategy = signal_data['strategy']

            # Create signal dict for validation
            signal = {
                'action': action,
                'timeframe': timeframe,
                'confidence': 0.8,
                'symbol_id': symbol_id,
                'ticker': ticker,
                'exchange': exchange
            }

            # Additional momentum failure check for existing positions
            momentum_exit = False
            if action == 'BUY' and current_position['qty'] > 0 and entry_indicators:
                # Check if we should exit due to momentum failure before adding to position
                current_candle_indicators = {k: v for k, v in signal_data.get('candle_data', {}).items()
                                           if k in ['rsi14', 'macd', 'macd_hist', 'adx14', 'bb_width',
                                                   'ema20', 'ema50', 'volume']}
                momentum_exit, momentum_reason = trade_executor.should_exit_on_momentum_failure(
                    entry_indicators, current_candle_indicators
                )
                if momentum_exit:
                    print(f"    🚨 {timestamp.strftime('%m-%d %H:%M')} Momentum failure detected - {momentum_reason}")
                    # Force a SELL signal to exit position
                    action = 'SELL'
                    signal['action'] = 'SELL'
                    momentum_exit = True

            # Validate signal using trade executor
            should_execute, reason = trade_executor.should_execute_signal(
                signal=signal,
                current_position=current_position,
                position_timeframe=position_timeframe
            )

            if not should_execute:
                reason_text = f"{reason} (momentum_failure)" if momentum_exit else reason
                print(f"    ⏭️ {timestamp.strftime('%m-%d %H:%M')} {timeframe} {action} skipped - {reason_text}")
                continue

            # Calculate position size with confidence-based scaling
            confidence = signal.get('confidence', 0.8)
            qty = trade_executor.calculate_position_size(
                action=action,
                symbol=ticker,
                entry_price=price,
                timeframe=timeframe,
                risk_limits={'max_position_value': 10000},
                portfolio_value=100000,  # Assume $100K portfolio for backtesting
                confidence=confidence
            )

            # Extract technical indicators from candle data for detailed analysis
            candle_data = signal_data.get('candle_data', {})
            indicators = {
                "strategy": strategy,
                "timeframe": timeframe,
                "entry_price": price,
                "confidence": 0.8,
                "indicators": {
                    "rsi14": float(candle_data.get('rsi14', 0)) if not pd.isna(candle_data.get('rsi14')) else None,
                    "ema20": float(candle_data.get('ema20', 0)) if not pd.isna(candle_data.get('ema20')) else None,
                    "ema50": float(candle_data.get('ema50', 0)) if not pd.isna(candle_data.get('ema50')) else None,
                    "macd": float(candle_data.get('macd', 0)) if not pd.isna(candle_data.get('macd')) else None,
                    "macd_signal": float(candle_data.get('macd_signal', 0)) if not pd.isna(candle_data.get('macd_signal')) else None,
                    "macd_hist": float(candle_data.get('macd_hist', 0)) if not pd.isna(candle_data.get('macd_hist')) else None,
                    "bb_upper": float(candle_data.get('bb_upper', 0)) if not pd.isna(candle_data.get('bb_upper')) else None,
                    "bb_mid": float(candle_data.get('bb_mid', 0)) if not pd.isna(candle_data.get('bb_mid')) else None,
                    "bb_lower": float(candle_data.get('bb_lower', 0)) if not pd.isna(candle_data.get('bb_lower')) else None,
                    "bb_width": float(candle_data.get('bb_width', 0)) if not pd.isna(candle_data.get('bb_width')) else None,
                    "atr14": float(candle_data.get('atr14', 0)) if not pd.isna(candle_data.get('atr14')) else None,
                    "adx14": float(candle_data.get('adx14', 0)) if not pd.isna(candle_data.get('adx14')) else None,
                    "vwap": float(candle_data.get('vwap', 0)) if not pd.isna(candle_data.get('vwap')) else None,
                    "close": float(candle_data.get('close', 0)) if not pd.isna(candle_data.get('close')) else None,
                    "volume": float(candle_data.get('volume', 0)) if not pd.isna(candle_data.get('volume')) else None
                }
            }

            # Create order with detailed technical context
            order_data = {
                "symbol_id": symbol_id,
                "ts": timestamp.isoformat(),
                "side": action,
                "type": "MARKET",
                "price": price,
                "qty": qty,
                "status": "FILLED",
                "simulator_notes": indicators,
                "slippage_bps": 0.0
            }

            order_result = sb.table("orders").insert(order_data).execute()
            if not order_result or not order_result.data or len(order_result.data) == 0:
                print(f"    ❌ Order insertion failed for {action} at {timestamp}")
                continue

            order_id = order_result.data[0]['id']

            # Update position
            current_position = trade_executor.update_position(
                symbol_id=symbol_id,
                action=action,
                quantity=qty,
                price=price,
                current_position=current_position
            )

            # Track position timeframe and entry indicators
            if action == 'BUY' and current_position['qty'] > 0:
                position_timeframe = timeframe
                # Store entry indicators for momentum failure detection
                entry_indicators = {k: v for k, v in signal_data.get('candle_data', {}).items()
                                  if k in ['rsi14', 'macd', 'macd_hist', 'adx14', 'bb_width',
                                          'ema20', 'ema50', 'volume']}
                print(f"    📊 Entry indicators stored: RSI {entry_indicators.get('rsi14', 'N/A'):.1f}, MACD {entry_indicators.get('macd', 'N/A'):.3f}")
            elif action == 'SELL' and current_position['qty'] == 0:
                # Position closed - reset entry indicators
                entry_indicators = None
                position_timeframe = None
                print(f"    🔄 Position closed - indicators reset")

            # Update position in database
            try:
                positions_result = sb.table("positions").select("*").eq("symbol_id", symbol_id).execute()
                existing_positions = positions_result.data if positions_result and positions_result.data else []

                if existing_positions:
                    pos = existing_positions[0]
                    sb.table("positions").update({
                        "qty": current_position['qty'],
                        "avg_price": current_position['avg_price'],
                        "updated_at": timestamp.isoformat()
                    }).eq("id", pos['id']).execute()
                else:
                    position_data = {
                        "symbol_id": symbol_id,
                        "qty": current_position['qty'],
                        "avg_price": current_position['avg_price'],
                        "unrealized_pnl": 0.0,
                        "realized_pnl": 0.0,
                        "updated_at": timestamp.isoformat()
                    }
                    sb.table("positions").insert(position_data).execute()

            except Exception as e:
                print(f"    ⚠️ Position update failed: {e}")

            print(f"    ✅ {timestamp.strftime('%m-%d %H:%M')} {timeframe} {action} {qty} @ ₹{price:.2f} (pos: {current_position['qty']})")
            trades_executed += 1

        except Exception as e:
            print(f"    ❌ Error processing signal: {e}")
            continue

    print(f"    📊 Final position for {ticker}: {current_position['qty']} shares")
    return trades_executed

if __name__ == "__main__":
    # Execute comprehensive backtest for all strategies and timeframes from Sep 20 to present
    execute_backtest_trades(
        start_date="2025-09-01",  # Extended date range from September 20
        end_date="2025-10-04"    # To present (October 4)
    )