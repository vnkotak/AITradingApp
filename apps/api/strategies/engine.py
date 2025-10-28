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

def mean_reversion(df: pd.DataFrame, current_index: int = -1) -> Optional[Signal]:
    """Mean Reversion Strategy with Bollinger Bands and RSI"""
    if len(df) < 30:  # Need enough data for indicators
        return None

    if current_index >= 0 and current_index < len(df):
        last = df.iloc[current_index]
    else:
        last = df.iloc[-1]

    # Require all indicators
    if not (pd.notna(last.get("close")) and pd.notna(last.get("rsi14")) and
            pd.notna(last.get("bb_lower")) and pd.notna(last.get("bb_upper")) and
            pd.notna(last.get("atr14"))):
        return None

    price_ok = 10 <= last["close"] <= 10000

    # BUY: Price below lower BB and RSI > 42 (dipping but not oversold)
    buy_signal = last["close"] < last["bb_lower"] and last["rsi14"] > 42 and price_ok

    # SELL: Price above upper BB and RSI > 70 (overbought)
    sell_signal = last["close"] > last["bb_upper"] and last["rsi14"] > 70

    if buy_signal:
        entry = float(last["close"])

        # Fixed 3% stop loss
        stop = float(entry * 0.97)

        # Target for 2:1 risk-reward
        risk = entry - stop
        target = float(entry + 2 * risk)

        # Base confidence
        confidence = 0.75

        # Bonus for deeper dips
        bb_distance = (last["bb_lower"] - last["close"]) / last["close"]
        if bb_distance > 0.02:
            confidence += 0.1

        # Bonus for RSI in moderate zone
        if 45 <= last["rsi14"] <= 55:
            confidence += 0.1

        confidence = min(0.95, confidence)

        return Signal("BUY", entry, stop, target, confidence, "mean_reversion",
                     {"rsi": float(last["rsi14"]), "bb_lower": float(last["bb_lower"]),
                      "bb_distance": bb_distance, "atr": float(last["atr14"])})


def signal_quality_filter(signal: Signal, df: pd.DataFrame) -> bool:
    """Filter signals based on quality criteria"""
    return True  # Accept all signals for now


def smma(src: pd.Series, length: int) -> pd.Series:
    """Smoothed Moving Average (SMMA) calculation - like in Pine Script"""
    smma_values = []
    for i in range(len(src)):
        if i < length - 1:
            smma_values.append(pd.NA)
        elif i == length - 1:
            # First SMMA value is SMA
            smma_values.append(src.iloc[:length].mean())
        else:
            # SMMA formula: (previous SMMA * (length - 1) + current src) / length
            prev_smma = smma_values[-1]
            current = src.iloc[i]
            new_smma = (prev_smma * (length - 1) + current) / length
            smma_values.append(new_smma)
    return pd.Series(smma_values, index=src.index)


