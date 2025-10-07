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

    # ULTRA-RESTRICTIVE TREND FILTERS - Only strongest trend setups
    if (pd.notna(last.get("ema20")) and pd.notna(last.get("ema50")) and pd.notna(last.get("adx14")) and
        pd.notna(last.get("rsi14")) and pd.notna(last.get("bb_width")) and pd.notna(last.get("atr14"))):

        crossed_up = prev["ema20"] <= prev["ema50"] and last["ema20"] > last["ema50"]
        crossed_dn = prev["ema20"] >= prev["ema50"] and last["ema20"] < last["ema50"]

        # BALANCED STRICT CRITERIA - Selective but achievable
        adx_min = 28  # Reasonable ADX requirement (strong trend)
        rsi_max_buy = 65  # Allow some overbought bounce
        rsi_min_sell = 35  # Allow some oversold bounce

        if (crossed_up and last["adx14"] > adx_min and
            (last.get("rsi14", 50) < rsi_max_buy or last["adx14"] > 40) and  # Allow higher RSI in very strong trends
            last.get("bb_width", 0.05) > 0.012 and  # Moderate volatility
            last["atr14"] > last["close"] * 0.006):  # Reasonable volatility environment

            entry = float(last["close"])
            stop = float(last["close"] - 1.5 * last["atr14"])  # Wider stops for trending moves
            target = float(entry + 3.0 * (entry - stop))  # Better reward:risk
            confidence = min(0.95, 0.75 + (last["adx14"] - adx_min) * 0.01)
            return Signal("BUY", entry, stop, target, confidence, "trend_follow",
                         {"ema_cross":"20>50","adx":float(last["adx14"]),"rsi":float(last["rsi14"]),"ultra_restrictive":True,"improved":True})

        if (crossed_dn and last["adx14"] > adx_min and
            (last.get("rsi14", 50) > rsi_min_sell or last["adx14"] > 40) and  # Allow lower RSI in very strong trends
            last.get("bb_width", 0.05) > 0.012 and  # Moderate volatility
            last["atr14"] > last["close"] * 0.006):  # Reasonable volatility environment

            entry = float(last["close"])
            stop = float(last["close"] + 1.5 * last["atr14"])
            target = float(entry - 3.0 * (stop - entry))
            confidence = min(0.95, 0.75 + (last["adx14"] - adx_min) * 0.01)
            return Signal("SELL", entry, stop, target, confidence, "trend_follow",
                         {"ema_cross":"20<50","adx":float(last["adx14"]),"rsi":float(last["rsi14"]),"ultra_restrictive":True,"improved":True})
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
        # Strong trend confirmation with balanced conditions
        adx = last.get("adx14", 0)
        rsi = last.get("rsi14", 50)
        bb_width = last.get("bb_width", 0.05)
        return (adx > 28 and  # Strong trend (>28)
                bb_width > 0.015 and  # Good volatility
                25 < rsi < 75)  # Reasonable RSI range

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


