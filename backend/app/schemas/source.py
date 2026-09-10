from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class JobSourceBase(BaseModel):
    SourceName: str
    SourceType: str
    BaseUrl: Optional[str] = None
    ProviderName: str
    ConfigJson: Optional[str] = None
    IsEnabled: bool = True

class JobSourceUpdate(BaseModel):
    SourceName: Optional[str] = None
    IsEnabled: Optional[bool] = None
    ConfigJson: Optional[str] = None

class JobSourceResponse(JobSourceBase):
    SourceId: int
    LastSuccessfulRun: Optional[datetime] = None
    CreatedAt: datetime
    UpdatedAt: datetime
    TotalJobsCount: int = 0

    class Config:
        from_attributes = True

class ScrapeRunResponse(BaseModel):
    ScrapeRunId: int
    SourceId: Optional[int] = None
    SourceName: Optional[str] = None
    StartedAt: datetime
    CompletedAt: Optional[datetime] = None
    JobsFound: int
    JobsAdded: int
    JobsUpdated: int
    DuplicatesFound: int
    JobsRejected: int
    Status: str
    ErrorMessage: Optional[str] = None

    class Config:
        from_attributes = True
