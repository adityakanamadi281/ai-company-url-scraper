from __future__ import annotations
from fastapi import APIRouter
from models import CompanyProfile
from database import fetch_all_companies

router = APIRouter()


@router.get("/results", response_model=list[CompanyProfile])
async def results() -> list[CompanyProfile]:
    rows = await fetch_all_companies()
    return [CompanyProfile(**row) for row in rows]
