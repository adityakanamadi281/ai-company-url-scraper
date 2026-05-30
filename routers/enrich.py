from __future__ import annotations
from fastapi import APIRouter, HTTPException
from models import EnrichRequest, CompanyProfile
from pipeline import enrich_company
from database import save_company

router = APIRouter()


@router.post("/enrich", response_model=CompanyProfile)
async def enrich(request: EnrichRequest) -> CompanyProfile:
    url = request.url
    if not url:
        raise HTTPException(status_code=422, detail="URL is required.")

    try:
        data = await enrich_company(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {e}")

    try:
        record_id = await save_company(url, data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database save failed: {e}")

    return CompanyProfile(id=record_id, url=url, **data)
