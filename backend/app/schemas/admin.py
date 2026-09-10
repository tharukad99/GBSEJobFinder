from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class SponsorshipOverrideRequest(BaseModel):
    sponsorship_status: str # CONFIRMED, MAY_OFFER, NO_SPONSORSHIP, UNKNOWN
    evidence_text: Optional[str] = "Manually adjusted by administrator."
    confidence_level: Optional[str] = "High"

class RefreshResponse(BaseModel):
    status: str
    message: str
    started_at: datetime
    results: List[Dict[str, Any]]
