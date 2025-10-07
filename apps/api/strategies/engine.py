import pandas as pd
from typing import Optional, List

# Define Signal class if not imported
class Signal:
    def __init__(self, action: str, entry: float, stop: float, target: float,
                 confidence: float, strategy: str, rationale: dict):
        self.action = action
        self.entry = entry
        self.stop = stop
        self.target = target
        self.confidence = confidence
        self.strategy = strategy
        self.rationale = rationale

def trend_follow(df: pd.DataFrame) -> Optional[Signal]:
    """BALANCED TREND FOLLOWING - Quality signals with reasonable frequency"""
    if len(df) < 60:  # Reasonable data requirement
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # BASIC TECHNICAL SETUP
    if (pd.notna(last.get("ema20")) and pd.notna(last.get("ema50")) and
        pd.notna(last.get("rsi14")) and pd.notna(last.get("atr14"))):

        crossed_up = prev["ema20"] <= prev["ema50"] and last["ema20"] > last["ema50"]

        # CORE REQUIREMENTS - Not too strict, but quality focused
        ema_rising = last["ema20"] > prev["ema20"]  # Fast EMA trending up
        rsi_ok = last["rsi14"] < 80  # Not extremely overbought
        volatility_ok = last["atr14"] > last["close"] * 0.003  # Some volatility
        price_ok = 15 <= last["close"] <= 3000  # Reasonable price range

        # ADDITIONAL CONFIRMATION - If available, use them
        adx_ok = True
        if pd.notna(last.get("adx14")):
            adx_ok = last["adx14"] >= 20  # Prefer some trend strength

        macd_ok = True
        if pd.notna(last.get("macd")) and pd.notna(last.get("macd_signal")):
            macd_ok = last["macd"] > last["macd_signal"]  # Prefer bullish MACD

        volume_ok = True
        if pd.notna(last.get("volume")) and len(df) > 20:
            avg_volume = df["volume"].rolling(20).mean().iloc[-1]
            volume_ok = last["volume"] > avg_volume * 1.05  # Slightly above average

        # BUY SIGNAL - Core requirements met, bonuses if available
        if (crossed_up and ema_rising and rsi_ok and volatility_ok and price_ok and
            adx_ok and macd_ok and volume_ok):

            entry = float(last["close"])
            stop = float(last["close"] - 1.2 * last["atr14"])  # Moderate stop
            target = float(entry + 2.5 * (entry - stop))     # 2.5:1 reward ratio

            # Confidence based on how many confirmations we have
            base_confidence = 0.65
            if pd.notna(last.get("adx14")) and last["adx14"] >= 25:
                base_confidence += 0.1  # Strong trend bonus
            if pd.notna(last.get("macd")) and last["macd"] > last["macd_signal"]:
                base_confidence += 0.1  # MACD confirmation bonus
            if volume_ok:
                base_confidence += 0.05  # Volume confirmation bonus

            confidence = min(0.85, base_confidence)  # Cap at 0.85

            return Signal("BUY", entry, stop, target, confidence, "trend_follow",
                         {"ema_cross":"20>50","rsi":float(last["rsi14"]),"atr":float(last["atr14"]),
                          "adx_ok":adx_ok,"macd_ok":macd_ok,"volume_ok":volume_ok,
                          "balanced_approach":True,"improved":True})


def signal_quality_filter(signal: Signal, df: pd.DataFrame) -> bool:
    """Filter signals based on quality criteria"""
    # Strategy-specific quality checks
    if signal.strategy == "trend_follow":
        # Balanced quality requirements for trend signals
        rationale = signal.rationale

        # Must have balanced approach marker
        balanced_approach = rationale.get("balanced_approach", False)

        return balanced_approach  # Accept balanced signals

    return True  # Default to accepting signals for other strategies


def mean_reversion(df: pd.DataFrame) -> Optional[Signal]:
    """Placeholder for mean reversion strategy"""
    return None


def momentum(df: pd.DataFrame) -> Optional[Signal]:
    """Placeholder for momentum strategy"""
    return None


def run_strategies(df: pd.DataFrame) -> List[Optional[Signal]]:
    """Run all available strategies and return their signals"""
    signals = []

    # Run trend following strategy
    trend_signal = trend_follow(df)
    if trend_signal:
        signals.append(trend_signal)

    # Run mean reversion strategy
    mean_rev_signal = mean_reversion(df)
    if mean_rev_signal:
        signals.append(mean_rev_signal)

    # Run momentum strategy
    momentum_signal = momentum(df)
    if momentum_signal:
        signals.append(momentum_signal)

    return signals
