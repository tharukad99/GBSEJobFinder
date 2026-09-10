from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from backend.app.database.config import settings
from backend.app.services.sponsor_register_service import sponsor_register
from backend.app.utils.rate_limiter import rate_limit

router = APIRouter(prefix="/sponsorship", tags=["Sponsorship"])

@router.get(
    "/lookup",
    dependencies=[Depends(rate_limit(max_requests=settings.RATE_LIMIT_LOOKUP_PER_MINUTE, window_seconds=60, bucket_name="sponsorship_lookup"))]
)
def lookup_company_sponsor_status(company: str = Query(..., description="Company name to look up in the UK sponsor register")):
    result = sponsor_register.lookup_company(company)
    if result:
        return {
            "found": True,
            "company_name": result["name"],
            "route": result["route"],
            "rating": result["rating"],
            "town": result.get("town", "UK"),
            "status": "LICENSED"
        }
    return {
        "found": False,
        "company_name": company,
        "status": "UNKNOWN",
        "message": "Company not found in current UK Home Office licensed sponsor register."
    }
