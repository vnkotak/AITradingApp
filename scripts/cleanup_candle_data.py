#!/usr/bin/env python3
"""
Candle Data Cleanup Script

Deletes old candle data from Supabase to manage database size and costs.
Retention periods:
- 1m timeframe: 5 days
- 5m timeframe: 10 days
- 15m timeframe: 15 days
- 1h timeframe: 30 days
- 1d timeframe: 90 days
"""

import os
from datetime import datetime, timezone, timedelta
from supabase import create_client

def get_supabase_client():
    """Initialize Supabase client"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")

    return create_client(url, key)

def cleanup_candle_data():
    """Clean up old candle data based on timeframe retention policies"""
    sb = get_supabase_client()
    now = datetime.now(timezone.utc)

    # Define retention periods (in days)
    retention_periods = {
        '1m': 5,      # 5 days for 1-minute data
        '5m': 10,     # 10 days for 5-minute data
        '15m': 15,    # 15 days for 15-minute data
        '1h': 30,     # 30 days for 1-hour data
        '1d': 90      # 90 days for daily data
    }

    total_deleted = 0

    print("🧹 Starting candle data cleanup...")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    for timeframe, days in retention_periods.items():
        cutoff_date = now - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        try:
            # Count records to be deleted
            count_result = sb.table("candles").select("id", count="exact").eq("timeframe", timeframe).lt("ts", cutoff_iso).execute()
            records_to_delete = count_result.count if hasattr(count_result, 'count') else 0

            if records_to_delete > 0:
                # Delete old records
                delete_result = sb.table("candles").delete().eq("timeframe", timeframe).lt("ts", cutoff_iso).execute()

                print(f"✅ Deleted {records_to_delete} records for {timeframe} timeframe (older than {days} days)")
                total_deleted += records_to_delete
            else:
                print(f"ℹ️ No old records to delete for {timeframe} timeframe")

        except Exception as e:
            print(f"❌ Error cleaning up {timeframe} data: {e}")
            continue

    print("
🎯 CLEANUP SUMMARY:"    print(f"  Total records deleted: {total_deleted}")
    print(f"  Database size optimized for better performance")
    print("  Next cleanup: Tomorrow at 2 AM IST")

if __name__ == "__main__":
    try:
        cleanup_candle_data()
        print("\n✅ Cleanup completed successfully!")
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        exit(1)