#!/usr/bin/env python3
"""
Test script to verify market hours logic for GitHub Actions workflows
"""

from datetime import datetime, timezone, timedelta
import sys

def test_market_hours_logic():
    """Test the market hours logic that runs in GitHub Actions"""

    # Test different scenarios
    test_cases = [
        # (utc_hour, utc_min, day_of_week, expected_result, description)
        (1, 0, 1, False, "Before market opens (Monday 1:00 UTC = 6:30 IST)"),
        (3, 45, 1, True, "Market opens (Monday 3:45 UTC = 9:15 IST)"),
        (3, 30, 1, False, "Before market opens (Monday 3:30 UTC = 9:00 IST)"),
        (9, 59, 1, True, "Within market hours (Monday 9:59 UTC = 3:29 PM IST)"),
        (10, 0, 1, True, "Market close (Monday 10:00 UTC = 3:30 PM IST)"),
        (10, 1, 1, False, "After market close (Monday 10:01 UTC = 3:31 PM IST)"),
        (15, 0, 1, False, "Afternoon outside market (Monday 15:00 UTC = 8:30 PM IST)"),
        (3, 45, 6, False, "Weekend market time (Saturday 3:45 UTC)"),
        (3, 45, 7, False, "Weekend market time (Sunday 3:45 UTC)"),
    ]

    print("🧪 TESTING MARKET HOURS LOGIC")
    print("=" * 60)

    passed = 0
    total = len(test_cases)

    for utc_hour, utc_min, day_of_week, expected, description in test_cases:
        # Simulate the logic from GitHub Actions
        IST_HOUR = (utc_hour + 5) % 24
        IST_MIN = utc_min + 30

        # Handle minute overflow
        if IST_MIN >= 60:
            IST_MIN -= 60
            IST_HOUR = (IST_HOUR + 1) % 24

        # Market hours check (same logic as workflows)
        is_weekday = 1 <= day_of_week <= 5
        is_market_hours = False

        if is_weekday:
            if IST_HOUR > 9 and IST_HOUR < 15:
                is_market_hours = True
            elif IST_HOUR == 9 and IST_MIN >= 15:
                is_market_hours = True
            elif IST_HOUR == 15 and IST_MIN <= 30:
                is_market_hours = True

        # Check if result matches expected
        status = "✅ PASS" if is_market_hours == expected else "❌ FAIL"

        print(f"{status} {description}")
        print(f"      UTC: {utc_hour:02d}:{utc_min:02d}, Day: {day_of_week}, IST: {IST_HOUR:02d}:{IST_MIN:02d}")
        print(f"      Expected: {'Open' if expected else 'Closed'}, Got: {'Open' if is_market_hours else 'Closed'}")
        print()

        if is_market_hours == expected:
            passed += 1

    print("=" * 60)
    percentage = passed/total*100
    print(f"📊 TEST RESULTS: {passed}/{total} passed ({percentage:.1f}%)")

    if passed == total:
        print("🎉 All tests passed! Market hours logic is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the logic.")
        return False

if __name__ == "__main__":
    success = test_market_hours_logic()
    sys.exit(0 if success else 1)