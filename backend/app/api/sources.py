from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.app.database.session import get_db
from backend.app.models.source import JobSource
from backend.app.models.job import Job
from backend.app.models.scrape_run import ScrapeRun
from backend.app.schemas.source import JobSourceResponse, ScrapeRunResponse

router = APIRouter(prefix="/sources", tags=["Sources"])

@router.get("", response_model=List[JobSourceResponse])
def get_sources(db: Session = Depends(get_db)):
    sources = db.query(JobSource).all()
    job_counts = dict(
        db.query(Job.SourceId, func.count(Job.JobId))
        .group_by(Job.SourceId)
        .all()
    )

    results = []
    for s in sources:
        results.append(JobSourceResponse(
            SourceId=s.SourceId,
            SourceName=s.SourceName,
            SourceType=s.SourceType,
            BaseUrl=s.BaseUrl,
            ProviderName=s.ProviderName,
            ConfigJson=s.ConfigJson,
            IsEnabled=s.IsEnabled,
            LastSuccessfulRun=s.LastSuccessfulRun,
            CreatedAt=s.CreatedAt,
            UpdatedAt=s.UpdatedAt,
            TotalJobsCount=job_counts.get(s.SourceId, 0)
        ))
    return results

@router.get("/runs", response_model=List[ScrapeRunResponse])
def get_scrape_runs(limit: int = 20, db: Session = Depends(get_db)):
    runs = (
        db.query(ScrapeRun)
        .outerjoin(JobSource, JobSource.SourceId == ScrapeRun.SourceId)
        .order_by(desc(ScrapeRun.StartedAt))
        .limit(limit)
        .all()
    )
    
    results = []
    for r in runs:
        results.append(ScrapeRunResponse(
            ScrapeRunId=r.ScrapeRunId,
            SourceId=r.SourceId,
            SourceName=r.source.SourceName if r.source else "Manual / All",
            StartedAt=r.StartedAt,
            CompletedAt=r.CompletedAt,
            JobsFound=r.JobsFound,
            JobsAdded=r.JobsAdded,
            JobsUpdated=r.JobsUpdated,
            DuplicatesFound=r.DuplicatesFound,
            JobsRejected=r.JobsRejected,
            Status=r.Status,
            ErrorMessage=r.ErrorMessage
        ))
    return results
