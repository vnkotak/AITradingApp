from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from apps.api.supabase_client import get_client

router = APIRouter()


class RegisterModel(BaseModel):
  version: str
  params: Dict
  metrics: Dict | None = None
  notes: str | None = None


@router.get('/ai/models/latest')
def ai_latest():
  sb = get_client()
  data = sb.table('ai_models').select('*').order('created_at', desc=True).limit(1).execute().data
  if not data:
    raise HTTPException(status_code=404, detail='No model')
  return data[0]


@router.post('/ai/models/register')
def ai_register(payload: RegisterModel):
  sb = get_client()
  row = sb.table('ai_models').insert({
    'version': payload.version,
    'params': payload.params,
    'metrics': payload.metrics,
    'notes': payload.notes,
  }).execute().data[0]
  return row


