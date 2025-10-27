#!/usr/bin/env python3
import os
import sys
from run_backtests import main

if __name__ == "__main__":
    # Set environment variables
    os.environ['SUPABASE_URL'] = 'https://lfwgposvyckptsrjkkyx.supabase.co'
    os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxmd2dwb3N2eWNrcHRzcmpra3l4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTg0MjI3MSwiZXhwIjoyMDY1NDE4MjcxfQ.7Pjsw_HpyE5RHHFshsRT3Ibpn1b6N4CO3F4rIw_GSvc'

    # Mock command line args for profitability test
    sys.argv = ['run_backtests.py', '--max-symbols', '225', '--start-date', '2025-10-17', '--end-date', '2025-10-20']

    print("🚀 TESTING OPTIMIZED PROFITABLE STRATEGY")
    print("Changes made:")
    print("- Risk-Reward: 4:1 (vs 2:1)")
    print("- Confidence threshold: 0.8 (vs 0.75)")
    print("- Trading costs: 0.005% commission + 1bps slippage")
    print("- Minimum profit filter: Expected profit > 3x costs")
    print()

    main()