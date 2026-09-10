import math
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, asc, func
from backend.app.database.session import get_db
from backend.app.models.job import Job
from backend.app.models.company import Company
from backend.app.models.sponsorship import SponsorshipEvidence
from backend.app.models.skill import Skill, JobSkill
from backend.app.schemas.job import JobListResponse, JobListItem, JobDetail, CompanySummary, SponsorshipEvidenceSchema, SkillItem

router = APIRouter(prefix="/jobs", tags=["Jobs"])

def serialize_job(job: Job) -> dict:
    comp = job.company
    spons = job.sponsorship_evidence
    skills = [
        {
            "SkillId": js.skill.SkillId,
            "SkillName": js.skill.SkillName,
            "NormalizedSkillName": js.skill.NormalizedSkillName,
            "RequiredOrPreferred": js.RequiredOrPreferred
        }
        for js in job.skills if js.skill
    ]
    return {
        "JobId": job.JobId,
        "ExternalJobId": job.ExternalJobId,
        "Title": job.Title,
        "NormalizedTitle": job.NormalizedTitle,
        "Description": job.Description,
        "Location": job.Location,
        "City": job.City,
        "Region": job.Region,
        "Country": job.Country,
        "RemoteType": job.RemoteType,
        "EmploymentType": job.EmploymentType,
        "SalaryText": job.SalaryText,
        "SalaryMin": job.SalaryMin,
        "SalaryMax": job.SalaryMax,
        "ExperienceLevel": job.ExperienceLevel,
        "SourceJobUrl": job.SourceJobUrl,
        "CompanyCareerUrl": job.CompanyCareerUrl,
        "ApplyUrl": job.ApplyUrl,
        "PostedDate": job.PostedDate,
        "ClosingDate": job.ClosingDate,
        "FirstSeenAt": job.FirstSeenAt,
        "LastSeenAt": job.LastSeenAt,
        "LastVerifiedAt": job.LastVerifiedAt,
        "JobStatus": job.JobStatus,
        "MatchScore": job.MatchScore,
        "QualityScore": job.QualityScore,
        "DuplicateHash": job.DuplicateHash,
        "Company": {
            "CompanyId": comp.CompanyId,
            "CompanyName": comp.CompanyName,
            "WebsiteUrl": comp.WebsiteUrl,
            "CareersUrl": comp.CareersUrl,
            "SponsorLicenceStatus": comp.SponsorLicenceStatus,
            "SponsorRoute": comp.SponsorRoute,
            "SponsorRating": comp.SponsorRating,
        } if comp else None,
        "Sponsorship": {
            "SponsorshipEvidenceId": spons.SponsorshipEvidenceId,
            "SponsorshipStatus": spons.SponsorshipStatus,
            "EvidenceText": spons.EvidenceText,
            "EvidenceUrl": spons.EvidenceUrl,
            "EvidenceSource": spons.EvidenceSource,
            "ConfidenceLevel": spons.ConfidenceLevel,
            "VerifiedAt": spons.VerifiedAt,
        } if spons else None,
        "Skills": skills
    }

