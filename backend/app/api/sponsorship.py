from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from backend.app.services.sponsor_register_service import sponsor_register

router = APIRouter(prefix="/sponsorship", tags=["Sponsorship"])

@router.get("/lookup")
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
