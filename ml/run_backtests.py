import os
import json
import argparse
from datetime import datetime
import pandas as pd
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
    print(f"🚀 Starting backtest with {symbols_limit} symbols, timeframe {timeframes[0]}...")
    res = run_backtests(strategies, timeframes, symbols_limit=symbols_limit, start_date=start_date, end_date=end_date)

    # Comprehensive analysis of all stocks
    print("\n📊 COMPREHENSIVE MULTI-STOCK ANALYSIS")
    analyze_all_stocks_comprehensive(res)

    # Analyze Hull Suite characteristics and suitability patterns
    analyze_hull_suite_characteristics(res)

    # Calculate total actual P&L across all trades and aggregate daily stats
    total_pnl = 0
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    total_positive_pnl = 0
    total_negative_pnl = 0

    # Aggregate daily statistics across all symbols
    global_daily_stats = {}

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
                        trades, _, daily_stats = backtest_strategy(df, strategy)

                        # Aggregate daily stats
                        for date, stats in daily_stats.items():
                            if date not in global_daily_stats:
                                global_daily_stats[date] = {'BUY': 0, 'SELL': 0, 'total': 0}
                            global_daily_stats[date]['BUY'] += stats['BUY']
                            global_daily_stats[date]['SELL'] += stats['SELL']
                            global_daily_stats[date]['total'] += stats['total']

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

    # Print global daily statistics
    if global_daily_stats:
        print(f"\n📊 AGGREGATE DAILY TRADE BREAKDOWN ACROSS ALL SYMBOLS:")
        print(f"{'Date':<12} {'BUY':<8} {'SELL':<8} {'Total':<8}")
        print("-" * 40)
        for date in sorted(global_daily_stats.keys()):
            stats = global_daily_stats[date]
            date_str = date.strftime('%Y-%m-%d')
            print(f"{date_str:<12} {stats['BUY']:<8} {stats['SELL']:<8} {stats['total']:<8}")

        # Show last date statistics
        last_date = max(global_daily_stats.keys())
        last_stats = global_daily_stats[last_date]
        last_date_str = last_date.strftime('%Y-%m-%d')
        print(f"\n📅 LAST DATE ({last_date_str}) STATS:")
        print(f"  BUY signals: {last_stats['BUY']}")
        print(f"  SELL signals: {last_stats['SELL']}")
        print(f"  Total trades: {last_stats['total']}")

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
    
    
def analyze_hull_suite_characteristics(res):
        """Analyze quantitative characteristics that make stocks suitable for Hull Suite"""
        print("\n🔬 HULL SUITE STRATEGY CHARACTERISTICS ANALYSIS")
    
        # Calculate characteristics for each stock that had Hull trades
        stock_characteristics = []
    
        for ticker, ticker_results in res.get("per_symbol", {}).items():
            for strategy, metrics in ticker_results.items():
                if strategy == "hull_suite" and metrics.get("trades", 0) > 0:
                    # Load historical data to calculate characteristics
                    try:
                        from backtest import supabase_client, load_candles
                        sb = supabase_client()
                        sym_data = sb.table("symbols").select("id").eq("ticker", ticker).eq("exchange", "NSE").single().execute().data
                        if sym_data:
                            df = load_candles(sym_data["id"], "15m", days=720)
                            if not df.empty and len(df) >= 100:  # Need sufficient data
                                # Calculate Hull-specific characteristics
                                chars = calculate_hull_characteristics(df)
                                chars.update({
                                    'ticker': ticker,
                                    'sharpe': metrics.get("sharpe", 0),
                                    'trades': metrics.get("trades", 0),
                                    'profitable': metrics.get("sharpe", 0) > 0
                                })
                                stock_characteristics.append(chars)
                    except Exception as e:
                        print(f"❌ Error calculating characteristics for {ticker}: {e}")
    
        if not stock_characteristics:
            print("❌ No stock characteristics data available")
            return []
    
        # Separate profitable vs unprofitable
        profitable = [s for s in stock_characteristics if s['profitable']]
        unprofitable = [s for s in stock_characteristics if not s['profitable']]
    
        print(f"\n📊 CHARACTERISTICS COMPARISON:")
        print(f"✅ Profitable Stocks ({len(profitable)}): {', '.join([s['ticker'] for s in profitable])}")
        print(f"❌ Unprofitable Stocks ({len(unprofitable)}): {', '.join([s['ticker'] for s in unprofitable])}")
    
        # Calculate average characteristics
        if profitable and unprofitable:
            print(f"\n📈 AVERAGE CHARACTERISTICS:")
    
            char_names = ['avg_adx', 'trend_consistency', 'volatility_regime', 'hma_slope_freq', 'volume_trend_corr']
            headers = ['Characteristic', 'Profitable Avg', 'Unprofitable Avg', 'Difference']
    
            print(f"{'Characteristic':<20} {'Profitable':<12} {'Unprofitable':<14} {'Better':<10}")
            print("-" * 70)
    
            for char_name in char_names:
                try:
                    prof_values = [s[char_name] for s in profitable if char_name in s and not pd.isna(s[char_name])]
                    unprof_values = [s[char_name] for s in unprofitable if char_name in s and not pd.isna(s[char_name])]

                    if prof_values and unprof_values:
                        prof_avg = sum(prof_values) / len(prof_values)
                        unprof_avg = sum(unprof_values) / len(unprof_values)
                        better = "Profitable" if prof_avg > unprof_avg else "Unprofitable"
                        print(f"{char_name:<20} {prof_avg:<12.3f} {unprof_avg:<14.3f} {better:<10}")
                    else:
                        print(f"{char_name:<20} {'N/A':<12} {'N/A':<14} {'N/A':<10}")
                except Exception as e:
                    print(f"{char_name:<20} {'ERROR':<12} {'ERROR':<14} {'ERROR':<10}")
    
        # Identify key discriminating factors
        print(f"\n🎯 KEY DISCRIMINATING FACTORS:")
        if profitable and unprofitable:
            # Find characteristics where profitable stocks significantly outperform
            factors = []
            for char_name in ['avg_adx', 'trend_consistency', 'volatility_regime', 'hma_slope_freq']:
                try:
                    prof_values = [s[char_name] for s in profitable if char_name in s and not pd.isna(s[char_name])]
                    unprof_values = [s[char_name] for s in unprofitable if char_name in s and not pd.isna(s[char_name])]

                    if prof_values and unprof_values:
                        prof_avg = sum(prof_values) / len(prof_values)
                        unprof_avg = sum(unprof_values) / len(unprof_values)
                        diff_pct = abs(prof_avg - unprof_avg) / max(abs(prof_avg), abs(unprof_avg)) * 100

                        if diff_pct > 20:  # 20% difference threshold
                            direction = "Higher" if prof_avg > unprof_avg else "Lower"
                            factors.append(f"{char_name} ({direction} in profitable stocks)")
                except Exception as e:
                    print(f"Error calculating factors for {char_name}: {e}")
    
            if factors:
                print("Stocks suitable for Hull Suite typically have:")
                for factor in factors:
                    print(f"  • {factor}")
            else:
                print("⚠️ No clear discriminating factors found - need more data")
    
        return stock_characteristics
    
    
