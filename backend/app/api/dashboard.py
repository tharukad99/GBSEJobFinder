from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.app.database.session import get_db
from backend.app.models.job import Job
from backend.app.models.company import Company
from backend.app.models.sponsorship import SponsorshipEvidence
from backend.app.models.skill import Skill, JobSkill
from backend.app.models.source import JobSource
from backend.app.models.scrape_run import ScrapeRun
from backend.app.schemas.dashboard import DashboardStatsResponse, SponsorshipBreakdown

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    # Base active jobs
    total_active = db.query(Job).filter(Job.JobStatus == "ACTIVE").count()

    # New jobs
    new_today = db.query(Job).filter(Job.JobStatus == "ACTIVE", Job.FirstSeenAt >= today_start).count()
    new_7_days = db.query(Job).filter(Job.JobStatus == "ACTIVE", Job.FirstSeenAt >= seven_days_ago).count()

    # Sponsorship counts
    spons_counts = dict(
        db.query(SponsorshipEvidence.SponsorshipStatus, func.count(SponsorshipEvidence.SponsorshipEvidenceId))
        .join(Job, Job.JobId == SponsorshipEvidence.JobId)
        .filter(Job.JobStatus == "ACTIVE")
        .group_by(SponsorshipEvidence.SponsorshipStatus)
        .all()
    )
    confirmed_count = spons_counts.get("CONFIRMED", 0)
    may_offer_count = spons_counts.get("MAY_OFFER", 0)
    no_spons_count = spons_counts.get("NO_SPONSORSHIP", 0)
    unknown_count = spons_counts.get("UNKNOWN", 0)

    # Location counts
    london_count = db.query(Job).filter(
        Job.JobStatus == "ACTIVE",
        or_(Job.City.ilike("%London%"), Job.Location.ilike("%London%"))
    ).count()

    manchester_count = db.query(Job).filter(
        Job.JobStatus == "ACTIVE",
        or_(Job.City.ilike("%Manchester%"), Job.Location.ilike("%Manchester%"))
    ).count()

    remote_uk_count = db.query(Job).filter(
        Job.JobStatus == "ACTIVE",
        Job.RemoteType == "Remote UK"
    ).count()

    hybrid_count = db.query(Job).filter(
        Job.JobStatus == "ACTIVE",
        Job.RemoteType == "Hybrid"
    ).count()

    # Companies
    total_companies = db.query(Company).count()
    total_licensed = db.query(Company).filter(Company.SponsorLicenceStatus == "LICENSED").count()

    # Refresh times
    latest_run = db.query(ScrapeRun).filter(ScrapeRun.Status == "SUCCESS").order_by(ScrapeRun.CompletedAt.desc()).first()
    last_refresh = latest_run.CompletedAt if latest_run else None
    next_refresh = (last_refresh + timedelta(hours=6)) if last_refresh else (now + timedelta(hours=6))

    # Top skills
    top_skills_raw = (
        db.query(Skill.SkillName, func.count(JobSkill.JobSkillId))
        .join(JobSkill, JobSkill.SkillId == Skill.SkillId)
        .join(Job, Job.JobId == JobSkill.JobId)
        .filter(Job.JobStatus == "ACTIVE")
        .group_by(Skill.SkillName)
        .order_by(func.count(JobSkill.JobSkillId).desc())
        .limit(10)
        .all()
    )
    top_skills = [{"name": name, "count": count} for name, count in top_skills_raw]

    return DashboardStatsResponse(
        total_active_jobs=total_active,
        new_jobs_today=new_today,
        new_jobs_last_7_days=new_7_days,
        confirmed_sponsorship_jobs=confirmed_count,
        may_offer_sponsorship_jobs=may_offer_count,
        london_jobs=london_count,
        manchester_jobs=manchester_count,
        remote_uk_jobs=remote_uk_count,
        hybrid_jobs=hybrid_count,
        last_refresh_time=last_refresh,
        next_refresh_time=next_refresh,
        total_companies=total_companies,
        total_licensed_sponsors=total_licensed,
        sponsorship_breakdown=SponsorshipBreakdown(
            confirmed=confirmed_count,
            may_offer=may_offer_count,
            no_sponsorship=no_spons_count,
            unknown=unknown_count
        ),
        top_skills=top_skills
    )
