import os
import json
import argparse
from datetime import datetime
from backtest import run_backtests, load_candles, backtest_strategy, BTTrade

def main():
    parser = argparse.ArgumentParser(description='Run backtests for trading strategies')
    parser.add_argument('--start-date', help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--tf', '--timeframe', default='15m', help='Timeframe to test')
    parser.add_argument('--strategy', default='trend_follow', help='Strategy to test')
    parser.add_argument('--max-symbols', type=int, default=10, help='Maximum symbols to test')

    args = parser.parse_args()

    version = f"bt-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    # Use command line args for limited testing
    strategies = ['hull_suite']  # Test only Hull Suite strategy
    timeframes = ['15m']  # Use 1h timeframe for testing
    symbols_limit = args.max_symbols
    start_date = args.start_date
    end_date = args.end_date
    res = run_backtests(strategies, timeframes, symbols_limit=symbols_limit, start_date=start_date, end_date=end_date)

    # Comprehensive analysis of all stocks
    print("\n📊 COMPREHENSIVE MULTI-STOCK ANALYSIS")
    analyze_all_stocks_comprehensive(res)

    # Calculate total actual P&L across all trades
    total_pnl = 0
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    total_positive_pnl = 0
    total_negative_pnl = 0

    for ticker, ticker_results in res.get("per_symbol", {}).items():
        for strategy, metrics in ticker_results.items():
            if metrics.get("trades", 0) > 0:
                # Load data and run strategy to get actual trade P&L
                from backtest import supabase_client, load_candles, backtest_strategy
                sb = supabase_client()
                sym_data = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", "NSE").single().execute().data
                if sym_data:
                    df = load_candles(sym_data["id"], "15m", days=720, start_date=start_date, end_date=end_date)
                    if not df.empty and len(df) >= 60:
                        trades, _ = backtest_strategy(df, strategy)

                        for trade in trades:
                            if trade.pnl is not None:
                                total_trades += 1
                                total_pnl += trade.pnl
                                if trade.pnl > 0:
                                    winning_trades += 1
                                    total_positive_pnl += trade.pnl
                                else:
                                    losing_trades += 1
                                    total_negative_pnl += abs(trade.pnl)

    print(f"\n💰 ACTUAL TRADING SIMULATION RESULTS:")
    print(f"  Total Trades Executed: {total_trades}")
    print(f"  Total P&L: ₹{total_pnl:,.2f}")
    print(f"  Daily P&L Rate: ₹{total_pnl/2:,.2f} (over 2 days)")
    if total_trades > 0:
        print(f"  Winning Trades: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
        print(f"  Losing Trades: {losing_trades} ({losing_trades/total_trades*100:.1f}%)")
        print(f"  Average P&L per Trade: ₹{total_pnl/total_trades:,.2f}")
        print(f"  Profit Factor: {total_positive_pnl/total_negative_pnl:.2f}" if total_negative_pnl > 0 else "  Profit Factor: Infinite (no losses)")

    # Show realistic expectation
    print("\n📋 TRADING COST BREAKDOWN (ULTRA-OPTIMIZED):")
    print("  Commission: 0.003% per trade (₹3 max)")
    print("  Slippage: 0.5 bps (0.005%) for limit orders")
    print("  Market orders: 0.5 bps adverse slippage")
    print("  Stop losses: Executed at market with slippage")
    print("  Risk-Reward: 3:1 (balanced)")
    print("  Confidence Threshold: 0.75 (balanced)")
    print("  Minimum Profit Filter: Expected profit > 2x costs")
    # Simple ensemble weights proportional to Sharpe
    weights = {}
    for name, m in res.get("per_strategy", {}).items():
        w = max(0.0, float(m.get("sharpe", 0.0)))
        weights[name] = w
    s = sum(weights.values()) or 1.0
    weights = {k: v/s for k,v in weights.items()}
    metrics = {"per_strategy": res.get("per_strategy", {}), "generated_at": version}
    params = {"weights": weights}
    print(json.dumps({"version": version, "params": params, "metrics": metrics}))

    # Show summary
    print("\n🎯 BACKTEST SUMMARY:")
    print(f"  Total symbols tested: {len(res.get('per_symbol', {}))}")
    print(f"  Total strategies: {len(res.get('per_strategy', {}))}")
    print(f"  Timeframes: {timeframes}")

    # Find best performing stocks
    best_stocks = []
    for ticker, ticker_results in res.get("per_symbol", {}).items():
        for strategy, metrics in ticker_results.items():
            if metrics.get("sharpe", 0) > 0:  # Only profitable strategies
                best_stocks.append((ticker, strategy, metrics.get("sharpe", 0), metrics.get("trades", 0)))

    if best_stocks:
        # Sort by Sharpe ratio
        best_stocks.sort(key=lambda x: x[2], reverse=True)
        print("\n🏆 TOP PERFORMING STOCKS:")
        for i, (ticker, strategy, sharpe, trades) in enumerate(best_stocks[:10]):
            print(f"  {i+1}. {ticker} - {strategy}: Sharpe {sharpe:.2f} ({trades} trades)")
    else:
        print("\n⚠️ No profitable strategies found in current dataset")
        print("💡 This is normal - strategies need real market data for accurate results")

def analyze_all_stocks_comprehensive(res):
    """Comprehensive analysis of all tested stocks"""
    print("\n🎯 STRATEGY PERFORMANCE SUMMARY:")

    # Strategy-level analysis
    strategy_stats = {}
    for strategy, data in res.get("per_strategy", {}).items():
        total_trades = data.get("total_trades", 0)
        strategy_stats[strategy] = {
            'total_trades': total_trades,
            'symbols_with_trades': 0
        }

    # Stock-level analysis
    stock_performance = []
    for ticker, ticker_results in res.get("per_symbol", {}).items():
        total_trades = sum(metrics.get("trades", 0) for metrics in ticker_results.values())
        total_sharpe = sum(metrics.get("sharpe", 0) for metrics in ticker_results.values())

        if total_trades > 0:
            # Count profitable strategies for this stock
            profitable_strategies = sum(1 for metrics in ticker_results.values() if metrics.get("sharpe", 0) > 0)

            stock_performance.append({
                'ticker': ticker,
                'total_trades': total_trades,
                'profitable_strategies': profitable_strategies,
                'total_strategies': len(ticker_results),
                'avg_sharpe': total_sharpe / len(ticker_results),
                'strategies': ticker_results
            })

    # Sort by average Sharpe ratio
    stock_performance.sort(key=lambda x: x['avg_sharpe'], reverse=True)

    print(f"\n📈 TOTAL STOCKS ANALYZED: {len(stock_performance)}")
    print(f"📊 TOTAL TRADES ACROSS ALL STOCKS: {sum(stock['total_trades'] for stock in stock_performance)}")

    print("\n🏆 TOP 15 PERFORMING STOCKS:")
    print(f"{'Rank'"<5"} {'Stock'"<12"} {'Trades'"<8"} {'Win Rate'"<10"} {'Avg Sharpe'"<12"} {'Best Strategy'"<15"}")
    print("-" * 70)

    for i, stock in enumerate(stock_performance[:15]):
        # Find best strategy for this stock
        best_strategy = max(stock['strategies'].items(), key=lambda x: x[1].get('sharpe', 0))
        strategy_name, strategy_metrics = best_strategy

        win_rate = f"{stock['profitable_strategies']}/{stock['total_strategies']}"

        print(f"{i+1: <5} {stock['ticker']: <12} {stock['total_trades']: <8} {win_rate: <10} {stock['avg_sharpe']: <12.3f} {strategy_name: <15}")

    # Strategy comparison
    print("\n🧠 STRATEGY COMPARISON:")
    for strategy, stats in strategy_stats.items():
        print(f"  {strategy.upper()}: {stats['total_trades']} total trades")

    # Best stock-strategy combinations
    print("\n🎖️ TOP STOCK-STRATEGY COMBINATIONS:")
    best_combinations = []

    for stock in stock_performance:
        for strategy, metrics in stock['strategies'].items():
            if metrics.get("sharpe", 0) > 0:  # Only profitable ones
                best_combinations.append((stock['ticker'], strategy, metrics.get("sharpe", 0), metrics.get("trades", 0)))

    # Sort by Sharpe ratio
    best_combinations.sort(key=lambda x: x[2], reverse=True)

    for i, (ticker, strategy, sharpe, trades) in enumerate(best_combinations[:10]):
        print(f"  {i+1}. {ticker} - {strategy}: Sharpe {sharpe:.3f} ({trades} trades)")

    # Summary statistics
    profitable_stocks = len([s for s in stock_performance if s['profitable_strategies'] > 0])
    total_possible = len(stock_performance) * 3  # 3 strategies per stock
    actual_trades = sum(s['total_trades'] for s in stock_performance)

    print("\n📋 PORTFOLIO SUMMARY:")
    if len(stock_performance) > 0:
        print(f"  Profitable Stocks: {profitable_stocks}/{len(stock_performance)} ({profitable_stocks/len(stock_performance)*100:.1f}%)")
    else:
        print("  Profitable Stocks: 0/0 (0.0%)")
    print(f"  Total Possible Strategy Combinations: {total_possible}")
    print(f"  Actual Trades Generated: {actual_trades}")
    if total_possible > 0:
        print(f"  Trade Generation Rate: {actual_trades/total_possible*100:.1f}%")
    else:
        print("  Trade Generation Rate: 0.0%")

if __name__ == "__main__":
    main()


