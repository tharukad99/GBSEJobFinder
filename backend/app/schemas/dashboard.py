from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class LocationBreakdown(BaseModel):
    name: str
    count: int

class SponsorshipBreakdown(BaseModel):
    confirmed: int
    may_offer: int
    no_sponsorship: int
    unknown: int

class DashboardStatsResponse(BaseModel):
    total_active_jobs: int
    new_jobs_today: int
    new_jobs_last_7_days: int
    confirmed_sponsorship_jobs: int
    may_offer_sponsorship_jobs: int
    applied_jobs: int = 0
    london_jobs: int
    manchester_jobs: int
    remote_uk_jobs: int
    hybrid_jobs: int
    last_refresh_time: Optional[datetime] = None
    next_refresh_time: Optional[datetime] = None
    total_companies: int
    total_licensed_sponsors: int
    sponsorship_breakdown: SponsorshipBreakdown
    top_skills: List[Dict[str, Any]]
