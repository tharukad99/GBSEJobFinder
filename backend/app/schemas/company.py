from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class CompanyBase(BaseModel):
    CompanyName: str
    WebsiteUrl: Optional[str] = None
    CareersUrl: Optional[str] = None
    Industry: Optional[str] = None
    SponsorLicenceStatus: str = "UNKNOWN"
    SponsorRoute: Optional[str] = None
    SponsorRating: Optional[str] = None

class CompanyResponse(CompanyBase):
    CompanyId: int
    NormalizedCompanyName: str
    SponsorVerifiedAt: Optional[datetime] = None
    CreatedAt: datetime
    UpdatedAt: datetime
    ActiveJobsCount: int = 0

    class Config:
        from_attributes = True

class CompanyListResponse(BaseModel):
    total: int
    items: List[CompanyResponse]
