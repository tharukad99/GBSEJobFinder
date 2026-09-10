import json
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.app.database.config import settings
from backend.app.database.session import get_db
from backend.app.models.job import Job
from backend.app.models.company import Company
from backend.app.models.source import JobSource
from backend.app.models.sponsorship import SponsorshipEvidence
from backend.app.services.job_service import JobService
from backend.app.services.verification_service import VerificationService
from backend.app.services.sponsor_register_service import sponsor_register
from backend.app.schemas.admin import RefreshResponse, SponsorshipOverrideRequest
from backend.app.schemas.source import JobSourceUpdate
from backend.app.utils.rate_limiter import rate_limit

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post(
    "/refresh",
    response_model=RefreshResponse,
    dependencies=[Depends(rate_limit(max_requests=settings.RATE_LIMIT_ADMIN_PER_MINUTE, window_seconds=60, bucket_name="admin_refresh"))]
)
async def trigger_job_refresh(source_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Manually triggers job collection and verification.
    """
    start_time = datetime.utcnow()
    if source_id:
        src = db.query(JobSource).filter(JobSource.SourceId == source_id).first()
        if not src:
            raise HTTPException(status_code=404, detail="Source not found")
        result = await JobService.process_single_source(db, src)
        results = [result]
    else:
        results = await JobService.refresh_all_sources(db)

    return RefreshResponse(
        status="COMPLETED",
        message="Job refresh finished.",
        started_at=start_time,
        results=results
    )

@router.patch("/sources/{source_id}")
def update_source(source_id: int, payload: JobSourceUpdate, db: Session = Depends(get_db)):
    src = db.query(JobSource).filter(JobSource.SourceId == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")

    if payload.IsEnabled is not None:
        src.IsEnabled = payload.IsEnabled
    if payload.SourceName is not None:
        src.SourceName = payload.SourceName
    if payload.ConfigJson is not None:
        src.ConfigJson = payload.ConfigJson

    src.UpdatedAt = datetime.utcnow()
    db.commit()
    db.refresh(src)
    return {"message": "Source updated successfully", "source_id": src.SourceId, "is_enabled": src.IsEnabled}

@router.patch("/jobs/{job_id}/sponsorship")
def override_job_sponsorship(
    job_id: int,
    payload: SponsorshipOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Manually override the sponsorship status for a specific vacancy.
    """
    job = db.query(Job).filter(Job.JobId == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    valid_statuses = ["CONFIRMED", "MAY_OFFER", "NO_SPONSORSHIP", "UNKNOWN"]
    if payload.sponsorship_status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid sponsorship status. Choose from: {valid_statuses}")

    spons = db.query(SponsorshipEvidence).filter(SponsorshipEvidence.JobId == job_id).first()
    now = datetime.utcnow()
    status_clean = payload.sponsorship_status.upper()

    if not spons:
        spons = SponsorshipEvidence(
            JobId=job_id,
            SponsorshipStatus=status_clean,
            EvidenceText=payload.evidence_text,
            EvidenceSource="Manual Admin Override",
            ConfidenceLevel=payload.confidence_level or "High",
            VerifiedAt=now
        )
        db.add(spons)
    else:
        spons.SponsorshipStatus = status_clean
        spons.EvidenceText = payload.evidence_text
        spons.EvidenceSource = "Manual Admin Override"
        spons.ConfidenceLevel = payload.confidence_level or "High"
        spons.VerifiedAt = now

    # Recalculate match score with new status
    from backend.app.services.matching_service import calculate_match_score, extract_technologies
    techs = extract_technologies(job.Title, job.Description)
    job.MatchScore = calculate_match_score(
        title=job.Title,
        matched_skills=techs,
        sponsorship_status=status_clean,
        city=job.City,
        region=job.Region,
        remote_type=job.RemoteType,
        experience_level=job.ExperienceLevel or "Mid"
    )
    job.UpdatedAt = now
    db.commit()

    return {
        "message": "Sponsorship classification updated.",
        "job_id": job_id,
        "new_status": status_clean,
        "new_match_score": job.MatchScore
    }

@router.post("/jobs/{job_id}/verify")
async def verify_single_job(job_id: int, db: Session = Depends(get_db)):
    """
    Manually check if the vacancy link is still live and reachable.
    """
    job = db.query(Job).filter(Job.JobId == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await VerificationService.verify_job(db, job)
    return result

@router.patch("/jobs/{job_id}/close")
def close_single_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.JobId == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.JobStatus = "CLOSED"
    job.UpdatedAt = datetime.utcnow()
    db.commit()
    return {"message": "Job marked as CLOSED", "job_id": job_id}

@router.post(
    "/sponsor-register/update",
    dependencies=[Depends(rate_limit(max_requests=settings.RATE_LIMIT_ADMIN_PER_MINUTE, window_seconds=60, bucket_name="admin_sponsor_update"))]
)
async def update_sponsor_register():
    """
    Updates the sponsor register from the official UK Home Office release.
    """
    count = await sponsor_register.update_from_gov_uk()
    return {"status": "SUCCESS", "message": f"Sponsor register active with {count} verified employers."}
