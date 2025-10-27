from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI TradingApp API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_scanner_token(authorization: str | None = Header(default=None)):
    token = os.getenv("SCANNER_TOKEN")
    if token is None:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or value != token:
        raise HTTPException(status_code=403, detail="Invalid token")


class RunResponse(BaseModel):
    status: str
    mode: str
    run_id: str | None = None
    signals: int | None = None
    symbols_scanned: int | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


from apps.api.routes import router as api_router
app.include_router(api_router)
from apps.api.ai_endpoints import router as ai_router
app.include_router(ai_router)

@app.post("/scanner/run", response_model=RunResponse)
def run_scanner(mode: str, force: bool = False, _=Depends(verify_scanner_token)):
    if mode not in {"1m", "5m", "15m", "1d", "1h"}:
        raise HTTPException(status_code=400, detail="Invalid mode")
    from apps.api.scanner import scan_once
    result = scan_once(mode, force=force)
    return {
        "status": "completed",
        "mode": mode,
        "run_id": (result.get("run_id") if isinstance(result, dict) else None),
        "signals": (result.get("signals") if isinstance(result, dict) else None),
        "symbols_scanned": (result.get("symbols_scanned") if isinstance(result, dict) else None),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

