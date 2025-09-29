import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

def get_client() -> Client | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        print("ERROR: Database not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        print("Current values:")
        print(f"  SUPABASE_URL: {url or 'NOT SET'}")
        print(f"  SUPABASE_SERVICE_KEY: {'SET' if key else 'NOT SET'}")
        return None
    return create_client(url, key)


