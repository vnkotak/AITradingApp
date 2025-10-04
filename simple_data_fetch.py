import os
import time
from datetime import datetime, timezone
from supabase import create_client
from apps.api.yahoo_client import fetch_yahoo_candles

# Set up environment variables
os.environ['SUPABASE_URL'] = 'https://lfwgposvyckptsrjkkyx.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxmd2dwb3N2eWNrcHRzcmpra3l4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTg0MjI3MSwiZXhwIjoyMDY1NDE4MjcxfQ.7Pjsw_HpyE5RHHFshsRT3Ibpn1b6N4CO3F4rIw_GSvc'

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

def fetch_symbols_from_db():
    """Fetch all active symbols from database"""
    try:
        symbols = sb.table('symbols').select('ticker,exchange').eq('is_active', True).execute().data
        return [(symbol['ticker'], symbol['exchange']) for symbol in symbols]
    except Exception as e:
        print(f"❌ Error fetching symbols from database: {e}")
        return []

def get_symbol_id(ticker: str, exchange: str) -> str:
    """Get or create symbol ID"""
    try:
        symbol = sb.table('symbols').select('id').eq('ticker', ticker).eq('exchange', exchange).single().execute().data
        if symbol:
            return symbol['id']
    except:
        pass

    # Create new symbol
    new_symbol = sb.table('symbols').insert({
        'ticker': ticker,
        'exchange': exchange,
        'name': ticker,
        'is_active': True
    }).execute().data[0]
    return new_symbol['id']

def get_existing_data_info(symbol_id: str, timeframe: str) -> dict:
    """Get information about existing data for a symbol/timeframe"""
    try:
        # Get the most recent candle
        latest_candle = sb.table('candles').select('ts').eq('symbol_id', symbol_id).eq('timeframe', timeframe).order('ts', desc=True).limit(1).execute().data

        if not latest_candle:
            return {'exists': False, 'latest_date': None, 'days_count': 0}

        latest_date = latest_candle[0]['ts']

        # Get total count of candles using a simple select and len()
        all_candles = sb.table('candles').select('ts').eq('symbol_id', symbol_id).eq('timeframe', timeframe).execute().data

        return {
            'exists': True,
            'latest_date': latest_date,
            'days_count': len(all_candles) if all_candles else 0
        }
    except Exception as e:
        print(f"❌ Error checking existing data: {e}")
        return {'exists': False, 'latest_date': None, 'days_count': 0}

