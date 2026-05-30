from __future__ import annotations
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional


class EnrichRequest(BaseModel):
    url: str
    name: str = ""

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith("http"):
            v = "https://" + v
        return v


class CompanyProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    url: str = ""
    website_name: str = ""
    company_name: str = ""
    address: str = ""
    mobile_number: str = ""
    mail: list[str] = []
    core_service: str = ""
    target_customer: str = ""
    probable_pain_point: str = ""
    outreach_opener: str = ""
    created_at: str = ""
