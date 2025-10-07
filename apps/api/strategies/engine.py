from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Callable
import pandas as pd


@dataclass
class Signal:
    action: str  # BUY/SELL/EXIT_LONG/EXIT_SHORT
    entry: float
    stop: float
    target: float | None
    confidence: float
    strategy: str
    rationale: Dict


Strategy = Callable[[pd.DataFrame], Signal | None]


def trend_follow(df: pd.DataFrame) -> Signal | None:
    if len(df) < 100:  # Increased data requirement
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # ENHANCED TREND FILTERS - Aligned with momentum breakout analysis
    if (pd.notna(last.get("ema20")) and pd.notna(last.get("ema50")) and pd.notna(last.get("adx14")) and
        pd.notna(last.get("rsi14")) and pd.notna(last.get("bb_width")) and pd.notna(last.get("atr14")) and
        pd.notna(last.get("macd")) and pd.notna(last.get("macd_signal")) and pd.notna(last.get("macd_hist")) and
        pd.notna(last.get("vwap")) and pd.notna(last.get("volume"))):

        crossed_up = prev["ema20"] <= prev["ema50"] and last["ema20"] > last["ema50"]
        crossed_dn = prev["ema20"] >= prev["ema50"] and last["ema20"] < last["ema50"]

        # VOLUME CONFIRMATION - Critical for momentum breakouts
        vol_avg = df["volume"].rolling(20).mean().iloc[-1]
        volume_spike = last["volume"] > vol_avg * 1.5 if pd.notna(vol_avg) and vol_avg > 0 else False

        # RSI MOMENTUM - Rising in 55-80 range (not overbought like ChatGPT analysis)
        rsi_rising = (last["rsi14"] > prev.get("rsi14", 50) and
                     last["rsi14"] >= 55 and last["rsi14"] <= 75)

        # TREND STRENGTH - ADX requirement
        adx_strong = last["adx14"] >= 25  # Reduced from 28 to align with analysis

        # MOMENTUM CONFIRMATION - MACD bullish
        macd_bullish = (last["macd"] > last["macd_signal"] and
                       last["macd_hist"] > 0)

        # VWAP BREAKOUT - Price above VWAP (buyers in control)
        vwap_breakout = last["close"] > last["vwap"]

        # VOLATILITY BREAKOUT - Price near Bollinger upper
        bb_breakout = last["close"] >= last.get("bb_upper", last["close"] * 1.1) * 0.995

        # BUY SIGNAL - Enhanced with momentum indicators
        if (crossed_up and adx_strong and rsi_rising and macd_bullish and
            vwap_breakout and bb_breakout and volume_spike and
            last.get("bb_width", 0.05) > 0.015 and  # Good volatility
            last["atr14"] > last["close"] * 0.005):  # Sufficient volatility

            entry = float(last["close"])
            stop = float(last["close"] - 1.5 * last["atr14"])
            target = float(entry + 3.0 * (entry - stop))
            confidence = min(0.95, 0.8 + (last["adx14"] - 25) * 0.005 +
                           (0.1 if volume_spike else 0) + (0.1 if macd_bullish else 0))
            return Signal("BUY", entry, stop, target, confidence, "trend_follow",
                         {"ema_cross":"20>50","adx":float(last["adx14"]),"rsi":float(last["rsi14"]),
                          "macd_bullish":macd_bullish,"vwap_breakout":vwap_breakout,"volume_spike":volume_spike,
                          "bb_breakout":bb_breakout,"momentum_aligned":True,"improved":True})

        # SELL SIGNAL - Enhanced with momentum indicators
        if (crossed_dn and adx_strong and rsi_rising and
            (last["macd"] < last["macd_signal"] and last["macd_hist"] < 0) and  # MACD bearish
            last["close"] < last["vwap"] and  # Below VWAP
            volume_spike and
            last.get("bb_width", 0.05) > 0.015 and
            last["atr14"] > last["close"] * 0.005):

            entry = float(last["close"])
            stop = float(last["close"] + 1.5 * last["atr14"])
            target = float(entry - 3.0 * (stop - entry))
            confidence = min(0.95, 0.8 + (last["adx14"] - 25) * 0.005 + (0.1 if volume_spike else 0))
            return Signal("SELL", entry, stop, target, confidence, "trend_follow",
                         {"ema_cross":"20<50","adx":float(last["adx14"]),"rsi":float(last["rsi14"]),
                          "macd_bearish":True,"vwap_breakout":False,"volume_spike":volume_spike,
                          "momentum_aligned":True,"improved":True})
    return None


