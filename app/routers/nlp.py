from fastapi import APIRouter, HTTPException, status
from app.models.schemas import HandleCompareRequest, HandleCompareResponse
from app.services.nlp_service import nlp_service

router = APIRouter(prefix="/nlp", tags=["NLP & Stylometry"])

@router.post("/compare", response_model=HandleCompareResponse)
def compare_authorship(payload: HandleCompareRequest):
    result = nlp_service.compare(
        handle_a=payload.handle_a,
        handle_b=payload.handle_b,
        text_a=payload.sample_text_a,
        text_b=payload.sample_text_b,
    )

    if "error" in result and result["similarity_score"] == 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    return HandleCompareResponse(
        handle_a=payload.handle_a,
        handle_b=payload.handle_b,
        similarity_score=result["similarity_score"],
        is_same_author=result["is_same_author"],
        confidence=result["confidence"],
        shared_linguistic_markers=result["shared_markers"],
        details={"threshold": result.get("threshold_used", 0.65)},
    )