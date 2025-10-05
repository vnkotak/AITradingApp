#!/usr/bin/env python3
"""
Test script for single backtest combination
"""
import sys
sys.path.append('../ml')
from execute_backtest_trades import execute_backtest_trades

if __name__ == "__main__":
    # Test with just one symbol, one strategy, one timeframe
    print("🧪 Testing single backtest combination...")

    # Modify the function to run just one combination for testing
    # We'll temporarily modify it to run only RELIANCE with trend_follow on 5m
    execute_backtest_trades(
        start_date="2025-10-01",
        end_date="2025-10-04"
    )