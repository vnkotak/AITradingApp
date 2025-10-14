#!/usr/bin/env python3
"""
Test signal generation for TATACOMM and DIVISLAB with adjusted parameters
"""
import sys
sys.path.append('apps/api')

from supabase_client import get_client
import pandas as pd
from signal_generator import score_signal, _feature_contributions
from strategies.indicators import add_core_indicators
import numpy as np

def test_signals_for_stock(ticker):
    """Test signal generation for a specific stock"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING SIGNALS FOR {ticker}")
    print(f"{'='*60}")

    sb = get_client()
    if not sb:
        print("❌ Database connection failed")
        return

    # Get symbol info
    sym = sb.table('symbols').select('id, ticker, exchange').eq('ticker', ticker).single().execute().data
    if not sym:
        print(f"❌ {ticker} not found in database")
        return

    print(f"✅ Found {ticker} (ID: {sym['id']})")

    # Get recent candles (last 300 for analysis)
    candles = sb.table('candles').select('*').eq('symbol_id', sym['id']).eq('timeframe', '1m').order('ts', desc=True).limit(300).execute().data

    if not candles or len(candles) < 100:
        print(f"❌ Insufficient candle data for {ticker}: {len(candles) if candles else 0} candles")
        return

    print(f"✅ Retrieved {len(candles)} recent 1m candles")

    # Convert to DataFrame and prepare
    df = pd.DataFrame(candles)
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.sort_values('ts').reset_index(drop=True)

    # Add technical indicators
    df = add_core_indicators(df)
    df = df.dropna()

    if len(df) < 50:
        print(f"❌ Insufficient data after adding indicators: {len(df)} rows")
        return

    print(f"✅ Data ready: {len(df)} rows with {len(df.columns)} columns")
    print(f"   Date range: {df.ts.min()} to {df.ts.max()}")
    print(f"   Latest close: ₹{df.iloc[-1].close:.2f}")

    # Test signal generation on recent data points
    recent_data = df.tail(30)  # Test on last 30 candles
    buy_signals_found = 0

    print("
🎯 Testing signal generation on recent candles..."    for i in range(10, len(recent_data), 5):  # Test every 5th candle
        test_df = recent_data.iloc[:i+1].copy()
        if len(test_df) < 30:
            continue

        try:
            # Test BUY signal
            confidence, rationale = score_signal(test_df, 'BUY', 0.5, {'ticker': ticker, 'exchange': 'NSE'})

            if confidence > 0.5:  # Lower threshold for testing
                timestamp = test_df.iloc[-1]['ts']
                entry_price = test_df.iloc[-1]['close']
                buy_signals_found += 1

                print("02d"                print(".2f"
                # Show key indicators
                last_row = test_df.iloc[-1]
                print("                   RSI: .1f"
                if 'macd' in last_row and 'macd_signal' in last_row:
                    macd_diff = last_row['macd'] - last_row['macd_signal']
                    print("                   MACD: .3f"
                if 'adx14' in last_row:
                    print("                   ADX: .1f"
                print(".3f"                print()

        except Exception as e:
            print(f"❌ Error testing signal at index {i}: {e}")
            continue

    print("
📊 SUMMARY:"    print(f"   Total test points: {len(range(10, len(recent_data), 5))}")
    print(f"   BUY signals found: {buy_signals_found}")
    print(".1f"
    # Show final technical state
    final_row = df.iloc[-1]
    print("
📈 FINAL TECHNICAL STATE:"    print(".2f"    print(".1f"    if 'macd' in final_row and 'macd_signal' in final_row:
        macd_diff = final_row['macd'] - final_row['macd_signal']
        print(".3f"    if 'adx14' in final_row:
        print(".1f"    if 'bb_upper' in final_row and 'bb_lower' in final_row:
        bb_position = (final_row['close'] - final_row['bb_lower']) / (final_row['bb_upper'] - final_row['bb_lower'])
        print(".1f"
def main():
    print("🧪 Testing adjusted signal generation for TATACOMM and DIVISLAB")

    test_signals_for_stock('TATACOMM')
    test_signals_for_stock('DIVISLAB')

if __name__ == "__main__":
    main()