def mean_reversion(df: pd.DataFrame) -> Signal | None:
    # TEMPORARILY DISABLE MEAN REVERSION - OFTEN NOISY IN TRENDING MARKETS
    return None

    if len(df) < 100:  # Much longer lookback for better context
        return None
    last = df.iloc[-1]

    # ULTRA-RESTRICTIVE MEAN REVERSION - Only extreme setups with confirming factors
    if (pd.notna(last.get("rsi14")) and pd.notna(last.get("bb_lower")) and pd.notna(last.get("bb_upper")) and
        pd.notna(last.get("adx14")) and pd.notna(last.get("volume")) and pd.notna(last.get("atr14"))):

        # BUY: Extreme oversold with low ADX (sideways market) and volume confirmation
        if (last["rsi14"] < 20 and  # Ultra oversold
            last["close"] < last["bb_lower"] * 0.995 and  # Deep below lower BB
            last.get("adx14", 25) < 20 and  # Low ADX = ranging market
            last["atr14"] < last["close"] * 0.01 and  # Low volatility environment
            last["volume"] > df["volume"].rolling(20).mean().iloc[-1] * 1.2):  # Above average volume

            entry = float(last["close"])
            stop = float(last["close"] - 2.0 * last["atr14"])  # Very wide stops for ranging moves
            target = float(last["bb_mid"]) if pd.notna(last.get("bb_mid")) else entry * 1.05
            confidence = min(0.8, 0.6 + (20 - last["rsi14"]) * 0.02)
            return Signal("BUY", entry, stop, target, confidence, "mean_reversion",
                         {"rsi":float(last["rsi14"]),"bb_breakout":True,"adx":float(last["adx14"]),"ultra_restrictive":True,"improved":True})

        # SELL: Extreme overbought with low ADX and volume confirmation
        if (last["rsi14"] > 80 and  # Ultra overbought
            last["close"] > last["bb_upper"] * 1.005 and  # Deep above upper BB
            last.get("adx14", 25) < 20 and  # Low ADX = ranging market
            last["atr14"] < last["close"] * 0.01 and  # Low volatility
            last["volume"] > df["volume"].rolling(20).mean().iloc[-1] * 1.2):  # Above average volume

            entry = float(last["close"])
            stop = float(last["close"] + 2.0 * last["atr14"])
            target = float(last["bb_mid"]) if pd.notna(last.get("bb_mid")) else entry * 0.95
            confidence = min(0.8, 0.6 + (last["rsi14"] - 80) * 0.02)
            return Signal("SELL", entry, stop, target, confidence, "mean_reversion",
                         {"rsi":float(last["rsi14"]),"bb_breakout":True,"adx":float(last["adx14"]),"ultra_restrictive":True,"improved":True})
    return None