def calculate_hull_characteristics(df):
        """Calculate quantitative characteristics that determine Hull Suite suitability"""
        from backtest import add_indicators
        df = add_indicators(df)
    
        # Skip if insufficient data
        if len(df) < 100 or 'hma55' not in df.columns or 'adx14' not in df.columns:
            return {}
    
        # 1. Average ADX (trend strength) - Hull works better in trending markets
        avg_adx = df['adx14'].mean()
    
        # 2. Trend Consistency - How often ADX indicates trending conditions
        trend_consistency = (df['adx14'] > 25).mean()  # % of time in trending regime
    
        # 3. Volatility Regime - Hull performs better in certain volatility ranges
        volatility_regime = df['bb_width'].mean()  # Average Bollinger Band width
    
        # 4. HMA Slope Frequency - How often HMA changes direction (Hull signal frequency)
        hma_slopes = []
        for i in range(2, len(df)):
            slope = df['hma55'].iloc[i] - df['hma55'].iloc[i-2]
            hma_slopes.append(slope)
    
        if hma_slopes:
            # Frequency of meaningful slope changes
            slope_changes = sum(1 for i in range(1, len(hma_slopes)) if (hma_slopes[i] * hma_slopes[i-1]) < 0)
            hma_slope_freq = slope_changes / len(hma_slopes) if hma_slopes else 0
        else:
            hma_slope_freq = 0
    
        # 5. Volume-Trend Correlation - Trending stocks often have volume confirmation
        volume_trend_corr = 0
        if 'volume' in df.columns and len(df) > 30:
            try:
                # Calculate trend direction (price momentum)
                price_momentum = df['close'].pct_change(5).shift(-5)  # 5-period forward return
                volume_ma = df['volume'].rolling(10).mean()

                # Correlation between volume and subsequent price movement
                valid_idx = ~(price_momentum.isna() | volume_ma.isna())
                if valid_idx.sum() > 10:
                    corr_data = pd.concat([price_momentum[valid_idx], volume_ma[valid_idx]], axis=1).dropna()
                    if len(corr_data) > 10:
                        volume_trend_corr = corr_data.iloc[:, 0].corr(corr_data.iloc[:, 1])
                        # Ensure it's not NaN
                        volume_trend_corr = volume_trend_corr if not pd.isna(volume_trend_corr) else 0
            except Exception as e:
                print(f"Volume correlation calculation failed: {e}")
                volume_trend_corr = 0
    
        return {
            'avg_adx': avg_adx,
            'trend_consistency': trend_consistency,
            'volatility_regime': volatility_regime,
            'hma_slope_freq': hma_slope_freq,
            'volume_trend_corr': volume_trend_corr
        }
    
    
if __name__ == "__main__":
    main()