@router.get("", response_model=JobListResponse)
def get_jobs(
    q: Optional[str] = Query(None, description="Search keyword (title, company, tech)"),
    sponsorship: Optional[str] = Query(None, description="confirmed, may_offer, confirmed_and_may_offer, unknown, all"),
    location: Optional[str] = Query(None, description="london, manchester, north_west, remote_uk, hybrid, all"),
    skill: Optional[str] = Query(None, description="Filter by skill e.g. .NET, C#, React, Azure"),
    experience_level: Optional[str] = Query(None, description="senior, mid, junior, all"),
    days: Optional[int] = Query(None, description="Posted in last N days (1, 3, 7, 14)"),
    work_type: Optional[str] = Query(None, description="Remote UK, Hybrid, On-site"),
    status: Optional[str] = Query("ACTIVE", description="ACTIVE, POSSIBLY_REMOVED, CLOSED, ALL"),
    sort: Optional[str] = Query("best_match", description="best_match, newest, sponsorship, recently_verified"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Job).options(
        joinedload(Job.company),
        joinedload(Job.sponsorship_evidence),
        joinedload(Job.skills).joinedload(JobSkill.skill)
    )

    # Status filter
    if status != "ALL":
        query = query.filter(Job.JobStatus == status)

    # Search keyword
    if q:
        term = f"%{q.strip()}%"
        query = query.join(Job.company).filter(
            or_(
                Job.Title.ilike(term),
                Job.NormalizedTitle.ilike(term),
                Job.Description.ilike(term),
                Company.CompanyName.ilike(term),
                Job.Location.ilike(term),
                Job.City.ilike(term)
            )
        )

    # Experience level filter
    if experience_level and experience_level.lower() != "all":
        exp = experience_level.lower()
        if exp in ("senior", "lead", "principal"):
            query = query.filter(
                or_(
                    Job.ExperienceLevel.in_(["Senior", "Lead", "Principal", "Staff", "Architect"]),
                    Job.Title.ilike("%senior%"),
                    Job.Title.ilike("%lead%"),
                    Job.Title.ilike("%principal%"),
                    Job.Title.ilike("%staff%"),
                    Job.Title.ilike("%architect%")
                )
            )
        elif exp in ("junior", "graduate", "entry"):
            query = query.filter(
                or_(
                    Job.ExperienceLevel == "Junior",
                    Job.Title.ilike("%junior%"),
                    Job.Title.ilike("%graduate%"),
                    Job.Title.ilike("%entry%"),
                    Job.Title.ilike("%associate%")
                )
            )
        elif exp == "mid":
            query = query.filter(Job.ExperienceLevel == "Mid")


    # Sponsorship filter (Default excludes NO_SPONSORSHIP unless requested)
    if sponsorship:
        s_lower = sponsorship.lower()
        if s_lower == "confirmed":
            query = query.join(Job.sponsorship_evidence).filter(SponsorshipEvidence.SponsorshipStatus == "CONFIRMED")
        elif s_lower == "may_offer":
            query = query.join(Job.sponsorship_evidence).filter(SponsorshipEvidence.SponsorshipStatus == "MAY_OFFER")
        elif s_lower in ("confirmed_and_may_offer", "confirmed_may_offer"):
            query = query.join(Job.sponsorship_evidence).filter(
                SponsorshipEvidence.SponsorshipStatus.in_(["CONFIRMED", "MAY_OFFER"])
            )
        elif s_lower == "unknown":
            query = query.join(Job.sponsorship_evidence).filter(SponsorshipEvidence.SponsorshipStatus == "UNKNOWN")
        elif s_lower == "no_sponsorship":
            query = query.join(Job.sponsorship_evidence).filter(SponsorshipEvidence.SponsorshipStatus == "NO_SPONSORSHIP")
    else:
        # By default exclude explicitly NO_SPONSORSHIP jobs to focus on viable roles
        query = query.outerjoin(Job.sponsorship_evidence).filter(
            or_(
                SponsorshipEvidence.SponsorshipStatus != "NO_SPONSORSHIP",
                SponsorshipEvidence.SponsorshipStatus.is_(None)
            )
        )

    # Location filter
    if location and location.lower() != "all":
        loc = location.lower()
        if loc == "london":
            query = query.filter(or_(Job.City.ilike("%London%"), Job.Location.ilike("%London%")))
        elif loc == "manchester":
            query = query.filter(or_(Job.City.ilike("%Manchester%"), Job.Location.ilike("%Manchester%")))
        elif loc == "north_west":
            query = query.filter(or_(Job.Region.ilike("%North West%"), Job.City.in_(["Manchester", "Liverpool", "Chester", "Preston", "Warrington"])))
        elif loc == "remote_uk":
            query = query.filter(Job.RemoteType == "Remote UK")
        elif loc == "hybrid":
            query = query.filter(Job.RemoteType == "Hybrid")

    # Work type filter
    if work_type and work_type.lower() != "all":
        query = query.filter(Job.RemoteType.ilike(f"%{work_type}%"))

    # Skill filter
    if skill:
        norm_skill = skill.lower().strip()
        query = query.join(Job.skills).join(JobSkill.skill).filter(
            Skill.NormalizedSkillName == norm_skill
        )

    # Days posted filter
    if days and days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Job.PostedDate >= cutoff)

    # Sorting
    if sort == "newest":
        query = query.order_by(desc(Job.PostedDate), desc(Job.JobId))
    elif sort == "sponsorship":
        query = query.order_by(
            desc(Job.MatchScore),
            desc(Job.PostedDate)
        )
    elif sort == "recently_verified":
        query = query.order_by(desc(Job.LastVerifiedAt), desc(Job.JobId))
    else: # best_match
        query = query.order_by(desc(Job.MatchScore), desc(Job.PostedDate))

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": [serialize_job(j) for j in items]
    }

@router.get("/confirmed", response_model=JobListResponse)
def get_confirmed_sponsorship_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    return get_jobs(sponsorship="confirmed", page=page, page_size=page_size, db=db)

@router.get("/may-offer", response_model=JobListResponse)
def get_may_offer_sponsorship_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    return get_jobs(sponsorship="may_offer", page=page, page_size=page_size, db=db)

@router.get("/recent", response_model=List[JobListItem])
def get_recent_jobs(limit: int = 10, db: Session = Depends(get_db)):
    jobs = db.query(Job).options(
        joinedload(Job.company),
        joinedload(Job.sponsorship_evidence),
        joinedload(Job.skills).joinedload(JobSkill.skill)
    ).filter(Job.JobStatus == "ACTIVE").order_by(desc(Job.PostedDate)).limit(limit).all()
    return [serialize_job(j) for j in jobs]

@router.get("/{job_id}", response_model=JobDetail)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).options(
        joinedload(Job.company),
        joinedload(Job.sponsorship_evidence),
        joinedload(Job.skills).joinedload(JobSkill.skill)
    ).filter(Job.JobId == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return serialize_job(job)
