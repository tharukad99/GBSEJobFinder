from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel

class SkillItem(BaseModel):
    SkillId: int
    SkillName: str
    NormalizedSkillName: str
    RequiredOrPreferred: str

    class Config:
        from_attributes = True

class SponsorshipEvidenceSchema(BaseModel):
    SponsorshipEvidenceId: int
    SponsorshipStatus: str
    EvidenceText: Optional[str] = None
    EvidenceUrl: Optional[str] = None
    EvidenceSource: Optional[str] = None
    ConfidenceLevel: str
    VerifiedAt: datetime

    class Config:
        from_attributes = True

class CompanySummary(BaseModel):
    CompanyId: int
    CompanyName: str
    WebsiteUrl: Optional[str] = None
    CareersUrl: Optional[str] = None
    SponsorLicenceStatus: str
    SponsorRoute: Optional[str] = None
    SponsorRating: Optional[str] = None

    class Config:
        from_attributes = True

class JobListItem(BaseModel):
    JobId: int
    ExternalJobId: Optional[str] = None
    Title: str
    NormalizedTitle: str
    Location: str
    City: Optional[str] = None
    Region: Optional[str] = None
    Country: str
    RemoteType: str
    EmploymentType: Optional[str] = None
    SalaryText: Optional[str] = None
    SalaryMin: Optional[float] = None
    SalaryMax: Optional[float] = None
    ExperienceLevel: Optional[str] = None
    SourceJobUrl: str
    CompanyCareerUrl: Optional[str] = None
    ApplyUrl: str
    IsApplied: bool = False
    AppliedAt: Optional[datetime] = None
    PostedDate: Optional[datetime] = None
    LastVerifiedAt: datetime
    JobStatus: str
    MatchScore: int
    QualityScore: int
    Company: CompanySummary
    Sponsorship: Optional[SponsorshipEvidenceSchema] = None
    Skills: List[SkillItem] = []

    class Config:
        from_attributes = True

class JobDetail(JobListItem):
    Description: Optional[str] = None
    FirstSeenAt: datetime
    LastSeenAt: datetime
    ClosingDate: Optional[datetime] = None
    DuplicateHash: Optional[str] = None

    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[JobListItem]

class ToggleAppliedRequest(BaseModel):
    IsApplied: Optional[bool] = None

class ToggleAppliedResponse(BaseModel):
    JobId: int
    IsApplied: bool
    AppliedAt: Optional[datetime] = None
    Message: str
