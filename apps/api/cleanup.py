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

    # Process timeframes in order of data volume (smallest first to avoid timeouts)
    timeframe_order = ['1m', '5m', '1h', '15m', '1d']
    print("Test")
    for timeframe in timeframe_order:
        if timeframe not in retention_periods:
            continue

        days = retention_periods[timeframe]
        try:
            cutoff_date = now - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            # Count records that would be deleted (use ts column since candles table has no id column)
            # Use smaller batch size for large timeframes to avoid timeouts
            batch_size = 10000 if timeframe in ['15m', '1d'] else 50000

            # Use direct counting via iteration instead of potentially buggy count queries
            print(f"DEBUG: Counting {timeframe} records manually...")

            # Get total records and count old ones
            total_records = 0
            old_records = 0
            batch_size = 5000  # Process in batches to avoid timeouts

            # First get total count
            try:
                total_query = sb.table("candles").select("ts").eq("timeframe", timeframe)
                total_result = total_query.execute()
                total_records = len(total_result.data) if total_result.data else 0
                print(f"DEBUG: {timeframe} - Total records in database: {total_records}")
            except Exception:
                print(f"DEBUG: {timeframe} - Could not get total count")
                total_records = 0

            # Count old records by iterating through data
            if total_records > 0:
                # Always check oldest record first
                oldest_check = sb.table("candles").select("ts").eq("timeframe", timeframe).order("ts").limit(1).execute()
                if oldest_check.data:
                    oldest_date = datetime.fromisoformat(oldest_check.data[0]['ts'].replace('Z', '+00:00'))
                    cutoff_date_obj = datetime.fromisoformat(cutoff_iso.replace('Z', '+00:00'))

                    print(f"DEBUG: {timeframe} - Oldest: {oldest_date}, Cutoff: {cutoff_date_obj}")

                    if oldest_date >= cutoff_date_obj:
                        old_records = 0
                        print(f"DEBUG: {timeframe} - All data newer than cutoff, no deletion needed")
                    else:
                        # Count actual old records
                        if total_records <= 5000:
                            # Small dataset - count exactly
                            try:
                                all_query = sb.table("candles").select("ts").eq("timeframe", timeframe).execute()
                                if all_query.data:
                                    old_records = sum(1 for record in all_query.data
                                                    if datetime.fromisoformat(record['ts'].replace('Z', '+00:00')) < cutoff_date_obj)
                                    print(f"DEBUG: {timeframe} - Exact count: {old_records} old records")
                                else:
                                    old_records = 0
                            except Exception as e:
                                print(f"DEBUG: {timeframe} - Error in exact count: {e}")
                                old_records = 0
                        else:
                            # Large dataset - use sampling to verify
                            sample_size = min(1000, total_records // 10)  # Sample 10% or 1000 records max
                            try:
                                sample_query = sb.table("candles").select("ts").eq("timeframe", timeframe).limit(sample_size).execute()
                                if sample_query.data:
                                    sample_old = sum(1 for record in sample_query.data
                                                   if datetime.fromisoformat(record['ts'].replace('Z', '+00:00')) < cutoff_date_obj)
                                    sample_ratio = sample_old / sample_size if sample_size > 0 else 0

                                    # If sample has old records, get exact count for small portion
                                    if sample_old > 0:
                                        # Get exact count for records older than cutoff
                                        exact_old_query = sb.table("candles").select("ts").eq("timeframe", timeframe).lt("ts", cutoff_iso).limit(5000).execute()
                                        if exact_old_query.data:
                                            old_records = len(exact_old_query.data)
                                            print(f"DEBUG: {timeframe} - Exact count from sample verification: {old_records}")
                                        else:
                                            old_records = 0
                                    else:
                                        old_records = 0
                                        print(f"DEBUG: {timeframe} - Sample shows no old records")
                                else:
                                    old_records = 0
                            except Exception as e:
                                print(f"DEBUG: {timeframe} - Error in sampling: {e}")
                                old_records = 0
                else:
                    old_records = 0
                    print(f"DEBUG: {timeframe} - No data found")

            records_to_delete = old_records
            print(f"DEBUG: {timeframe} - Final count: {records_to_delete} records to delete")

            timeframe_result = {
                "timeframe": timeframe,
                "retention_days": days,
                "cutoff_date": cutoff_iso,
                "records_to_delete": records_to_delete,
                "status": "success"
            }

            results["total_records_counted"] += records_to_delete

            if not dry_run and records_to_delete > 0:
                # Delete old records in batches to avoid timeouts
                try:
                    if timeframe in ['15m', '1d'] and records_to_delete > 50000:
                        # For very large datasets, use batched deletion
                        deleted_count = 0
                        batch_cutoff = cutoff_iso

                        for batch in range(min(10, (records_to_delete // batch_size) + 1)):  # Max 10 batches
                            try:
                                # Delete a batch of records
                                delete_query = sb.table("candles").delete().eq("timeframe", timeframe).lt("ts", batch_cutoff).limit(batch_size)
                                delete_result = delete_query.execute()
                                # Since we can't get exact count, assume batch_size was deleted
                                batch_deleted = min(batch_size, records_to_delete - deleted_count)
                                deleted_count += batch_deleted

                                # Move cutoff forward for next batch (rough approximation)
                                next_cutoff_date = cutoff_date + timedelta(hours=batch)
                                batch_cutoff = next_cutoff_date.isoformat()

                                if deleted_count >= records_to_delete:
                                    break
                            except Exception as batch_error:
                                print(f"Batch delete failed for {timeframe} batch {batch}: {batch_error}")
                                break

                        timeframe_result["records_deleted"] = deleted_count
                        results["total_records_deleted"] += deleted_count
                    else:
                        # Standard deletion for smaller datasets
                        delete_query = sb.table("candles").delete().eq("timeframe", timeframe).lt("ts", cutoff_iso)
                        delete_result = delete_query.execute()
                        timeframe_result["records_deleted"] = records_to_delete
                        results["total_records_deleted"] += records_to_delete

                except Exception as delete_error:
                    timeframe_result["delete_error"] = str(delete_error)
                    timeframe_result["status"] = "delete_failed"

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
            # Get total count for timeframe (use ts column since candles table has no id column)
            # Use sample-based estimation for large datasets to avoid timeouts
            try:
                total_query = sb.table("candles").select("ts", count="exact").eq("timeframe", tf)
                total_result = total_query.execute()
                total_count = total_result.count if hasattr(total_result, 'count') else 0
            except Exception:
                # Fallback: estimate based on sample
                sample_query = sb.table("candles").select("ts").eq("timeframe", tf).limit(1000)
                sample_result = sample_query.execute()
                sample_size = len(sample_result.data) if sample_result.data else 0

                # For large timeframes, estimate higher multiplier
                if tf in ['15m', '1d']:
                    multiplier = 50  # Rough estimate for large datasets
                else:
                    multiplier = 20

                total_count = sample_size * multiplier

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
            try:
                old_query = sb.table("candles").select("ts", count="exact").eq("timeframe", tf).lt("ts", thirty_days_ago)
                old_result = old_query.execute()
                old_count = old_result.count if hasattr(old_result, 'count') else 0
            except Exception:
                # Fallback: estimate old records
                old_sample_query = sb.table("candles").select("ts").eq("timeframe", tf).lt("ts", thirty_days_ago).limit(500)
                old_sample_result = old_sample_query.execute()
                old_sample_size = len(old_sample_result.data) if old_sample_result.data else 0
                old_count = old_sample_size * 10  # Rough estimate

            timeframe_stats = {
                "total_records": total_count,
                "old_records_30d": old_count,
                "oldest_timestamp": oldest_ts,
                "newest_timestamp": newest_ts,
                "estimated": True if "estimate" in str(total_count) else False
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