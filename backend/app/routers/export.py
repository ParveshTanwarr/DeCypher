from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
import pandas as pd
import io
from app.routers.actors import MOCK_ACTORS

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/json")
def export_json():
    return JSONResponse(content=[actor.model_dump() for actor in MOCK_ACTORS])

@router.get("/csv")
def export_csv():
    records = []
    for a in MOCK_ACTORS:
        records.append({
            "actor_id": a.actor_id,
            "primary_handle": a.primary_handle,
            "risk_category": a.risk_category,
            "confidence_score": a.confidence_score,
            "handles_count": len(a.handles),
            "wallets_count": len(a.wallets)
        })
    df = pd.DataFrame(records)

    stream = io.StringIO()
    df.to_csv(stream, index=False)

    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=threat_actors.csv"}
    )