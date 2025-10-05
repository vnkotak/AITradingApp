#!/usr/bin/env python3
"""
Automated Paper Trading Execution Script

This script monitors generated signals and automatically executes paper trades
based on high-confidence signals during market hours.

Usage:
    python apps/api/auto_execute_signals.py --confidence 0.7 --tf 1m

Or as a module:
    from apps.api.auto_execute_signals import run_auto_execution
    run_auto_execution(confidence_threshold=0.7, timeframe='1m')
"""

import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import pytz

from apps.api.supabase_client import get_client
from apps.api.execution import simulate_order, apply_trade_updates
from apps.api.risk_engine import get_limits, suggest_position_size, should_block_order
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoExecutor:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.sb = get_client()

    def is_market_open(self) -> bool:
        """Check if Indian markets are currently open"""
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)

        # Market hours: 9:15 AM - 3:30 PM IST, Monday-Friday
        market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)

        # Check weekday
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        return market_open_time <= now <= market_close_time

    def get_recent_signals(self, timeframe: str, confidence_threshold: float, hours_back: int = 2) -> List[Dict]:
        """Fetch recent high-confidence signals"""
        if not self.sb:
            logger.error("Database connection not available")
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        try:
            signals = self.sb.table("signals").select("""
                id, ts, strategy, action, entry, stop, target, confidence,
                symbol_id, timeframe
            """).eq("timeframe", timeframe).gte("confidence", confidence_threshold).gte("ts", cutoff_time.isoformat()).order("ts", desc=True).execute().data or []

            # Attach symbol information to each signal
            signals_with_symbols = []
            for signal in signals:
                if signal.get("symbol_id"):
                    try:
                        symbol_info = self.sb.table("symbols").select("ticker,exchange").eq("id", signal["symbol_id"]).single().execute().data
                        if symbol_info:
                            signal["ticker"] = symbol_info["ticker"]
                            signal["exchange"] = symbol_info["exchange"]
                            signals_with_symbols.append(signal)
                    except Exception as e:
                        logger.warning(f"Failed to get symbol info for {signal['symbol_id']}: {e}")
                        continue

            logger.info(f"Found {len(signals_with_symbols)} signals above {confidence_threshold} confidence in last {hours_back} hours")
            return signals_with_symbols

        except Exception as e:
            logger.error(f"Error fetching signals: {e}")
            return []

    def get_current_position(self, symbol_id: str) -> Optional[Dict]:
        """Get current position for a symbol"""
        try:
            positions = self.sb.table("positions").select("*").eq("symbol_id", symbol_id).execute().data
            return positions[0] if positions else None
        except Exception as e:
            logger.error(f"Error fetching position for symbol {symbol_id}: {e}")
            return None

    def has_recent_order(self, symbol_id: str, action: str, minutes_back: int = 10) -> bool:
        """Check if there's already a recent order for this symbol and action"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_back)
            recent_orders = self.sb.table("orders").select("id, ts, side").eq("symbol_id", symbol_id).eq("side", action).gte("ts", cutoff_time.isoformat()).execute().data or []
            return len(recent_orders) > 0
        except Exception as e:
            logger.error(f"Error checking recent orders for {symbol_id}: {e}")
            return False

    def execute_signal(self, signal: Dict) -> bool:
        """Execute a trading signal (paper trading)"""
        symbol_id = signal['symbol_id']
        ticker = signal['ticker']
        exchange = signal['exchange']
        action = signal['action']
        entry_price = signal['entry']

        # Check if we already executed this signal recently
        if self.has_recent_order(symbol_id, action, minutes_back=10):
            logger.info(f"Signal {signal['id']} for {ticker} {action} already processed recently, skipping")
            return False

        # Check risk controls
        blocked, reason = should_block_order(ticker, exchange, action)
        if blocked:
            logger.warning(f"Order blocked for {ticker}: {reason}")
            return False

        # Get current position
        position = self.get_current_position(symbol_id)

        # Logic for execution
        should_execute = False
        order_side = action
        order_qty = 0

        if action == 'BUY':
            # Buy if no position or short position
            if not position or position['qty'] <= 0:
                # Calculate position size
                limits = get_limits()
                available_capital = limits.get('max_position_value', 10000)  # Default 10k
                if position and position['qty'] < 0:
                    # Covering short - size based on existing short
                    order_qty = abs(position['qty'])
                else:
                    # New long position
                    order_qty = suggest_position_size(ticker, exchange, entry_price)

                if order_qty > 0:
                    should_execute = True
                    order_side = 'BUY'
                else:
                    logger.info(f"No quantity calculated for BUY {ticker}")
            else:
                logger.info(f"Already have long position in {ticker}, skipping BUY signal")

        elif action == 'SELL':
            # Sell if have long position
            if position and position['qty'] > 0:
                order_qty = position['qty']  # Close entire position
                should_execute = True
                order_side = 'SELL'
            else:
                logger.info(f"No long position in {ticker}, skipping SELL signal")

        if should_execute and order_qty > 0:
            try:
                # Place order using existing API
                order_payload = {
                    "ticker": ticker,
                    "exchange": exchange,
                    "side": order_side,
                    "type": "LIMIT",  # Use limit orders for signals
                    "price": entry_price,
                    "qty": order_qty
                }

                # Call the orders API
                response = requests.post(f"{self.api_base_url}/orders", json=order_payload)
                response.raise_for_status()

                order_result = response.json()
                logger.info(f"✅ Executed {order_side} order for {order_qty} {ticker} at {entry_price}: {order_result}")

                return True

            except Exception as e:
                logger.error(f"❌ Failed to execute {order_side} order for {ticker}: {e}")
                return False
        else:
            logger.debug(f"Skipping signal execution for {ticker} {action}")
            return False

    def run_execution_cycle(self, timeframe: str, confidence_threshold: float = 0.7, dry_run: bool = False, minutes_back: int = 15):
        """Run one execution cycle"""
        logger.info(f"Starting auto-execution cycle for {timeframe} timeframe (confidence >= {confidence_threshold})")
        logger.info(dry_run);
        if dry_run:
            logger.info("DRY RUN MODE - No orders will be placed - bypassing time filters for testing")

        if not (dry_run or self.is_market_open()):
            logger.info("Market is closed, skipping execution")
            return {"executed": 0, "skipped": 0, "errors": 0}

        # Get recent signals (15 minutes by default, or longer for dry runs)
        hours_back = minutes_back/60.0 if not dry_run else 24.0  # 24 hours for dry run testing
        signals = self.get_recent_signals(timeframe, confidence_threshold, hours_back=hours_back)
        logger.info(signals);
        executed = 0
        skipped = 0
        errors = 0

        for signal in signals:
            try:
                if dry_run:
                    logger.info(f"DRY RUN: Would execute {signal['action']} {signal['ticker']} at {signal['entry']} (conf: {signal['confidence']:.2f})")
                    executed += 1
                else:
                    if self.execute_signal(signal):
                        executed += 1
                    else:
                        skipped += 1
            except Exception as e:
                logger.error(f"Error processing signal {signal['id']}: {e}")
                errors += 1

        logger.info(f"Execution cycle complete: {executed} executed, {skipped} skipped, {errors} errors")
        return {
            "executed": executed,
            "skipped": skipped,
            "errors": errors,
            "signals_processed": len(signals)
        }

def main():
    parser = argparse.ArgumentParser(description='Auto-execute trading signals for paper trading')
    parser.add_argument('--tf', '--timeframe', default='1m',
                       help='Timeframe(s) to process signals for (comma-separated)')
    parser.add_argument('--confidence', type=float, default=0.7,
                       help='Minimum confidence threshold (0.0-1.0)')
    parser.add_argument('--api-url', default='http://localhost:8000',
                       help='API base URL')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in dry-run mode (no orders placed)')
    parser.add_argument('--hours-back', type=int, default=2,
                       help='Hours back to look for signals')

    args = parser.parse_args()

    executor = AutoExecutor(api_base_url=args.api_url)

    # Handle multiple timeframes
    tf_list = [tf.strip() for tf in args.tf.split(',')]

    if len(tf_list) == 1:
        # Single timeframe - return result directly
        result = executor.run_execution_cycle(
            timeframe=tf_list[0],
            confidence_threshold=args.confidence,
            dry_run=args.dry_run
        )
        print(f"Results: {result}")
    else:
        # Multiple timeframes - aggregate results
        results = {}
        for tf in tf_list:
            logger.info(f"Processing timeframe: {tf}")
            result = executor.run_execution_cycle(
                timeframe=tf,
                confidence_threshold=args.confidence,
                dry_run=args.dry_run
            )
            results[tf] = result

        summary = {
            "timeframes_processed": tf_list,
            "results": results,
            "summary": {
                "total_executed": sum(r.get("executed", 0) for r in results.values()),
                "total_skipped": sum(r.get("skipped", 0) for r in results.values()),
                "total_errors": sum(r.get("errors", 0) for r in results.values())
            }
        }
        print(f"Multi-timeframe Results: {summary}")

if __name__ == "__main__":
    main()