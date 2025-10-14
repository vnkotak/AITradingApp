#!/usr/bin/env python3
"""
Debug why TATACOMM and DIVISLAB are not generating signals
"""
import sys
sys.path.append('apps/api')

from supabase_client import get_client
import pandas as pd
from strategies.indicators import add_core_indicators
from strategies.engine import trend_follow, signal_quality_filter
from signal_generator import score_signal

def debug_stock_signals(ticker):
    print(f"\n{'='*60}")
    print(f"🔍 DEBUGGING {ticker}")
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

    # Get recent candles (last 100 for analysis)
    candles = sb.table('candles').select('*').eq('symbol_id', sym['id']).eq('timeframe', '1m').order('ts', desc=True).limit(100).execute().data

    if not candles or len(candles) < 50:
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

    if len(df) < 20:
        print(f"❌ Insufficient data after adding indicators: {len(df)} rows")
        return

    print(f"✅ Data ready: {len(df)} rows with indicators")

    # Show latest technical indicators
    latest = df.iloc[-1]
    print("\n📊 Latest Technical Indicators:")
    print(f"  Close: ₹{latest['close']:.2f}")
    print(f"  RSI: {latest['rsi14']:.1f}")
    print(f"  MACD: {latest['macd']:.3f}")
    print(f"  MACD Signal: {latest['macd_signal']:.3f}")
    print(f"  MACD Hist: {latest['macd_hist']:.3f}")
    print(f"  EMA20: ₹{latest['ema20']:.2f}")
    print(f"  EMA50: ₹{latest['ema50']:.2f}")
    print(f"  ADX: {latest['adx14']:.1f}")
    print(f"  ATR: ₹{latest['atr14']:.2f}")
    print(f"  BB Width: {latest['bb_width']:.3f}")
    print(f"  VWAP: ₹{latest['vwap']:.2f}")
    print(f"  Volume: {latest['volume']:.0f}")

    # Show volume data for last 5 candles
    print(f"\n📊 Volume data for last 5 candles:")
    for i in range(min(5, len(df))):
        idx = len(df) - 1 - i
        row = df.iloc[idx]
        print(f"  Candle {i+1} ({row['ts']}): Volume = {row['volume']:.0f}")

    # Check trend_follow strategy requirements
    print("\n🎯 Checking Strategy Requirements:")
    ema_cross = df.iloc[-2]['ema20'] <= df.iloc[-2]['ema50'] and latest['ema20'] > latest['ema50']
    ema_rising = latest['ema20'] > df.iloc[-2]['ema20']
    rsi_ok = latest['rsi14'] < 85  # Updated threshold
    volatility_ok = latest['atr14'] > latest['close'] * 0.002  # Updated threshold
    price_ok = 10 <= latest['close'] <= 10000  # Updated to match strategy

    adx_ok = True
    if pd.notna(latest.get('adx14')):
        adx_ok = latest['adx14'] >= 15  # Further relaxed threshold

    macd_ok = True  # Temporarily disable MACD check to focus on other conditions
    # if pd.notna(latest.get('macd')) and pd.notna(latest.get('macd_signal')):
    #     macd_ok = latest['macd'] >= latest['macd_signal'] * 0.3  # Very permissive MACD

    volume_ok = True  # Temporarily disabled to match strategy changes
    # if pd.notna(latest.get('volume')) and len(df) > 20:
    #     avg_volume = df["volume"].rolling(20).mean().iloc[-1]
    #     volume_ok = latest['volume'] > avg_volume * 0.9  # Updated threshold

    print(f"  EMA Cross (20>50): {ema_cross}")
    print(f"  EMA Rising: {ema_rising}")
    print(f"  RSI < 85: {rsi_ok}")
    print(f"  Volatility OK: {volatility_ok}")
    print(f"  Price Range OK: {price_ok}")
    print(f"  ADX >= 15: {adx_ok}")
    print(f"  MACD OK: {macd_ok}")
    print(f"  Volume OK: {volume_ok}")

    # Check strong trend alternative
    strong_trend_ok = False
    if pd.notna(latest.get("adx14")) and latest["adx14"] >= 15:  # Weak trend strength
        ema_alignment = abs(latest["ema20"] - latest["ema50"]) / latest["ema50"] <= 0.05  # Within 5%
        strong_trend_ok = ema_alignment
    print(f"  Strong Trend (ADX>=15 + EMA aligned): {strong_trend_ok}")

    # Overall signal eligibility
    traditional_signal = ema_cross and ema_rising and rsi_ok and volatility_ok and price_ok and adx_ok and macd_ok and volume_ok
    strong_trend_signal = strong_trend_ok and rsi_ok and price_ok and macd_ok and volume_ok  # Match strategy engine
    overall_signal = traditional_signal or strong_trend_signal
    print(f"  Traditional Signal: {traditional_signal}")
    print(f"  Strong Trend Signal: {strong_trend_signal}")
    print(f"  Overall Eligible: {overall_signal}")

    # Test strategy signal generation
    print("\n🎲 Testing Strategy Signal Generation:")
    try:
        print("  Calling trend_follow()...")
        signal = trend_follow(df)
        print(f"  trend_follow() returned: {signal}")
        if signal:
            print(f"✅ Strategy generated signal: {signal.action} @ ₹{signal.entry:.2f}")

            # Test quality filter
            quality_pass = signal_quality_filter(signal, df)
            print(f"✅ Quality filter passed: {quality_pass}")

            if quality_pass:
                # Test confidence scoring
                confidence, rationale = score_signal(df, signal.action, signal.confidence, {'ticker': ticker, 'exchange': 'NSE'})
                print(f"✅ Confidence score: {confidence:.3f}")
                if confidence >= 0.6:
                    print(f"✅ Signal would be ACCEPTED!")
                else:
                    print(f"❌ Signal would be rejected (confidence < 0.6)")
            else:
                print("❌ Quality filter failed")
        else:
            print("❌ Strategy did not generate any signal")
    except Exception as e:
        print(f"❌ Strategy signal generation failed: {e}")
        import traceback
        traceback.print_exc()

    # Check if all requirements are met (new logic)
    traditional_requirements = ema_cross and ema_rising and rsi_ok and volatility_ok and price_ok and adx_ok and macd_ok and volume_ok
    strong_trend_requirements = strong_trend_ok and rsi_ok and price_ok and macd_ok and volume_ok  # Match strategy engine
    all_requirements = traditional_requirements or strong_trend_requirements

    print(f"\n🎯 Signal Requirements Analysis:")
    print(f"  Traditional Requirements Met: {traditional_requirements}")
    print(f"  Strong Trend Requirements Met: {strong_trend_requirements}")
    print(f"  Overall Signal Eligible: {all_requirements}")

    if not all_requirements:
        print("❌ NO SIGNAL ELIGIBLE - Analysis:")
        if not traditional_requirements and not strong_trend_requirements:
            missing_traditional = []
            missing_strong = []

            # Traditional missing
            if not ema_cross: missing_traditional.append("EMA Cross")
            if not ema_rising: missing_traditional.append("EMA Rising")
            if not rsi_ok: missing_traditional.append("RSI < 85")
            if not volatility_ok: missing_traditional.append("Volatility")
            if not price_ok: missing_traditional.append("Price Range")
            if not adx_ok: missing_traditional.append("ADX >= 15")
            if not macd_ok: missing_traditional.append("MACD")
            if not volume_ok: missing_traditional.append("Volume")

            # Strong trend missing
            if not strong_trend_ok: missing_strong.append("ADX >= 15 + EMA alignment")
            if not rsi_ok: missing_strong.append("RSI < 85")
            if not price_ok: missing_strong.append("Price Range")
            if not macd_ok: missing_strong.append("MACD")
            if not volume_ok: missing_strong.append("Volume")

            print(f"  Traditional path missing: {', '.join(missing_traditional)}")
            print(f"  Strong trend path missing: {', '.join(missing_strong)}")
    else:
        print("✅ SIGNAL SHOULD BE GENERATED!")
        if traditional_requirements:
            print("  Via: Traditional EMA crossover path")
        else:
            print("  Via: Strong trend path")

# Main debug
def main():
    print("🔧 DEBUGGING SIGNAL GENERATION FOR TATACOMM & DIVISLAB")

    debug_stock_signals('TATACOMM')
    debug_stock_signals('DIVISLAB')

if __name__ == "__main__":
    main()