import os
from typing import List, Optional, Dict, Any
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.postgres import get_db
from app.models.sql_models import Actor, DarkWebHandle, Wallet, Observation, ScanTarget
from app.routers.auth import get_current_user
from app.config import settings
from app.services.observation_scope import build_observation_target_keys

router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(get_current_user)])
GEMINI_MODEL = settings.GEMINI_MODEL

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    actor_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list, max_length=12)

def _actor_context(actor_id: Optional[str], db: Session) -> Dict[str, Any]:
    if not actor_id:
        return {"scope": "global", "note": "No actor is currently selected. Answer only from the platform context provided."}
    actor = db.query(Actor).filter(func.lower(Actor.actor_id) == actor_id.lower()).first()
    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")
    handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
    wallets = db.query(Wallet).filter(Wallet.actor_id == actor.actor_id).all()
    targets = db.query(ScanTarget).filter(ScanTarget.actor_id == actor.actor_id).all()
    handle_names = [h.handle for h in handles]
    target_keys = build_observation_target_keys(
        actor.actor_id,
        actor.primary_handle,
        handles,
        targets,
    )
    observations = (
        db.query(Observation)
        .filter(
            func.lower(Observation.target).in_(target_keys),
            Observation.detected.is_(True),
        )
        .order_by(Observation.timestamp.desc())
        .limit(60)
        .all()
    )
    return {
        "scope": "actor",
        "actor": {
            "actor_id": actor.actor_id,
            "primary_handle": actor.primary_handle,
            "risk_category": actor.risk_category,
            "confidence_score": actor.confidence_score,
            "priority_score": actor.priority_score,
            "handles": handle_names,
            "wallets": [w.address for w in wallets],
            "marketplaces": sorted({h.platform for h in handles if h.platform}),
            "pgp_keys": sorted({key.fingerprint for h in handles for key in getattr(h, "pgp_keys", []) if key.fingerprint}),
            "scan_targets": [t.target_url or t.name for t in targets if t.target_url or t.name],
            "evidence": [{
                "id": o.observation_id,
                "indicator_type": o.indicator_type,
                "value": o.value,
                "target": o.target,
                "source": o.source,
                "confidence": o.confidence,
                "timestamp": o.timestamp.isoformat() if o.timestamp else None,
                "description": o.description,
            } for o in observations[:30]],
        },
    }

def _call_gemini(prompt: str, history: List[ChatMessage]) -> str:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini is not configured. Set GEMINI_API_KEY on the backend.")
    contents = []
    for item in history[-6:]:
        role = "model" if item.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": item.content[:4000]}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": contents,
                "systemInstruction": {"parts": [{"text": "You are DeCypher Copilot, an investigation assistant inside a dark-web threat-intelligence platform. Use ONLY the supplied DeCypher context. Never invent actors, identifiers, evidence, relationships, sources, or attribution conclusions. Clearly separate documented evidence from inference and unknowns. Treat confidence and priority as platform-derived scores, not proof of identity. Prefer concise investigator-friendly answers with bullets. If the context does not support an answer, say so."}]},
                "generationConfig": {"temperature": 0.15, "maxOutputTokens": 900},
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {exc}") from exc
    if not response.ok:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {response.text[:500]}")
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Gemini returned an empty response.")

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    context = _actor_context(request.actor_id, db)
    prompt = "DeCypher context (authoritative for this answer):\n" + str(context) + "\n\nUser question:\n" + request.message
    answer = _call_gemini(prompt, request.history)
    return {"answer": answer, "provider": "gemini", "model": GEMINI_MODEL, "scope": context.get("scope"), "actor_id": request.actor_id}