def calculate_delta_days(target_days: int, existing_info: dict) -> int:
    """Calculate how many additional days of data we need"""
    if not existing_info['exists']:
        # No existing data, fetch full target period
        return target_days

    # For now, we'll use a simple approach: if we have any data, skip fetching more
    # In a production system, you'd want more sophisticated logic here
    latest_date = existing_info['latest_date']

    # If the latest data is recent (within 1 day), we probably don't need more data
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Handle both string and datetime objects
    if isinstance(latest_date, str):
        # Parse ISO datetime string
        try:
            if latest_date.endswith('Z'):
                latest_date = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
            else:
                latest_date = datetime.fromisoformat(latest_date)
        except:
            print(f"  ⚠️ Could not parse date: {latest_date}")
            return 0

    if isinstance(latest_date, datetime):
        days_since_latest = (now - latest_date).days

        if days_since_latest <= 1:
            print(f"  📊 Data is up to date (latest: {latest_date.strftime('%Y-%m-%d %H:%M:%S')})")
            return 0

        # If data is older, fetch a smaller delta period
        delta_days = min(target_days // 4, max(1, days_since_latest // 2))  # Fetch 25% of target or half the gap
        print(f"  📊 Data is {days_since_latest} days old, fetching {delta_days} additional days")
        return delta_days

    return 0

def fetch_and_store(ticker: str, exchange: str, timeframe: str, target_days: int):
    """Fetch and store data for one symbol/timeframe with delta logic"""
    try:
        # Get symbol ID
        symbol_id = get_symbol_id(ticker, exchange)

        # Check existing data
        existing_info = get_existing_data_info(symbol_id, timeframe)

        # Calculate how many days we actually need to fetch
        delta_days = calculate_delta_days(target_days, existing_info)

        if delta_days == 0:
            print(f"\n📊 {ticker} {timeframe}: No new data needed")
            return 0

        print(f"\n📊 Fetching {ticker} {timeframe} ({delta_days} additional days)...")

        # Fetch from Yahoo
        candles = fetch_yahoo_candles(ticker, exchange, timeframe, delta_days)

        if not candles or len(candles) == 0:
            print(f"❌ No data for {ticker} {timeframe}")
            return 0

        print(f"✅ Got {len(candles)} candles from Yahoo")

        # Filter valid candles (exclude weekends and zero values)
        valid_candles = []
        for candle in candles:
            # Skip zero-value candles (weekends/holidays)
            if (candle.get('open', 0) <= 0 or
                candle.get('high', 0) <= 0 or
                candle.get('low', 0) <= 0 or
                candle.get('close', 0) <= 0):
                continue

            # Additional validation for volume
            volume = candle.get('volume', 0)
            if volume <= 0:
                continue

            valid_candles.append({
                'symbol_id': symbol_id,
                'timeframe': timeframe,
                'ts': candle['ts'],
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': volume
            })

        if valid_candles:
            # Store in database
            sb.table('candles').upsert(valid_candles, on_conflict='symbol_id,timeframe,ts').execute()
            print(f"💾 Stored {len(valid_candles)} candles")
            return len(valid_candles)
        else:
            print("⚠️ No valid candles to store")
            return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

def main():
    print("🚀 FETCHING INDIAN STOCK DATA (DELTA MODE)")
    print("Timeframes: 1m (7 days synthetic), 5m, 15m, 1h, 1d (real data)")

    # Fetch symbols from database
    STOCKS = fetch_symbols_from_db()

    if not STOCKS:
        print("❌ No active symbols found in database. Exiting.")
        return

    print(f"📊 Found {len(STOCKS)} active symbols in database")

    total_stored = 0
    total_processed = 0

    # Updated timeframes including 1m for swing trading
    target_timeframes = {
        '1m': 7,      # 7 days of 1m data for swing trading (synthetic)
        '5m': 30,     # 30 days of 5-minute data
        '15m': 30,    # 30 days of 15-minute data
        '1h': 365,    # 1 year of hourly data
        '1d': 365     # 1 year of daily data
    }

    for ticker, exchange in STOCKS:
        print(f"\n{'='*50}")
        print(f"📈 {ticker} ({exchange})")
        print(f"{'='*50}")

        for timeframe, target_days in target_timeframes.items():
            stored = fetch_and_store(ticker, exchange, timeframe, target_days)
            total_stored += stored
            total_processed += 1

            if stored > 0:
                time.sleep(1)  # Be nice to Yahoo API

    print(f"\n{'='*60}")
    print("🎉 DELTA DATA FETCH COMPLETE!")
    print(f"📊 Total candles stored: {total_stored}")
    print(f"📊 Total symbol/timeframe combinations processed: {total_processed}")

    # Show what's in the database
    print("\n📋 DATABASE SUMMARY:")

    # Refresh symbols from database in case new ones were added during execution
    current_STOCKS = fetch_symbols_from_db()

    for ticker, exchange in current_STOCKS:
        symbol_id = get_symbol_id(ticker, exchange)
        for timeframe in target_timeframes.keys():
            try:
                candles = sb.table('candles').select('*').eq('symbol_id', symbol_id).eq('timeframe', timeframe).limit(1).execute().data
                count = len(candles)
                if count > 0:
                    latest = sb.table('candles').select('ts,close').eq('symbol_id', symbol_id).eq('timeframe', timeframe).order('ts', desc=True).limit(1).execute().data
                    if latest:
                        print(f"  {ticker} {timeframe}: {count} candles (₹{latest[0]['close']:.0f})")
                    else:
                        print(f"  {ticker} {timeframe}: {count} candles")
                else:
                    print(f"  {ticker} {timeframe}: 0 candles")
            except Exception as e:
                print(f"  {ticker} {timeframe}: Error - {str(e)[:50]}")

if __name__ == "__main__":
    main()