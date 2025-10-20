import os
import json
import argparse
from datetime import datetime
from backtest import run_backtests, load_candles, backtest_strategy, BTTrade

def main():
    parser = argparse.ArgumentParser(description='Run backtests for trading strategies')
    parser.add_argument('--start-date', help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--tf', '--timeframe', default='5m', help='Timeframe to test')
    parser.add_argument('--strategy', default='trend_follow', help='Strategy to test')
    parser.add_argument('--max-symbols', type=int, default=10, help='Maximum symbols to test')

    args = parser.parse_args()

    version = f"bt-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    # Use command line args for limited testing
    strategies = [args.strategy]
    timeframes = [args.tf]
    symbols_limit = args.max_symbols
    res = run_backtests(strategies, timeframes, symbols_limit=symbols_limit)

    # Comprehensive analysis of all stocks
    print("\n📊 COMPREHENSIVE MULTI-STOCK ANALYSIS")
    analyze_all_stocks_comprehensive(res)
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
    print(f"  Timeframes: {['5m']}")

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
    print(f"  Profitable Stocks: {profitable_stocks}/{len(stock_performance)} ({profitable_stocks/len(stock_performance)*100:.1f}%)")
    print(f"  Total Possible Strategy Combinations: {total_possible}")
    print(f"  Actual Trades Generated: {actual_trades}")
    print(f"  Trade Generation Rate: {actual_trades/total_possible*100:.1f}%")

if __name__ == "__main__":
    main()


