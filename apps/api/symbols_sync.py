import json
from supabase_client import get_client


def sync_symbols_from_seed(path: str = "apps/api/symbols_seed.json") -> int:
    sb = get_client()
    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)
    upserts = []
    for it in items:
        upserts.append({
            "ticker": it["ticker"],
            "exchange": it["exchange"],
            "name": it.get("name"),
            "sector": it.get("sector"),
            "is_fno": it.get("is_fno", False),
            "lot_size": it.get("lot_size"),
            "is_active": True,
        })
    if upserts:
        sb.table("symbols").upsert(upserts, on_conflict="ticker,exchange").execute()
    return len(upserts)


if __name__ == "__main__":
    n = sync_symbols_from_seed()
    print(f"Synced {n} symbols")


