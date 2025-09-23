from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel
import os

app = FastAPI(title="AITradingApp API", version="0.1.0")


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


@app.get("/health")
def health():
    return {"status": "ok"}


from .routes import router as api_router
app.include_router(api_router)
from .ai_endpoints import router as ai_router
app.include_router(ai_router)

@app.post("/scanner/run", response_model=RunResponse)
def run_scanner(mode: str, _=Depends(verify_scanner_token)):
    if mode not in {"1m", "5m", "15m"}:
        raise HTTPException(status_code=400, detail="Invalid mode")
    from .scanner import scan_once
    result = scan_once(mode)
    return {"status": "completed", "mode": mode}


