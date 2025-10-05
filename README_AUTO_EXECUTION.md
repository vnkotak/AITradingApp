# Automated Paper Trading Execution

This document describes the automated paper trading execution system that automatically executes trades based on AI-generated signals.

## Overview

The system consists of:
1. **Signal Generation** - AI models scan markets and generate trading signals
2. **Automated Execution** - High-confidence signals are automatically converted to paper trades
3. **Risk Management** - Position sizing, stop-losses, and risk controls are applied

## Architecture

### Files
- `apps/api/auto_execute_signals.py` - Main execution script
- `apps/api/routes.py` - API endpoint for manual triggering
- `.github/workflows/execute_paper_trades.yml` - Scheduled automation

### Components

#### AutoExecutor Class
- `is_market_open()` - Checks Indian market hours (9:15 AM - 3:30 PM IST)
- `get_recent_signals()` - Fetches high-confidence signals from database
- `get_current_position()` - Checks existing positions
- `execute_signal()` - Places simulated orders
- `run_execution_cycle()` - Main execution loop

## Usage

### Manual Execution
```bash
# Dry run for specific timeframe (no orders placed)
python apps/api/auto_execute_signals.py --tf 1m --confidence 0.7 --dry-run

# Live execution for specific timeframe
python apps/api/auto_execute_signals.py --tf 1m --confidence 0.7

# Run for multiple timeframes
python apps/api/auto_execute_signals.py --tf 1m,5m,15m --confidence 0.7 --dry-run
```

### API Endpoint
```bash
# POST /auto-execute/run - Single timeframe
curl -X POST "http://localhost:8000/auto-execute/run?timeframes=1m&confidence_threshold=0.7&dry_run=true"

# POST /auto-execute/run - Multiple timeframes
curl -X POST "http://localhost:8000/auto-execute/run?timeframes=1m,5m,15m&confidence_threshold=0.7&dry_run=true"
```

### GitHub Actions
The `execute_paper_trades.yml` workflow runs automatically:
- Every 5 minutes during market hours (9:15 AM - 3:30 PM IST)
- Monday-Friday
- Can be triggered manually with custom parameters

## Execution Logic

### Signal Processing
1. Fetches signals with confidence > threshold for specified timeframe(s)
   - Normal mode: signals from last 15 minutes
   - Dry run mode: signals from last 24 hours (for testing)
2. Supports multiple timeframes: 1m, 5m, 15m, 1h, 1d
3. Checks for recent orders to prevent duplicate execution
4. Checks current positions for each symbol

### Trade Execution Rules
- **BUY Signal**: Execute if no position exists or currently short
- **SELL Signal**: Execute if long position exists
- Uses limit orders at signal entry price
- Applies position sizing based on risk management

### Risk Controls
- Respects existing risk limits (`get_limits()`)
- Uses position sizing algorithm (`suggest_position_size()`)
- Checks order blocking conditions (`should_block_order()`)
- Simulated slippage and market impact

## Configuration

### Environment Variables
- `SUPABASE_URL` - Database connection
- `SUPABASE_SERVICE_KEY` - Database authentication

### Parameters
- `timeframe`: Signal timeframe to process ('1m', '5m', '15m', etc.)
- `confidence_threshold`: Minimum signal confidence (0.0-1.0)
- `hours_back`: How far back to look for signals (default: 2)
- `dry_run`: Test mode without placing orders

## Monitoring

### Logs
The system logs all execution attempts:
```
INFO - Starting auto-execution cycle for 1m timeframe (confidence >= 0.7)
INFO - Found 5 signals above 0.7 confidence in last 2 hours
INFO - ✅ Executed BUY order for 10 RELIANCE at 2450.0 (conf: 0.85)
```

### Database Tables
- `signals` - Generated trading signals
- `orders` - Executed paper orders
- `positions` - Current simulated positions

## Safety Features

1. **Market Hours Check** - Only executes during Indian market hours
2. **Dry Run Mode** - Test execution without placing orders, bypasses time filters
3. **Risk Limits** - Respects position size and capital limits
4. **Order-Based Deduplication** - Checks recent orders to prevent re-processing signals
5. **Position Validation** - Only executes if position logic allows (no conflicting trades)
6. **Error Handling** - Comprehensive logging and error recovery

## Testing

### Dry Run Testing
```bash
# Test with current signals without executing
python apps/api/auto_execute_signals.py --dry-run
```

### Manual API Testing
```bash
# Test API endpoint
curl -X POST "http://localhost:8000/auto-execute/run?dry_run=true"
```

### Integration Testing
1. Generate signals using scanner
2. Run auto-execution in dry-run mode
3. Verify position updates in database
4. Check order history

## Deployment

### Local Development
```bash
# Install dependencies
pip install -r apps/api/requirements.txt

# Run API server
uvicorn apps.api.main:app --reload --port 8000

# Test execution
python apps/api/auto_execute_signals.py --dry-run
```

### Production
- Deploy API to cloud (Render, Railway, etc.)
- Set up GitHub Actions for scheduled execution
- Configure environment variables
- Monitor logs and execution results

## Future Enhancements

1. **Real Broker Integration** - Connect to live trading APIs
2. **Advanced Risk Management** - Portfolio-level risk controls
3. **Strategy-specific Logic** - Different execution rules per strategy
4. **Performance Analytics** - Track execution success rates
5. **Multi-timeframe Execution** - Execute across multiple timeframes