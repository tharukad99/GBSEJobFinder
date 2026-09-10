from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.app.database.session import get_db
from backend.app.models.source import JobSource
from backend.app.models.job import Job
from backend.app.models.scrape_run import ScrapeRun
from backend.app.schemas.source import JobSourceResponse, ScrapeRunResponse
from backend.app.services.job_service import JobService

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

@router.get("/monitor")
def get_monitor_status(db: Session = Depends(get_db)):
    from backend.app.scheduler.job_scheduler import scheduler
    from backend.app.database.config import settings
    
    # Scheduler runtime info
    is_running = scheduler.running if scheduler else False
    registered_jobs = []
    next_run_time = None
    if scheduler and is_running:
        for job in scheduler.get_jobs():
            next_t = job.next_run_time
            if next_t and (next_run_time is None or next_t < next_run_time):
                next_run_time = next_t
            registered_jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": next_t.isoformat() if next_t else None,
                "trigger": str(job.trigger)
            })

    # Metric counts
    total_runs = db.query(ScrapeRun).count()
    success_runs = db.query(ScrapeRun).filter(ScrapeRun.Status == "SUCCESS").count()
    failed_runs = db.query(ScrapeRun).filter(ScrapeRun.Status == "FAILED").count()
    running_runs = db.query(ScrapeRun).filter(ScrapeRun.Status == "RUNNING").count()
    
    total_jobs_added = db.query(func.sum(ScrapeRun.JobsAdded)).scalar() or 0
    total_jobs_updated = db.query(func.sum(ScrapeRun.JobsUpdated)).scalar() or 0
    total_duplicates = db.query(func.sum(ScrapeRun.DuplicatesFound)).scalar() or 0

    latest_run = db.query(ScrapeRun).order_by(desc(ScrapeRun.StartedAt)).first()

    # Recent 30 execution records
    recent_runs_db = (
        db.query(ScrapeRun)
        .outerjoin(JobSource, JobSource.SourceId == ScrapeRun.SourceId)
        .order_by(desc(ScrapeRun.StartedAt))
        .limit(30)
        .all()
    )
    recent_runs = [
        {
            "ScrapeRunId": r.ScrapeRunId,
            "SourceId": r.SourceId,
            "SourceName": r.source.SourceName if r.source else "All Feeds (Auto-Scheduler)",
            "StartedAt": r.StartedAt.isoformat() if r.StartedAt else None,
            "CompletedAt": r.CompletedAt.isoformat() if r.CompletedAt else None,
            "DurationSeconds": round((r.CompletedAt - r.StartedAt).total_seconds(), 2) if r.CompletedAt and r.StartedAt else None,
            "JobsFound": r.JobsFound,
            "JobsAdded": r.JobsAdded,
            "JobsUpdated": r.JobsUpdated,
            "DuplicatesFound": r.DuplicatesFound,
            "JobsRejected": r.JobsRejected,
            "Status": r.Status,
            "ErrorMessage": r.ErrorMessage
        }
        for r in recent_runs_db
    ]

    # Configured sources status
    sources_db = db.query(JobSource).all()
    sources_list = [
        {
            "SourceId": s.SourceId,
            "SourceName": s.SourceName,
            "SourceType": s.SourceType,
            "ProviderName": s.ProviderName,
            "IsEnabled": s.IsEnabled,
            "LastSuccessfulRun": s.LastSuccessfulRun.isoformat() if s.LastSuccessfulRun else None,
            "TotalJobsCount": db.query(Job).filter(Job.SourceId == s.SourceId).count()
        }
        for s in sources_db
    ]

    return {
        "scheduler_enabled": settings.ENABLE_SCHEDULER,
        "scheduler_running": is_running,
        "interval_minutes": settings.JOB_REFRESH_MINUTES or 5,
        "next_run_time": next_run_time.isoformat() if next_run_time else None,
        "last_run_time": latest_run.StartedAt.isoformat() if latest_run and latest_run.StartedAt else None,
        "last_run_status": latest_run.Status if latest_run else "NONE",
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "running_runs": running_runs,
        "total_jobs_added": int(total_jobs_added),
        "total_jobs_updated": int(total_jobs_updated),
        "total_duplicates_prevented": int(total_duplicates),
        "registered_jobs": registered_jobs,
        "sources": sources_list,
        "recent_runs": recent_runs
    }

class AddCompanyPayload(BaseModel):
    provider: str
    company_slug: str
    company_name: Optional[str] = None

@router.post("/auto-discover")
async def trigger_auto_discovery(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers AI-powered and probe-based auto-discovery across UK tech employers.
    """
    from backend.app.services.source_discovery_service import SourceDiscoveryService
    res = await SourceDiscoveryService.run_discovery_cycle(db, use_ai=True)
    
    # If new sources were added, automatically trigger ingestion for them
    if res.get("new_sources_added", 0) > 0:
        background_tasks.add_task(JobService.refresh_all_sources, db)

    return res

@router.post("/add-company")
async def add_custom_company_source(
    payload: AddCompanyPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Manually registers a company slug on a supported ATS provider and starts ingestion.
    """
    from backend.app.services.source_discovery_service import SourceDiscoveryService
    try:
        res = await SourceDiscoveryService.add_custom_company(
            db=db,
            provider=payload.provider,
            company_slug=payload.company_slug,
            company_name=payload.company_name
        )
        
        # Trigger ingestion for the provider
        src = db.query(JobSource).filter(JobSource.ProviderName == payload.provider.lower()).first()
        if src:
            background_tasks.add_task(JobService.process_single_source, db, src)

        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add company source: {str(e)}")

