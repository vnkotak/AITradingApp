from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def add_core_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Moving averages
    out["ema20"] = ta.ema(out["close"], length=20)
    out["ema50"] = ta.ema(out["close"], length=50)
    # RSI
    out["rsi14"] = ta.rsi(out["close"], length=14)
    # MACD
    macd = ta.macd(out["close"], fast=12, slow=26, signal=9)
    out["macd"] = macd["MACD_12_26_9"]
    out["macd_signal"] = macd["MACDs_12_26_9"]
    out["macd_hist"] = macd["MACDh_12_26_9"]
    # Bollinger Bands
    bb = ta.bbands(out["close"], length=20, std=2.0)
    out["bb_lower"] = bb["BBL_20_2.0"]
    out["bb_mid"] = bb["BBM_20_2.0"]
    out["bb_upper"] = bb["BBU_20_2.0"]
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_mid"]
    # ATR
    out["atr14"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    # ADX
    out["adx14"] = ta.adx(out["high"], out["low"], out["close"], length=14)["ADX_14"]
    # VWAP (requires typical price and cumulative volume calc)
    try:
        out["vwap"] = ta.vwap(out["high"], out["low"], out["close"], out["volume"])  # type: ignore
    except Exception:
        out["vwap"] = pd.NA
    return out


