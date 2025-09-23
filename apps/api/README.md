# API Service (FastAPI)

Run locally:

```
pip install -r apps/api/requirements.txt
uvicorn apps.api.main:app --reload --port 8000
```

Env vars:
- SCANNER_TOKEN (optional for protecting /scanner/run)
- SUPABASE_URL, SUPABASE_SERVICE_KEY (for data access when implemented)


