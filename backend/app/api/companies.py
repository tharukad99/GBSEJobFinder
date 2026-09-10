from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.app.database.session import get_db
from backend.app.models.company import Company
from backend.app.models.job import Job
from backend.app.schemas.company import CompanyResponse, CompanyListResponse

router = APIRouter(prefix="/companies", tags=["Companies"])

@router.get("", response_model=CompanyListResponse)
def get_companies(
    q: Optional[str] = Query(None, description="Search company name"),
    licensed_only: bool = Query(False, description="Only companies with sponsor licence"),
    db: Session = Depends(get_db)
):
    query = db.query(Company)

    if q:
        query = query.filter(Company.CompanyName.ilike(f"%{q.strip()}%"))

    if licensed_only:
        query = query.filter(Company.SponsorLicenceStatus == "LICENSED")

    companies = query.order_by(Company.CompanyName).all()

    # Get active job counts per company
    job_counts = dict(
        db.query(Job.CompanyId, func.count(Job.JobId))
        .filter(Job.JobStatus == "ACTIVE")
        .group_by(Job.CompanyId)
        .all()
    )

    results = []
    for comp in companies:
        results.append(CompanyResponse(
            CompanyId=comp.CompanyId,
            CompanyName=comp.CompanyName,
            NormalizedCompanyName=comp.NormalizedCompanyName,
            WebsiteUrl=comp.WebsiteUrl,
            CareersUrl=comp.CareersUrl,
            Industry=comp.Industry,
            SponsorLicenceStatus=comp.SponsorLicenceStatus,
            SponsorRoute=comp.SponsorRoute,
            SponsorRating=comp.SponsorRating,
            SponsorVerifiedAt=comp.SponsorVerifiedAt,
            CreatedAt=comp.CreatedAt,
            UpdatedAt=comp.UpdatedAt,
            ActiveJobsCount=job_counts.get(comp.CompanyId, 0)
        ))

    return {"total": len(results), "items": results}

@router.get("/{company_id}", response_model=CompanyResponse)
def get_company_by_id(company_id: int, db: Session = Depends(get_db)):
    comp = db.query(Company).filter(Company.CompanyId == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")

    active_count = db.query(Job).filter(Job.CompanyId == company_id, Job.JobStatus == "ACTIVE").count()

    return CompanyResponse(
        CompanyId=comp.CompanyId,
        CompanyName=comp.CompanyName,
        NormalizedCompanyName=comp.NormalizedCompanyName,
        WebsiteUrl=comp.WebsiteUrl,
        CareersUrl=comp.CareersUrl,
        Industry=comp.Industry,
        SponsorLicenceStatus=comp.SponsorLicenceStatus,
        SponsorRoute=comp.SponsorRoute,
        SponsorRating=comp.SponsorRating,
        SponsorVerifiedAt=comp.SponsorVerifiedAt,
        CreatedAt=comp.CreatedAt,
        UpdatedAt=comp.UpdatedAt,
        ActiveJobsCount=active_count
    )
