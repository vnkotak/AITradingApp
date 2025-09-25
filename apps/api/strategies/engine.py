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
    if len(df) < 60:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2]
    # EMA cross + ADX filter
    if pd.notna(last.get("ema20")) and pd.notna(last.get("ema50")) and pd.notna(last.get("adx14")):
        crossed_up = prev["ema20"] <= prev["ema50"] and last["ema20"] > last["ema50"]
        crossed_dn = prev["ema20"] >= prev["ema50"] and last["ema20"] < last["ema50"]
        if crossed_up and last["adx14"] > 15:
            entry = float(last["close"])
            stop = float(last["close"] - 1.5 * last["atr14"])
            target = float(entry + 2 * (entry - stop))
            return Signal("BUY", entry, stop, target, 0.6, "trend_follow", {"ema_cross":"20>50","adx":float(last["adx14"])})
        if crossed_dn and last["adx14"] > 15:
            entry = float(last["close"])
            stop = float(last["close"] + 1.5 * last["atr14"])
            target = float(entry - 2 * (stop - entry))
            return Signal("SELL", entry, stop, target, 0.6, "trend_follow", {"ema_cross":"20<50","adx":float(last["adx14"])})
    return None


def mean_reversion(df: pd.DataFrame) -> Signal | None:
    if len(df) < 30:
        return None
    last = df.iloc[-1]
    if pd.notna(last.get("rsi14")) and pd.notna(last.get("bb_lower")) and pd.notna(last.get("bb_upper")):
        if last["rsi14"] < 30 and last["close"] < last["bb_lower"]:
            entry = float(last["close"])
            stop = float(min(last["bb_lower"], last["close"] - 1.2 * last["atr14"]))
            target = float(last["bb_mid"]) if pd.notna(last.get("bb_mid")) else None
            return Signal("BUY", entry, stop, target, 0.5, "mean_reversion", {"rsi":float(last["rsi14"])})
        if last["rsi14"] > 70 and last["close"] > last["bb_upper"]:
            entry = float(last["close"])
            stop = float(max(last["bb_upper"], last["close"] + 1.2 * last["atr14"]))
            target = float(last["bb_mid"]) if pd.notna(last.get("bb_mid")) else None
            return Signal("SELL", entry, stop, target, 0.5, "mean_reversion", {"rsi":float(last["rsi14"])})
    return None


def momentum(df: pd.DataFrame) -> Signal | None:
    if len(df) < 30:
        return None
    last = df.iloc[-1]
    vol = df["volume"].rolling(20).mean()
    vol_z = (df["volume"] - vol) / (df["volume"].rolling(20).std() + 1e-9)
    last_z = float(vol_z.iloc[-1]) if pd.notna(vol_z.iloc[-1]) else 0.0
    if pd.notna(last.get("vwap")) and pd.notna(last.get("ema20")):
        if last["close"] > last["vwap"] and last["ema20"] > last["ema50"] and last_z > 1.0:
            entry = float(last["close"])
            stop = float(last["close"] - 1.0 * last["atr14"]) if pd.notna(last.get("atr14")) else float(last["close"]*0.98)
            target = float(entry + 2 * (entry - stop))
            return Signal("BUY", entry, stop, target, 0.55, "momentum", {"vol_z":last_z})
        if last["close"] < last["vwap"] and last["ema20"] < last["ema50"] and last_z > 1.0:
            entry = float(last["close"])
            stop = float(last["close"] + 1.0 * last["atr14"]) if pd.notna(last.get("atr14")) else float(last["close"]*1.02)
            target = float(entry - 2 * (stop - entry))
            return Signal("SELL", entry, stop, target, 0.55, "momentum", {"vol_z":last_z})
    return None


def run_strategies(df: pd.DataFrame) -> List[Signal]:
    signals: List[Signal] = []
    for strat in (trend_follow, mean_reversion, momentum):
        try:
            s = strat(df)
            if s:
                signals.append(s)
        except Exception:
            continue
    return signals