def alligator(df: pd.DataFrame, current_index: int = -1) -> Optional[Signal]:
    """Alligator Strategy with ATR Stop-Loss - Based on TradingView Pine Script"""
    if len(df) < 50:  # Need enough data for indicators
        return None

    if current_index >= 0 and current_index < len(df):
        last = df.iloc[current_index]
        if current_index > 0:
            prev = df.iloc[current_index - 1]
        else:
            return None  # Need at least 2 data points
    else:
        last = df.iloc[-1]
        prev = df.iloc[-2]

    # Require basic price data and ATR
    if not (pd.notna(last.get("close")) and pd.notna(last.get("high")) and
            pd.notna(last.get("low")) and pd.notna(last.get("atr14"))):
        return None

    price_ok = 10 <= last["close"] <= 10000

    # Calculate Alligator lines using SMMA on hl2
    hl2 = (df["high"] + df["low"]) / 2

    # Calculate SMMA lines
    df_copy = df.copy()
    df_copy["jaw"] = smma(hl2, 13)
    df_copy["teeth"] = smma(hl2, 8)
    df_copy["lips"] = smma(hl2, 5)

    if current_index >= 0 and current_index < len(df_copy):
        last = df_copy.iloc[current_index]
        prev = df_copy.iloc[current_index - 1]
    else:
        last = df_copy.iloc[-1]
        prev = df_copy.iloc[-2]

    # Check if we have enough SMMA data
    if pd.isna(last.get("jaw")) or pd.isna(last.get("teeth")) or pd.isna(last.get("lips")) or \
       pd.isna(prev.get("jaw")) or pd.isna(prev.get("teeth")) or pd.isna(prev.get("lips")):
        return None

    # Trading conditions from Pine Script
    long_condition = (prev["lips"] <= prev["jaw"]) and (last["lips"] > last["jaw"])
    exit_condition = (prev["lips"] >= prev["jaw"]) and (last["lips"] < last["jaw"])

    if long_condition and price_ok:
        entry = float(last["close"])

        # ATR-based stop-loss: entry - (atrMult * atrValue)
        atr_mult = 2.0  # From Pine Script
        atr_value = float(last["atr14"])
        stop = float(entry - atr_mult * atr_value)

        # No target - only stop-loss exit (like Pine Script)
        target = float(entry + atr_mult * atr_value * 3)  # Conservative target

        confidence = 0.75  # Balanced confidence

        return Signal("BUY", entry, stop, target, confidence, "alligator",
                     {"jaw": float(last["jaw"]), "teeth": float(last["teeth"]),
                      "lips": float(last["lips"]), "atr": atr_value, "atr_mult": atr_mult})

    elif exit_condition and price_ok:
        # For exit signals, we could return a SELL signal
        entry = float(last["close"])
        stop = float(entry + 2.0 * float(last["atr14"]))  # Symmetric stop for shorts
        target = float(entry - 2.0 * float(last["atr14"]) * 3)

        confidence = 0.7

        return Signal("SELL", entry, stop, target, confidence, "alligator",
                     {"jaw": float(last["jaw"]), "teeth": float(last["teeth"]),
                      "lips": float(last["lips"]), "atr": float(last["atr14"])})

    return None


def hull_suite(df: pd.DataFrame, current_index: int = -1) -> Optional[Signal]:
    """Hull Suite Strategy - Slope-based trend following with HMA"""
    if len(df) < 60:  # Need enough data for HMA
        return None

    if current_index >= 0 and current_index < len(df):
        last = df.iloc[current_index]
        if current_index >= 2:
            prev_2 = df.iloc[current_index - 2]
        else:
            return None  # Need at least 3 data points for comparison
    else:
        last = df.iloc[-1]
        prev_2 = df.iloc[-3]  # HULL[2] means 2 periods back

    # Require HMA indicator
    if not (pd.notna(last.get("close")) and pd.notna(last.get("hma55")) and
            pd.notna(prev_2.get("hma55")) and pd.notna(last.get("atr14"))):
        return None

    price_ok = 10 <= last["close"] <= 10000

    # Core Hull Suite logic: slope-based trend detection
    # BUY: HULL > HULL[2] (current HMA > HMA 2 periods ago = uptrend)
    # SELL: HULL < HULL[2] (current HMA < HMA 2 periods ago = downtrend)

    if last["hma55"] > prev_2["hma55"] and price_ok:
        # Uptrend detected - BUY signal
        entry = float(last["close"])
        # ATR-based stop-loss (more conservative than Alligator)
        atr_mult = 1.5  # Less aggressive than Alligator's 2.0
        atr_value = float(last["atr14"])
        stop = float(entry - atr_mult * atr_value)
        # 3:1 risk-reward ratio
        risk = entry - stop
        target = float(entry + 3 * risk)

        confidence = 0.8  # High confidence for trend-following

        return Signal("BUY", entry, stop, target, confidence, "hull_suite",
                     {"hma_current": float(last["hma55"]), "hma_prev": float(prev_2["hma55"]),
                      "hma_slope": float(last["hma55"] - prev_2["hma55"]), "atr": atr_value,
                      "trend": "bullish"})

    elif last["hma55"] < prev_2["hma55"] and price_ok:
        # Downtrend detected - SELL signal
        entry = float(last["close"])
        # ATR-based stop-loss for shorts
        atr_mult = 1.5
        atr_value = float(last["atr14"])
        stop = float(entry + atr_mult * atr_value)
        # 3:1 risk-reward ratio
        risk = stop - entry
        target = float(entry - 3 * risk)

        confidence = 0.8

        return Signal("SELL", entry, stop, target, confidence, "hull_suite",
                     {"hma_current": float(last["hma55"]), "hma_prev": float(prev_2["hma55"]),
                      "hma_slope": float(last["hma55"] - prev_2["hma55"]), "atr": atr_value,
                      "trend": "bearish"})

    return None


