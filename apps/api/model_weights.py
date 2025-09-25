from __future__ import annotations

from typing import Dict
from apps.api.supabase_client import get_client


def get_latest_strategy_weights(defaults: Dict[str, float] | None = None) -> Dict[str, float]:
    sb = get_client()
    model = sb.table('ai_models').select('params').order('created_at', desc=True).limit(1).execute().data
    if not model:
        return defaults or {}
    params = model[0].get('params') or {}
    return params.get('weights') or defaults or {}


