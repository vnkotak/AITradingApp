#!/usr/bin/env python3
"""
Candle Data Cleanup API Endpoint

Provides automated cleanup of old candle data from Supabase database.
Retention periods by timeframe to balance data needs with storage costs.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List
from fastapi import HTTPException

from apps.api.supabase_client import get_client


def cleanup_candle_data(dry_run: bool = False) -> Dict:
    """
    Clean up old candle data based on timeframe retention policies.

    Args:
        dry_run: If True, only count records without deleting

    Returns:
        Dict containing cleanup statistics
    """
    sb = get_client()
    if not sb:
        raise HTTPException(status_code=500, detail="Database connection failed")

    now = datetime.now(timezone.utc)

    # Define retention periods (in days) based on timeframe frequency
    retention_periods = {
        '1m': 5,      # 5 days - high frequency, short-term relevance
        '5m': 10,     # 10 days - medium frequency, moderate relevance
        '15m': 15,    # 15 days - lower frequency, longer relevance
        '1h': 30,     # 30 days - hourly data, good for trend analysis
        '1d': 90      # 90 days - daily data, long-term context
    }

    results = {
        "cleanup_timestamp": now.isoformat(),
        "retention_policies": retention_periods,
        "timeframes_processed": [],
        "total_records_deleted": 0,
        "total_records_counted": 0,
        "dry_run": dry_run,
        "errors": []
    }

    for timeframe, days in retention_periods.items():
        try:
            cutoff_date = now - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            # Count records that would be deleted
            count_query = sb.table("candles").select("id", count="exact").eq("timeframe", timeframe).lt("ts", cutoff_iso)
            count_result = count_query.execute()
            records_to_delete = count_result.count if hasattr(count_result, 'count') else 0

            timeframe_result = {
                "timeframe": timeframe,
                "retention_days": days,
                "cutoff_date": cutoff_iso,
                "records_to_delete": records_to_delete,
                "status": "success"
            }

            results["total_records_counted"] += records_to_delete

            if not dry_run and records_to_delete > 0:
                # Delete old records
                delete_query = sb.table("candles").delete().eq("timeframe", timeframe).lt("ts", cutoff_iso)
                delete_result = delete_query.execute()

                # Note: Supabase delete doesn't return count, so we use our pre-count
                timeframe_result["records_deleted"] = records_to_delete
                results["total_records_deleted"] += records_to_delete

            results["timeframes_processed"].append(timeframe_result)

        except Exception as e:
            error_info = {
                "timeframe": timeframe,
                "error": str(e),
                "status": "failed"
            }
            results["errors"].append(error_info)
            results["timeframes_processed"].append(error_info)

    return results


def get_cleanup_stats() -> Dict:
    """
    Get statistics about current candle data in the database.

    Returns:
        Dict with data counts by timeframe and age analysis
    """
    sb = get_client()
    if not sb:
        raise HTTPException(status_code=500, detail="Database connection failed")

    now = datetime.now(timezone.utc)
    stats = {
        "timestamp": now.isoformat(),
        "timeframes": {},
        "total_records": 0,
        "oldest_record": None,
        "newest_record": None
    }

    timeframes = ['1m', '5m', '15m', '1h', '1d']

    for tf in timeframes:
        try:
            # Get total count for timeframe
            total_query = sb.table("candles").select("id", count="exact").eq("timeframe", tf)
            total_result = total_query.execute()
            total_count = total_result.count if hasattr(total_result, 'count') else 0

            # Get oldest record
            oldest_query = sb.table("candles").select("ts").eq("timeframe", tf).order("ts").limit(1)
            oldest_result = oldest_query.execute()
            oldest_ts = oldest_result.data[0]['ts'] if oldest_result.data else None

            # Get newest record
            newest_query = sb.table("candles").select("ts").eq("timeframe", tf).order("ts", desc=True).limit(1)
            newest_result = newest_query.execute()
            newest_ts = newest_result.data[0]['ts'] if newest_result.data else None

            # Count old records (>30 days for all timeframes as benchmark)
            thirty_days_ago = (now - timedelta(days=30)).isoformat()
            old_query = sb.table("candles").select("id", count="exact").eq("timeframe", tf).lt("ts", thirty_days_ago)
            old_result = old_query.execute()
            old_count = old_result.count if hasattr(old_result, 'count') else 0

            timeframe_stats = {
                "total_records": total_count,
                "old_records_30d": old_count,
                "oldest_timestamp": oldest_ts,
                "newest_timestamp": newest_ts
            }

            stats["timeframes"][tf] = timeframe_stats
            stats["total_records"] += total_count

            # Update global oldest/newest
            if oldest_ts and (not stats["oldest_record"] or oldest_ts < stats["oldest_record"]):
                stats["oldest_record"] = oldest_ts
            if newest_ts and (not stats["newest_record"] or newest_ts > stats["newest_record"]):
                stats["newest_record"] = newest_ts

        except Exception as e:
            stats["timeframes"][tf] = {"error": str(e)}

    return stats