def macd_trend(df: pd.DataFrame, current_index: int = -1) -> Optional[Signal]:
    """MACD Trend Following Strategy - Based on TradingView Pine Script"""
    if len(df) < 200:  # Need enough data for 200-period MA
        return None

    if current_index >= 0 and current_index < len(df):
        last = df.iloc[current_index]
        if current_index > 0:
            prev = df.iloc[current_index - 1]
        else:
            return None  # Need at least 2 data points
    else:
        last = df.iloc[-1]
        prev = df.iloc[-2]

    # Require MACD indicators and 200-period MA
    if not (pd.notna(last.get("close")) and pd.notna(last.get("macd")) and
            pd.notna(last.get("macd_signal")) and pd.notna(last.get("macd_hist")) and
            pd.notna(last.get("atr14"))):
        return None

    # Calculate required MAs manually
    df_copy = df.copy()
    df_copy["fastMA"] = df_copy["close"].rolling(12).mean()
    df_copy["slowMA"] = df_copy["close"].rolling(26).mean()
    df_copy["veryslowMA"] = df_copy["close"].rolling(200).mean()

    if current_index >= 0 and current_index < len(df_copy):
        last = df_copy.iloc[current_index]
        prev = df_copy.iloc[current_index - 1]
    else:
        last = df_copy.iloc[-1]
        prev = df_copy.iloc[-2]

    price_ok = 10 <= last["close"] <= 10000

    # MACD histogram crossover conditions
    hist_cross_above = (prev["macd_hist"] <= 0) and (last["macd_hist"] > 0)
    hist_cross_below = (prev["macd_hist"] >= 0) and (last["macd_hist"] < 0)

    # Trend alignment conditions
    bullish_trend = (last["macd"] > 0 and last["fastMA"] > last["slowMA"] and
                    last["close"] > last["veryslowMA"])
    bearish_trend = (last["macd"] < 0 and last["fastMA"] < last["slowMA"] and
                    last["close"] < last["veryslowMA"])

    if hist_cross_above and bullish_trend and price_ok:
        entry = float(last["close"])
        stop = float(entry * 0.97)  # 3% stop loss
        risk = entry - stop
        target = float(entry + 2 * risk)  # 2:1 reward

        confidence = 0.8  # High confidence for this strategy

        return Signal("BUY", entry, stop, target, confidence, "macd_trend",
                     {"macd": float(last["macd"]), "macd_hist": float(last["macd_hist"]),
                      "fastMA": float(last["fastMA"]), "slowMA": float(last["slowMA"]),
                      "veryslowMA": float(last["veryslowMA"]), "trend": "bullish"})

    elif hist_cross_below and bearish_trend and price_ok:
        entry = float(last["close"])
        stop = float(entry * 1.03)  # 3% stop loss for shorts
        risk = stop - entry
        target = float(entry - 2 * risk)  # 2:1 reward

        confidence = 0.8

        return Signal("SELL", entry, stop, target, confidence, "macd_trend",
                     {"macd": float(last["macd"]), "macd_hist": float(last["macd_hist"]),
                      "fastMA": float(last["fastMA"]), "slowMA": float(last["slowMA"]),
                      "veryslowMA": float(last["veryslowMA"]), "trend": "bearish"})

    return None


def momentum(df: pd.DataFrame) -> Optional[Signal]:
    """Placeholder for momentum strategy"""
    return None


def run_strategies(df: pd.DataFrame) -> List[Optional[Signal]]:
    """Run all available strategies and return their signals"""
    signals = []

    # Run mean reversion strategy
    # mean_rev_signal = mean_reversion(df)
    # if mean_rev_signal:
    #     signals.append(mean_rev_signal)

    # Run MACD trend strategy
    # macd_signal = macd_trend(df)
    # if macd_signal:
    #     signals.append(macd_signal)

    # Run Hull Suite strategy (replacing Alligator)
    hull_signal = hull_suite(df)
    if hull_signal:
        signals.append(hull_signal)

    return signals
