from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import math
import pandas as pd


@dataclass
class ScoredSignal:
    action: str
    entry: float
    stop: float
    target: float | None
    confidence: float
    strategy: str
    rationale: Dict


def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _feature_contributions(df: pd.DataFrame) -> Dict[str, float]:
    last = df.iloc[-1]
    feats: Dict[str, float] = {}
    # Normalize some indicators to ~[-1,1]
    # RSI distance from mid (50) scaled
    rsi = float(last["rsi14"]) if pd.notna(last.get("rsi14")) else 50.0
    feats["rsi_bias"] = (rsi - 50.0) / 50.0  # -1..+1 approx
    # MACD histogram sign and magnitude
    macdh = float(last["macd_hist"]) if pd.notna(last.get("macd_hist")) else 0.0
    feats["macd_momentum"] = max(-1.0, min(1.0, macdh))
    # ADX trend strength scaled 0..1
    adx = float(last["adx14"]) if pd.notna(last.get("adx14")) else 0.0
    feats["trend_strength"] = max(0.0, min(1.0, adx / 50.0))
    # Price vs VWAP distance in ATRs
    if pd.notna(last.get("vwap")) and pd.notna(last.get("atr14")) and last["atr14"]:
        feats["vwap_premium_atr"] = float((last["close"] - last["vwap"]) / last["atr14"])
    else:
        feats["vwap_premium_atr"] = 0.0
    # Bollinger width regime (narrow/wide)
    bb_width = float(last["bb_width"]) if pd.notna(last.get("bb_width")) else 0.05
    feats["bb_regime"] = max(0.0, min(1.0, bb_width / 0.1))
    # Volume z-score (20)
    vol = df["volume"].rolling(20).mean()
    vol_z = (df["volume"] - vol) / (df["volume"].rolling(20).std() + 1e-9)
    v = vol_z.iloc[-1]
    feats["volume_z"] = float(v) if pd.notna(v) else 0.0
    return feats


def _sentiment_bias(ticker: str, exchange: str, lookback: int = 3) -> float:
    # Skip sentiment bias during backtesting and scanner to avoid database calls
    try:
        import inspect
        # Check if we're being called from backtest or scanner context
        frame = inspect.currentframe()
        while frame:
            filename = frame.f_code.co_filename.lower()
            if 'backtest' in filename or 'scanner' in filename:
                return 0.0
            frame = frame.f_back
    except:
        pass

    try:
        from supabase_client import get_client
        sb = get_client()
        sym = sb.table('symbols').select('id').eq('ticker', ticker).eq('exchange', exchange).single().execute().data
        if not sym:
            return 0.0
        data = sb.table('sentiment').select('score').eq('symbol_id', sym['id']).order('ts', desc=True).limit(10).execute().data
        if not data:
            return 0.0
        scores = [float(x['score']) for x in data][:lookback]
        return float(sum(scores) / max(1, len(scores)))
    except Exception:
        return 0.0


def score_signal(df: pd.DataFrame, action: str, base_conf: float, context: Dict | None = None) -> tuple[float, Dict]:
    feats = _feature_contributions(df)
    last = df.iloc[-1]
    contribs: Dict[str, float] = {}

    # Detect regime - Hull Suite is trend-following, so optimize for trends
    adx = feats.get("trend_strength", 0.0)
    macd = feats.get("macd_momentum", 0.0)
    trend_regime = "trend" if adx > 0.6 and abs(macd) > 0.2 else "range"

    # Dynamic weights based on market regime - favor trend-following for Hull
    if trend_regime == "range":
        w = {
            "rsi_bias": 0.6 if action == "BUY" else -0.5,  # Moderate RSI preference
            "macd_momentum": 0.5 if action == "BUY" else -0.6,  # MACD confirmation
            "trend_strength": -0.3,  # Slightly penalize weak trends in ranging markets
            "vwap_premium_atr": 0.25,
            "bb_regime": 0.4,  # Moderate volatility preference
            "volume_z": 0.3,
        }
    else:  # trend regime - optimize for Hull Suite trend-following
        w = {
            "rsi_bias": 0.3 if action == "BUY" else -0.3,  # Reduced RSI importance in trends
            "macd_momentum": 0.9 if action == "BUY" else -0.9,  # Strong MACD alignment with trend
            "trend_strength": 0.8,  # Reward strong trends (Hull's strength)
            "vwap_premium_atr": 0.4,  # Trend continuation signal
            "bb_regime": 0.2,  # Less emphasis on volatility in strong trends
            "volume_z": 0.6,  # Volume confirmation for trend moves
        }

    logits = base_conf * 1.2  # Reduced base multiplier for more conservative scoring

    # Compute contributions
    for k, weight in w.items():
        c = feats.get(k, 0.0) * weight
        contribs[k] = c
        logits += c

    # RSI extreme confirmation (but not primary signal)
    rsi = float(last.get("rsi14", 50))
    if action == "BUY" and rsi < 35:  # Only boost on extreme oversold in trends
        logits += 0.2
        contribs["rsi_extreme"] = 0.2
    elif action == "SELL" and rsi > 65:  # Only boost on extreme overbought in trends
        logits += 0.2
        contribs["rsi_extreme"] = 0.2

    # HMA trend alignment (Hull-specific confirmation) - DISABLED for now
    # The base Hull signal already includes HMA slope logic, so don't double-count
    pass

    # Sentiment bias (reduced importance for trend strategies)
    ticker = context.get("ticker") if context else None
    exchange = context.get("exchange") if context else None
    if ticker and exchange:
        s_bias = _sentiment_bias(ticker, exchange)
        logits += s_bias * (0.15 if action == "BUY" else -0.15)
        contribs["sentiment"] = s_bias * (0.15 if action == "BUY" else -0.15)

    # Compute final confidence
    conf = _sigmoid(logits)
    conf = float(max(0.0, min(1.0, conf)))
    rationale = {
        "base": base_conf,
        "regime": trend_regime,
        "features": feats,
        "contribs": contribs,
    }
    return conf, rationale


def ensemble(signals: List[ScoredSignal], strategy_weights: Dict[str, float] | None = None) -> Dict:
    if not signals:
        return {"decision": "PASS", "weights": {}}
    # Group by action and take weighted vote by confidence
    weights: Dict[str, float] = {}
    for s in signals:
        w = s.confidence
        if strategy_weights and s.strategy in strategy_weights:
            w *= float(strategy_weights[s.strategy])
        weights[s.action] = weights.get(s.action, 0.0) + w
    decision = max(weights.items(), key=lambda kv: kv[1])[0]
    return {"decision": decision, "weights": weights}


