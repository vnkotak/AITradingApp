from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def add_core_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Ensure ordered DatetimeIndex for TA functions that require it (e.g., VWAP)
    had_index = False
    if "ts" in out.columns:
        try:
            out["ts"] = pd.to_datetime(out["ts"], utc=True)
            # set index to 'ts' and drop the column to avoid duplicates on reset
            out = out.set_index("ts", drop=True).sort_index()
            had_index = True
        except Exception:
            had_index = False
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
    try:
        bb = ta.bbands(out["close"], length=20, std=2.0)
        # Some pandas-ta versions use different column keys; detect dynamically
        if bb is not None and not bb.empty:
            lower_key = next((c for c in bb.columns if str(c).startswith("BBL_")), None)
            mid_key = next((c for c in bb.columns if str(c).startswith("BBM_")), None)
            upper_key = next((c for c in bb.columns if str(c).startswith("BBU_")), None)
            if lower_key and mid_key and upper_key:
                out["bb_lower"] = bb[lower_key]
                out["bb_mid"] = bb[mid_key]
                out["bb_upper"] = bb[upper_key]
            else:
                raise KeyError("BB columns missing")
        else:
            raise KeyError("BB empty")
    except Exception:
        # Manual fallback
        mid = out["close"].rolling(20).mean()
        std = out["close"].rolling(20).std()
        out["bb_mid"] = mid
        out["bb_lower"] = mid - 2.0 * std
        out["bb_upper"] = mid + 2.0 * std
    # width (avoid divide-by-zero)
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / (out["bb_mid"].replace(0, pd.NA))
    # ATR
    out["atr14"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    # ADX
    out["adx14"] = ta.adx(out["high"], out["low"], out["close"], length=14)["ADX_14"]
    # VWAP (requires ordered DatetimeIndex). Compute or fallback to manual.
    try:
        vwap = ta.vwap(out["high"], out["low"], out["close"], out["volume"])  # type: ignore
        out["vwap"] = vwap
    except Exception:
        try:
            tp = (out["high"].astype(float) + out["low"].astype(float) + out["close"].astype(float)) / 3.0
            vol = out["volume"].astype(float).fillna(0.0)
            cum_pv = (tp * vol).cumsum()
            cum_v = vol.cumsum().replace(0, pd.NA)
            out["vwap"] = cum_pv / cum_v
        except Exception:
            out["vwap"] = pd.NA
    # Restore original index if we changed it
    if had_index:
        out = out.reset_index()  # index name 'ts' becomes a 'ts' column
    return out


