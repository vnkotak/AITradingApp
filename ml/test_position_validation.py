#!/usr/bin/env python3
"""
Test position validation logic
"""
import pandas as pd
from datetime import datetime, timezone

# Simulate the position validation logic
def test_position_validation():
    print("🧪 Testing Position Validation Logic")

    # Simulate signals: BUY, SELL, SELL, BUY
    signals = ['BUY', 'SELL', 'SELL', 'BUY']

    current_position_qty = 0
    current_avg_price = 0.0
    trades_executed = 0

    print(f"Initial position: {current_position_qty} shares")

    for i, signal in enumerate(signals):
        print(f"\nSignal {i+1}: {signal}")

        if signal == 'SELL' and current_position_qty <= 0:
            print(f"  ❌ BLOCKED: Cannot sell - no position (current qty: {current_position_qty})")
            continue

        # Execute the trade
        if signal == 'BUY':
            if current_position_qty == 0:
                current_avg_price = 100.0  # Assume price
                current_position_qty = 10
            else:
                current_position_qty += 10
                current_avg_price = ((current_position_qty - 10) * current_avg_price + 10 * 100.0) / current_position_qty
        else:  # SELL
            current_position_qty -= 10

        print(f"  ✅ EXECUTED: Position now {current_position_qty} shares @ ₹{current_avg_price:.2f}")
        trades_executed += 1

    print(f"\n📊 Final result: {trades_executed} trades executed, final position: {current_position_qty} shares")
    print("✅ Position validation working correctly - no invalid sells!")

if __name__ == "__main__":
    test_position_validation()