def momentum(df: pd.DataFrame) -> Signal | None:
    # TEMPORARILY DISABLE MOMENTUM STRATEGY - CAUSING TOO MANY TRADES
    return None

    if len(df) < 60:  # Increased data requirement
        return None
    last = df.iloc[-1]

    # Calculate volume z-score
    vol = df["volume"].rolling(20).mean()
    vol_z = (df["volume"] - vol) / (df["volume"].rolling(20).std() + 1e-9)
    last_z = float(vol_z.iloc[-1]) if pd.notna(vol_z.iloc[-1]) else 0.0

    # ULTRA-RESTRICTIVE FILTERS - Only strongest momentum setups
    if (pd.notna(last.get("vwap")) and pd.notna(last.get("ema20")) and pd.notna(last.get("ema50")) and
        pd.notna(last.get("rsi14")) and pd.notna(last.get("atr14"))):

        # BUY: Extremely strong bullish momentum with oversold bounce
        if (last["close"] > last["vwap"] and
            last["ema20"] > last["ema50"] and
            last_z > 2.5 and  # Very strong volume spike (>2.5 std dev)
            last["close"] > last["ema20"] * 1.005 and  # Significant distance above EMA
            last.get("rsi14", 50) > 65 and  # RSI showing strength, not overbought
            last["atr14"] > last["close"] * 0.005):  # Sufficient volatility

            entry = float(last["close"])
            stop = float(last["close"] - 1.5 * last["atr14"])  # Wider stop for volatile moves
            target = float(entry + 3.0 * (entry - stop))  # Higher reward:risk
            confidence = min(0.9, 0.7 + min(last_z - 2.5, 1.5) * 0.1)
            return Signal("BUY", entry, stop, target, confidence, "momentum",
                         {"vol_z":last_z,"vwap_breakout":True,"ultra_restrictive":True,"improved":True})

        # SELL: Extremely strong bearish momentum with overbought bounce
        if (last["close"] < last["vwap"] and
            last["ema20"] < last["ema50"] and
            last_z > 2.5 and  # Very strong volume spike
            last["close"] < last["ema20"] * 0.995 and  # Significant distance below EMA
            last.get("rsi14", 50) < 35 and  # RSI showing weakness, not oversold
            last["atr14"] > last["close"] * 0.005):  # Sufficient volatility

            entry = float(last["close"])
            stop = float(last["close"] + 1.5 * last["atr14"])
            target = float(entry - 3.0 * (stop - entry))
            confidence = min(0.9, 0.7 + min(last_z - 2.5, 1.5) * 0.1)
            return Signal("SELL", entry, stop, target, confidence, "momentum",
                         {"vol_z":last_z,"vwap_breakout":True,"ultra_restrictive":True,"improved":True})
    return None


def signal_quality_filter(signal: Signal, df: pd.DataFrame) -> bool:
    """BALANCED signal filtering - quality setups without being impossible"""

    # Reasonable confidence threshold
    if signal.confidence < 0.7:  # Reduced from 0.75 to 0.7
        return False

    # Check for improved strategies
    if not signal.rationale.get("improved", False):
        return False

    last = df.iloc[-1]

    # Strategy-specific quality checks
    if signal.strategy == "trend_follow":
        # Enhanced momentum breakout confirmation
        adx = last.get("adx14", 0)
        rsi = last.get("rsi14", 50)
        bb_width = last.get("bb_width", 0.05)
        rationale = signal.rationale

        # Must have momentum alignment markers
        momentum_aligned = rationale.get("momentum_aligned", False)
        volume_spike = rationale.get("volume_spike", False)
        macd_bullish = rationale.get("macd_bullish", False)

        return (adx >= 25 and  # Reduced ADX requirement for momentum breakouts
                bb_width > 0.015 and  # Good volatility
                45 < rsi < 80 and  # RSI in momentum range (55-75 rising preferred)
                momentum_aligned and  # Must have momentum confirmation
                (volume_spike or macd_bullish))  # At least one volume/MACD confirmation

    elif signal.strategy == "mean_reversion":
        # Selective mean reversion setups
        adx = last.get("adx14", 25)
        rsi = last.get("rsi14", 50)
        return (adx < 25 and  # Low ADX = ranging market
                ((rsi < 30) or (rsi > 70)))  # Extreme RSI levels

    elif signal.strategy == "momentum":
        # Strong momentum confirmation
        vol = df["volume"].rolling(20).mean()
        vol_z = (df["volume"] - vol) / (df["volume"].rolling(20).std() + 1e-9)
        last_z = float(vol_z.iloc[-1]) if pd.notna(vol_z.iloc[-1]) else 0.0
        return last_z > 2.0  # Strong volume confirmation

    return True  # Allow other strategies

def run_strategies(df: pd.DataFrame) -> List[Signal]:
    signals: List[Signal] = []
    # FOCUS ON TREND_FOLLOW ONLY - DISABLE OTHERS TO PREVENT OVERTRADING
    for strat in (trend_follow,):  # Only trend_follow for now
        try:
            s = strat(df)
            if s and signal_quality_filter(s, df):
                signals.append(s)
        except Exception:
            continue
    return signals


