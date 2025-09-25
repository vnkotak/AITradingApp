import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY/ANON_KEY")
    return create_client(url, key)


