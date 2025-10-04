import os
from supabase import create_client

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://lfwgposvyckptsrjkkyx.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxmd2dwb3N2eWNrcHRzcmpra3l4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTg0MjI3MSwiZXhwIjoyMDY1NDE4MjcxfQ.7Pjsw_HpyE5RHHFshsRT3Ibpn1b6N4CO3F4rIw_GSvc'

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_SERVICE_KEY')
sb = create_client(url, key)

print("=== DATABASE STATUS CHECK ===")

# Check symbols
symbols = sb.table('symbols').select('id,ticker,exchange,is_active').execute().data
print(f"Symbols in database: {len(symbols) if symbols else 0}")

if symbols:
    print("Sample symbols:")
    for s in symbols[:5]:
        print(f"  {s['ticker']} ({s['exchange']}) - Active: {s['is_active']}")
else:
    print("❌ No symbols found - need to add stocks first!")

# Check candles
candles = sb.table('candles').select('symbol_id,timeframe,ts').limit(5).execute().data
print(f"\nCandles in database: {len(candles) if candles else 0}")

if candles:
    print("Sample candles:")
    for c in candles[:3]:
        print(f"  Symbol ID: {c['symbol_id']}, TF: {c['timeframe']}, TS: {c['ts']}")
else:
    print("❌ No candle data found - need historical price data!")

# Check recent signals
signals = sb.table('signals').select('id,strategy,action,confidence,ts').limit(5).execute().data
print(f"\nSignals in database: {len(signals) if signals else 0}")

if signals:
    print("Sample signals:")
    for s in signals[:3]:
        print(f"  {s['strategy']} {s['action']} (conf: {s['confidence']}) - {s['ts']}")
else:
    print("❌ No signals found - strategy hasn't generated any signals!")

print("\n=== CONCLUSION ===")
if not symbols:
    print("Need to add symbols to database first")
elif not candles:
    print("Need to fetch historical price data for symbols")
else:
    print("Database has data - strategy should be able to generate signals")