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

    # IMPROVED FILTERS - More selective
    if pd.notna(last.get("ema20")) and pd.notna(last.get("ema50")) and pd.notna(last.get("adx14")):
        crossed_up = prev["ema20"] <= prev["ema50"] and last["ema20"] > last["ema50"]
        crossed_dn = prev["ema20"] >= prev["ema50"] and last["ema20"] < last["ema50"]

        # STRicTER CRITERIA - Higher ADX threshold
        if crossed_up and last["adx14"] > 25:  # Increased from 15 to 25
            entry = float(last["close"])
            # Tighter stop loss for better risk management
            stop = float(last["close"] - 1.2 * last["atr14"])  # Reduced from 1.5x to 1.2x
            target = float(entry + 2.5 * (entry - stop))  # Better reward:risk
            confidence = min(0.9, 0.6 + (last["adx14"] - 25) * 0.02)  # Higher confidence for stronger trends
            return Signal("BUY", entry, stop, target, confidence, "trend_follow",
                         {"ema_cross":"20>50","adx":float(last["adx14"]),"improved":True})

        if crossed_dn and last["adx14"] > 25:  # Increased from 15 to 25
            entry = float(last["close"])
            stop = float(last["close"] + 1.2 * last["atr14"])  # Reduced from 1.5x to 1.2x
            target = float(entry - 2.5 * (stop - entry))  # Better reward:risk
            confidence = min(0.9, 0.6 + (last["adx14"] - 25) * 0.02)
            return Signal("SELL", entry, stop, target, confidence, "trend_follow",
                         {"ema_cross":"20<50","adx":float(last["adx14"]),"improved":True})
    return None


def mean_reversion(df: pd.DataFrame) -> Signal | None:
    if len(df) < 60:  # Increased data requirement
        return None
    last = df.iloc[-1]

    if pd.notna(last.get("rsi14")) and pd.notna(last.get("bb_lower")) and pd.notna(last.get("bb_upper")):
        # IMPROVED FILTERS - More extreme conditions only
        if last["rsi14"] < 25 and last["close"] < last["bb_lower"]:  # Stricter from 30 to 25
            entry = float(last["close"])
            # Tighter stop for better risk management
            stop = float(min(last["bb_lower"], last["close"] - 1.0 * last["atr14"]))  # Reduced from 1.2x to 1.0x
            target = float(last["bb_mid"]) if pd.notna(last.get("bb_mid")) else None
            # Higher confidence for more extreme conditions
            confidence = min(0.8, 0.5 + (25 - last["rsi14"]) * 0.02)
            return Signal("BUY", entry, stop, target, confidence, "mean_reversion",
                         {"rsi":float(last["rsi14"]),"bb_breakout":True,"improved":True})

        if last["rsi14"] > 75 and last["close"] > last["bb_upper"]:  # Stricter from 70 to 75
            entry = float(last["close"])
            stop = float(max(last["bb_upper"], last["close"] + 1.0 * last["atr14"]))  # Reduced from 1.2x to 1.0x
            target = float(last["bb_mid"]) if pd.notna(last.get("bb_mid")) else None
            confidence = min(0.8, 0.5 + (last["rsi14"] - 75) * 0.02)
            return Signal("SELL", entry, stop, target, confidence, "mean_reversion",
                         {"rsi":float(last["rsi14"]),"bb_breakout":True,"improved":True})
    return None


def momentum(df: pd.DataFrame) -> Signal | None:
    if len(df) < 60:  # Increased data requirement
        return None
    last = df.iloc[-1]

    # Calculate volume z-score
    vol = df["volume"].rolling(20).mean()
    vol_z = (df["volume"] - vol) / (df["volume"].rolling(20).std() + 1e-9)
    last_z = float(vol_z.iloc[-1]) if pd.notna(vol_z.iloc[-1]) else 0.0

    if pd.notna(last.get("vwap")) and pd.notna(last.get("ema20")) and pd.notna(last.get("ema50")):
        # IMPROVED FILTERS - Higher volume threshold and better price action
        if (last["close"] > last["vwap"] and
            last["ema20"] > last["ema50"] and
            last_z > 1.5 and  # Increased from 1.0 to 1.5 (stronger volume spike)
            last["close"] > last["ema20"] * 1.001):  # Price above MA (strong momentum)

            entry = float(last["close"])
            # Tighter stop for better risk management
            stop = float(last["close"] - 0.8 * last["atr14"]) if pd.notna(last.get("atr14")) else float(last["close"]*0.992)
            target = float(entry + 2.5 * (entry - stop))  # Better reward:risk
            # Higher confidence for stronger setups
            confidence = min(0.85, 0.55 + min(last_z - 1.5, 2.0) * 0.1)
            return Signal("BUY", entry, stop, target, confidence, "momentum",
                         {"vol_z":last_z,"vwap_breakout":True,"improved":True})

        if (last["close"] < last["vwap"] and
            last["ema20"] < last["ema50"] and
            last_z > 1.5 and  # Increased from 1.0 to 1.5
            last["close"] < last["ema20"] * 0.999):  # Price below MA (strong down momentum)

            entry = float(last["close"])
            stop = float(last["close"] + 0.8 * last["atr14"]) if pd.notna(last.get("atr14")) else float(last["close"]*1.008)
            target = float(entry - 2.5 * (stop - entry))
            confidence = min(0.85, 0.55 + min(last_z - 1.5, 2.0) * 0.1)
            return Signal("SELL", entry, stop, target, confidence, "momentum",
                         {"vol_z":last_z,"vwap_breakout":True,"improved":True})
    return None


def signal_quality_filter(signal: Signal, df: pd.DataFrame) -> bool:
    """Filter signals for better quality - only keep high-confidence setups"""

    # Minimum confidence threshold
    if signal.confidence < 0.6:
        return False

    # Check for improved strategies only (exclude old logic)
    if not signal.rationale.get("improved", False):
        return False

    last = df.iloc[-1]

    # Additional filters based on strategy type
    if signal.strategy == "trend_follow":
        # Strong trend confirmation
        return last.get("adx14", 0) > 25

    elif signal.strategy == "mean_reversion":
        # Extreme RSI conditions only
        rsi = last.get("rsi14", 50)
        if signal.action == "BUY":
            return rsi < 25
        else:
            return rsi > 75

    elif signal.strategy == "momentum":
        # Strong volume confirmation
        vol = df["volume"].rolling(20).mean()
        vol_z = (df["volume"] - vol) / (df["volume"].rolling(20).std() + 1e-9)
        last_z = float(vol_z.iloc[-1]) if pd.notna(vol_z.iloc[-1]) else 0.0
        return last_z > 1.5

    return True

def run_strategies(df: pd.DataFrame) -> List[Signal]:
    signals: List[Signal] = []
    for strat in (trend_follow, mean_reversion, momentum):
        try:
            s = strat(df)
            if s and signal_quality_filter(s, df):
                signals.append(s)
        except Exception:
            continue
    return signals


