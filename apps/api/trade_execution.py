#!/usr/bin/env python3
"""
Common Trade Execution Logic

Shared between live execution (auto_execute_signals.py) and backtesting (execute_backtest_trades.py)
Provides consistent buy/sell logic with configurable features.
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, enable_advanced_exits: bool = True, enable_timeframe_precedence: bool = True):
        """
        Initialize trade executor with configurable features.

        Args:
            enable_advanced_exits: Enable smart profit-taking and stop losses
            enable_timeframe_precedence: Enable multi-timeframe signal precedence
        """
        self.enable_advanced_exits = enable_advanced_exits
        self.enable_timeframe_precedence = enable_timeframe_precedence

    def should_execute_signal(self, signal: Dict, current_position: Dict = None,
                            position_timeframe: str = None, context: Dict = None) -> Tuple[bool, str]:
        """
        Determine if a trading signal should be executed based on current conditions.

        Args:
            signal: Signal dict with action, timeframe, confidence, etc.
            current_position: Current position dict (qty, avg_price)
            position_timeframe: Timeframe that opened current position
            context: Additional context (technical indicators, market data)

        Returns:
            (should_execute, reason)
        """
        if not current_position:
            current_position = {'qty': 0, 'avg_price': 0}

        action = signal['action']
        signal_timeframe = signal.get('timeframe', '1m')
        confidence = signal.get('confidence', 0.5)

        # Basic position validation
        if action == 'SELL' and current_position['qty'] <= 0:
            return False, "no_long_position"

        if action == 'BUY' and current_position['qty'] >= 0:
            # Allow BUY for new positions or to add to existing long positions
            pass

        # Timeframe precedence (if enabled)
        if self.enable_timeframe_precedence and position_timeframe:
            timeframe_hierarchy = {'1m': 1, '5m': 2, '15m': 3, '1h': 4, '1d': 5}
            signal_rank = timeframe_hierarchy.get(signal_timeframe, 0)
            position_rank = timeframe_hierarchy.get(position_timeframe, 0)

            # DISABLE STRICT TIMEFRAME PRECEDENCE FOR BETTER SIGNAL FLOW
            # if action == 'BUY' and position_rank > signal_rank:
            #     return False, f"lower_timeframe_buy_ignored_{position_timeframe}"

            if action == 'SELL':
                # SELL signals check hierarchy but are more permissive than before
                rank_difference = position_rank - signal_rank
                if rank_difference <= 2:  # Allow same timeframe or one level down
                    pass  # Allow the sell signal
                elif rank_difference > 4:  # Too far down the hierarchy (2+ levels down)
                    return False, f"too_low_timeframe_sell_{signal_timeframe}_vs_{position_timeframe}"
                else:
                    # Moderate timeframe difference - allow with caution
                    pass

        # Advanced exits (if enabled and we have position and context)
        if self.enable_advanced_exits and current_position['qty'] > 0 and context:
            entry_price = current_position['avg_price']
            current_price = context.get('current_price', entry_price)
            pnl_pct = (current_price - entry_price) / entry_price * 100

            # Check if we should exit for profit/risk management
            technical_context = context.get('technical_context', {})
            should_exit_profit = self._should_exit_for_profit(pnl_pct, technical_context)
            should_exit_loss = self._should_exit_for_loss(pnl_pct, technical_context)

            if should_exit_profit:
                return False, f"profit_taking_triggered_{pnl_pct:.1f}%"

            if should_exit_loss:
                return False, f"stop_loss_triggered_{pnl_pct:.1f}%"

        return True, "signal_valid"

    def _should_exit_for_profit(self, pnl_pct: float, context: Dict) -> bool:
        """RELAXED profit-taking logic - allow more profit capture"""
        # Always take profits at significant levels
        if pnl_pct >= 15.0:  # Increased from 10.0%
            return True

        if pnl_pct >= 8.0:  # Increased from 5.0%
            # Check if momentum is still strong
            if context.get("trend") == "bullish" and context.get("rsi", 50) > 60:  # Lowered from 70
                return False  # Moderate momentum continues
            else:
                return True

        return False

    def _should_exit_for_loss(self, pnl_pct: float, context: Dict) -> bool:
        """RELAXED stop loss logic - allow more breathing room"""
        # Large losses always exit immediately
        if pnl_pct <= -5.0:  # Relaxed from -3.0% back to -5.0%
            return True

        if pnl_pct <= -2.5:  # Relaxed from -1.5% to -2.5%
            # Check if trend is still intact - less strict
            if context.get("trend") == "bullish" and context.get("rsi", 50) > 30:  # Lower RSI requirement
                return False

            return True  # Exit on significant weakness

        return False

    def should_exit_on_momentum_failure(self, entry_indicators: Dict, current_indicators: Dict) -> Tuple[bool, str]:
        """
        Detect momentum failure patterns that should trigger early exits.

        Args:
            entry_indicators: Technical indicators at position entry
            current_indicators: Current technical indicators

        Returns:
            (should_exit, reason)
        """
        if not entry_indicators or not current_indicators:
            return False, "insufficient_data"

        reasons = []

        # RSI reversal: Significant drop from overbought levels
        rsi_drop = entry_indicators.get('rsi14', 50) - current_indicators.get('rsi14', 50)
        if rsi_drop > 20 and entry_indicators.get('rsi14', 50) > 65:
            reasons.append(f"rsi_reversal_{rsi_drop:.1f}")

        # MACD flip: Positive to negative momentum
        macd_flip = (entry_indicators.get('macd', 0) > 0 and
                    current_indicators.get('macd', 0) < 0 and
                    current_indicators.get('macd_hist', 0) < 0)
        if macd_flip:
            reasons.append("macd_flip_negative")

        # ADX trend exhaustion: Losing directional strength
        adx_drop = entry_indicators.get('adx14', 25) - current_indicators.get('adx14', 25)
        if adx_drop > 10 and current_indicators.get('adx14', 25) < 20:
            reasons.append(f"adx_exhaustion_{adx_drop:.1f}")

        # Bollinger Band squeeze tightening (volatility contraction)
        bb_width_entry = entry_indicators.get('bb_width', 0.05)
        bb_width_current = current_indicators.get('bb_width', 0.05)
        if bb_width_current < bb_width_entry * 0.7:  # 30% tighter bands
            reasons.append("bb_squeeze_tightening")

        # EMA convergence: Fast EMA catching up to slow EMA (trend weakening)
        ema20_entry = entry_indicators.get('ema20', 0)
        ema50_entry = entry_indicators.get('ema50', 0)
        ema20_current = current_indicators.get('ema20', 0)
        ema50_current = current_indicators.get('ema50', 0)

        if ema50_entry > 0:
            ema_spread_entry = abs(ema20_entry - ema50_entry) / ema50_entry
            ema_spread_current = abs(ema20_current - ema50_current) / ema50_current if ema50_current > 0 else 0
            if ema_spread_current < ema_spread_entry * 0.5:  # EMAs converging
                reasons.append("ema_convergence")

        # Volume drying up relative to entry
        volume_ratio = current_indicators.get('volume', 1) / max(entry_indicators.get('volume', 1), 1)
        if volume_ratio < 0.5:  # Volume less than half of entry
            reasons.append("volume_drying_up")

        should_exit = len(reasons) >= 2  # Require multiple signals for exit
        reason_str = ", ".join(reasons) if reasons else "no_momentum_failure"

        return should_exit, reason_str

    def get_technical_context(self, symbol_id: str, ticker: str, exchange: str,
                            entry_price: float, current_price: float, sb) -> Dict:
        """
        Get technical indicators for smarter exit decisions.

        Args:
            symbol_id: Symbol identifier
            ticker: Symbol ticker
            exchange: Exchange name
            entry_price: Position entry price
            current_price: Current market price
            sb: Supabase client

        Returns:
            Technical context dict with trend, RSI, volume, etc.
        """
        try:
            # Get recent candles for technical analysis
            candles = sb.table("candles").select("close,high,low,volume").eq("symbol_id", symbol_id).eq("timeframe", "1m").order("ts", desc=True).limit(250).execute().data or []

            if len(candles) < 20:
                return {"trend": "unknown", "rsi": 50, "volume_trend": "neutral", "reason": "insufficient_data"}

            # Calculate simple trend (price direction)
            recent_prices = [float(c['close']) for c in candles[:20]]
            trend_slope = (recent_prices[0] - recent_prices[-1]) / recent_prices[-1] * 100
            trend = "bullish" if trend_slope > 0.5 else "bearish" if trend_slope < -0.5 else "sideways"

            # Calculate RSI approximation
            gains = sum(max(0, recent_prices[i] - recent_prices[i+1]) for i in range(19))
            losses = sum(max(0, recent_prices[i+1] - recent_prices[i]) for i in range(19))
            if losses > 0:
                rs = gains / losses
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100

            # Volume trend
            recent_volume = [float(c.get('volume', 0)) for c in candles[:10]]
            avg_volume = sum(recent_volume) / len(recent_volume)
            latest_volume = recent_volume[0]
            volume_trend = "high" if latest_volume > avg_volume * 1.2 else "low" if latest_volume < avg_volume * 0.8 else "normal"

            # Support/resistance levels
            highs = [float(c['high']) for c in candles[:20]]
            lows = [float(c['low']) for c in candles[:20]]
            recent_high = max(highs)
            recent_low = min(lows)

            return {
                "trend": trend,
                "rsi": rsi,
                "volume_trend": volume_trend,
                "recent_high": recent_high,
                "recent_low": recent_low,
                "entry_price": entry_price,
                "current_price": current_price
            }

        except Exception as e:
            logger.warning(f"Error getting technical context for {ticker}: {e}")
            return {"trend": "unknown", "rsi": 50, "volume_trend": "neutral", "reason": "error"}

    def calculate_position_size(self, action: str, symbol: str, entry_price: float,
                               timeframe: str = '1m', risk_limits: Dict = None,
                               portfolio_value: float = None, confidence: float = 0.8) -> int:
        """
        Calculate position size based on portfolio value, timeframe, confidence, and risk limits.
        Returns integer quantities for stock trading.

        Args:
            action: BUY or SELL
            symbol: Symbol ticker
            entry_price: Entry price
            timeframe: Signal timeframe
            risk_limits: Risk management limits
            portfolio_value: Total portfolio value (if available)
            confidence: Signal confidence (0.0-1.0)

        Returns:
            Position quantity (integer)
        """
        if not risk_limits:
            risk_limits = {'max_position_value': 10000}

        # Use portfolio-based sizing if portfolio value is provided
        if portfolio_value and portfolio_value > 0:
            # Risk 1-2% of total portfolio per trade based on confidence
            base_risk_pct = 0.01 + (confidence - 0.5) * 0.01  # 1-2% based on confidence
            base_risk_pct = min(base_risk_pct, 0.02)  # Cap at 2%

            # Timeframe adjustments (higher timeframes get larger positions)
            timeframe_multipliers = {
                '1m': 0.5,   # 50% of base risk (shortest timeframe, most signals)
                '5m': 0.75,  # 75% of base risk
                '15m': 1.0,  # 100% of base risk
                '1h': 1.25, # 125% of base risk
                '1d': 1.5   # 150% of base risk (longest timeframe, fewer signals)
            }

            multiplier = timeframe_multipliers.get(timeframe, 0.75)
            risk_amount = portfolio_value * base_risk_pct * multiplier
            target_value = risk_amount
        else:
            # Fallback to fixed position sizing
            base_target_value = risk_limits.get('max_position_value', 10000)

            # Timeframe-based position sizing
            timeframe_multipliers = {
                '1m': 0.3,   # 30% of base
                '5m': 0.5,   # 50% of base
                '15m': 0.8,  # 80% of base
                '1h': 1.0,   # 100% of base
                '1d': 1.2    # 120% of base
            }

            multiplier = timeframe_multipliers.get(timeframe, 0.5)
            target_value = base_target_value * multiplier

        quantity = target_value / entry_price

        # For stock trading, always round to nearest integer
        # Stocks are traded in whole shares, no fractional quantities
        quantity = round(quantity)

        # Ensure minimum quantity of 1 and reasonable maximum
        return max(1, min(quantity, 10000))  # Cap at 10,000 shares

    def update_position(self, symbol_id: str, action: str, quantity: float, price: float,
                        current_position: Dict = None) -> Dict:
        """
        Update position after executing a trade.
        Prevents negative positions for stock trading.

        Args:
            symbol_id: Symbol identifier
            action: BUY or SELL
            quantity: Trade quantity (must be positive)
            price: Trade price
            current_position: Current position dict

        Returns:
            Updated position dict
        """
        if not current_position:
            current_position = {'qty': 0, 'avg_price': 0.0}

        curr_qty = current_position['qty']
        curr_avg = current_position['avg_price']

        if action == 'BUY':
            if curr_qty <= 0:  # Opening new position or covering short
                new_qty = quantity
                new_avg = price
            else:  # Adding to existing long position
                new_qty = curr_qty + quantity
                new_avg = ((curr_qty * curr_avg) + (quantity * price)) / new_qty
        else:  # SELL
            if curr_qty <= 0:
                # Cannot sell if no long position - this shouldn't happen due to validation
                logger.warning(f"Attempted to sell {quantity} but no long position (qty: {curr_qty})")
                return current_position  # Return unchanged

            # Ensure we don't sell more than we own
            actual_sell_qty = min(quantity, curr_qty)
            new_qty = curr_qty - actual_sell_qty
            new_avg = curr_avg  # Average price stays the same for sells

            if actual_sell_qty < quantity:
                logger.warning(f"Reduced sell quantity from {quantity} to {actual_sell_qty} to prevent negative position")

        return {
            'qty': new_qty,
            'avg_price': new_avg,
            'last_update': price,
            'last_action': action
        }