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
    try:
        from .supabase_client import get_client
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
    # Simple linear blend; weights chosen heuristically
    w = {
        "rsi_bias": 0.8 if action == "BUY" else -0.8,
        "macd_momentum": 0.7 if action == "BUY" else -0.7,
        "trend_strength": 0.5,
        "vwap_premium_atr": -0.6 if action == "BUY" else 0.6,
        "bb_regime": 0.2,
        "volume_z": 0.3,
    }
    logits = base_conf * 1.5
    contribs: Dict[str, float] = {}
    for k, weight in w.items():
        c = feats.get(k, 0.0) * weight
        contribs[k] = c
        logits += c
    # Sentiment bias
    ticker = context.get('ticker') if context else None
    exchange = context.get('exchange') if context else None
    if ticker and exchange:
        s_bias = _sentiment_bias(ticker, exchange)
        logits += s_bias * (0.3 if action == 'BUY' else -0.3)
        contribs['sentiment'] = s_bias * (0.3 if action == 'BUY' else -0.3)
    conf = _sigmoid(logits)
    # Clamp and round
    conf = float(max(0.0, min(1.0, conf)))
    rationale = {"base": base_conf, "features": feats, "contribs": contribs}
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


