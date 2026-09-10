import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from backend.app.models.job import Job
from backend.app.models.company import Company
from backend.app.models.skill import Skill, JobSkill
from backend.app.models.source import JobSource
from backend.app.models.scrape_run import ScrapeRun
from backend.app.models.sponsorship import SponsorshipEvidence
from backend.app.providers import get_provider
from backend.app.utils.text_normalizer import normalize_company_name, normalize_job_title
from backend.app.utils.location_parser import parse_location
from backend.app.services.matching_service import (
    is_target_job_title, extract_technologies, calculate_match_score, 
    calculate_quality_score, determine_experience_level
)
from backend.app.services.sponsorship_service import evaluate_sponsorship
from backend.app.services.deduplication_service import DeduplicationService
from backend.app.services.verification_service import VerificationService

logger = logging.getLogger(__name__)

class JobService:
    @staticmethod
    def get_or_create_company(
        db: Session,
        company_name: str,
        website_url: Optional[str] = None,
        careers_url: Optional[str] = None,
        sponsor_status: str = "UNKNOWN",
        sponsor_route: Optional[str] = None,
        sponsor_rating: Optional[str] = None
    ) -> Company:
        norm_name = normalize_company_name(company_name)
        company = db.query(Company).filter(Company.NormalizedCompanyName == norm_name).first()
        
        now = datetime.utcnow()
        if not company:
            company = Company(
                CompanyName=company_name.strip(),
                NormalizedCompanyName=norm_name,
                WebsiteUrl=website_url,
                CareersUrl=careers_url,
                SponsorLicenceStatus=sponsor_status,
                SponsorRoute=sponsor_route,
                SponsorRating=sponsor_rating,
                SponsorVerifiedAt=now if sponsor_status != "UNKNOWN" else None
            )
            db.add(company)
            db.flush()
        else:
            # Update existing company details if newly verified
            if sponsor_status != "UNKNOWN" and company.SponsorLicenceStatus == "UNKNOWN":
                company.SponsorLicenceStatus = sponsor_status
                company.SponsorRoute = sponsor_route
                company.SponsorRating = sponsor_rating
                company.SponsorVerifiedAt = now
            if careers_url and not company.CareersUrl:
                company.CareersUrl = careers_url
            if website_url and not company.WebsiteUrl:
                company.WebsiteUrl = website_url
            db.flush()

        return company

    @classmethod
    async def process_single_source(cls, db: Session, source: JobSource) -> Dict[str, Any]:
        """
        Executes a scrape run for a single source safely.
        """
        now = datetime.utcnow()
        scrape_run = ScrapeRun(
            SourceId=source.SourceId,
            StartedAt=now,
            Status="RUNNING"
        )
        db.add(scrape_run)
        db.commit()

        provider = get_provider(source.ProviderName)
        if not provider:
            scrape_run.Status = "FAILED"
            scrape_run.ErrorMessage = f"Provider '{source.ProviderName}' not implemented."
            scrape_run.CompletedAt = datetime.utcnow()
            db.commit()
            return {"error": scrape_run.ErrorMessage}

        config = {}
        if source.ConfigJson:
            try:
                config = json.loads(source.ConfigJson)
            except Exception:
                pass

        jobs_found = 0
        jobs_added = 0
        jobs_updated = 0
        duplicates_found = 0
        jobs_rejected = 0

        try:
            raw_jobs = await provider.fetch_jobs(config)
            jobs_found = len(raw_jobs)

            # Preload skill cache
            skills_dict = {s.NormalizedSkillName: s for s in db.query(Skill).all()}

            for raw in raw_jobs:
                norm_job = provider.parse_job(raw, "")
                if not norm_job:
                    jobs_rejected += 1
                    continue

                # 1. Validate target title
                if not is_target_job_title(norm_job.title):
                    jobs_rejected += 1
                    continue

                # 2. Validate UK Location
                loc_info = parse_location(norm_job.raw_location, norm_job.description)
                if not loc_info.is_uk:
                    jobs_rejected += 1
                    continue

                # 3. Sponsorship Evaluation
                spons_res = evaluate_sponsorship(
                    norm_job.company_name,
                    norm_job.title,
                    norm_job.description
                )

                # 4. Experience & Tech extraction
                exp_level = determine_experience_level(norm_job.title, norm_job.description)
                matched_techs = extract_technologies(norm_job.title, norm_job.description)

                # 5. Calculate match & quality scores
                match_score = calculate_match_score(
                    title=norm_job.title,
                    matched_skills=matched_techs,
                    sponsorship_status=spons_res.status,
                    city=loc_info.city,
                    region=loc_info.region,
                    remote_type=loc_info.remote_type,
                    experience_level=exp_level
                )

                quality_score = calculate_quality_score(
                    source_type=norm_job.source_type,
                    has_apply_url=bool(norm_job.apply_url),
                    description_len=len(norm_job.description or ""),
                    has_posted_date=norm_job.posted_date is not None,
                    has_sponsorship_evidence=bool(spons_res.evidence_text),
                    is_company_licensed=spons_res.company_is_licensed
                )

                # 6. Deduplication check
                dup_hash = DeduplicationService.generate_hash(
                    norm_job.company_name, norm_job.title, loc_info.normalized_location
                )
                existing_job = DeduplicationService.find_duplicate(db, dup_hash, norm_job.external_job_id)

                if existing_job:
                    duplicates_found += 1
                    # Refresh last seen date & update scores
                    existing_job.LastSeenAt = datetime.utcnow()
                    existing_job.MatchScore = match_score
                    existing_job.QualityScore = quality_score
                    if norm_job.description and len(norm_job.description) > len(existing_job.Description or ""):
                        existing_job.Description = norm_job.description
                    
                    # Update source if incoming has higher priority tier
                    if DeduplicationService.should_replace_source(existing_job, norm_job.source_type):
                        existing_job.ApplyUrl = norm_job.apply_url
                        existing_job.SourceJobUrl = norm_job.source_job_url
                    
                    jobs_updated += 1
                else:
                    # 7. Get / Create Company
                    comp_status = "LICENSED" if spons_res.company_is_licensed else "UNKNOWN"
                    company = cls.get_or_create_company(
                        db=db,
                        company_name=norm_job.company_name,
                        careers_url=norm_job.company_career_url,
                        sponsor_status=comp_status,
                        sponsor_route=spons_res.company_sponsor_route,
                        sponsor_rating=spons_res.company_sponsor_rating
                    )

                    new_job = Job(
                        ExternalJobId=norm_job.external_job_id,
                        CompanyId=company.CompanyId,
                        Title=norm_job.title,
                        NormalizedTitle=normalize_job_title(norm_job.title),
                        Description=norm_job.description,
                        Location=loc_info.normalized_location,
                        City=loc_info.city,
                        Region=loc_info.region,
                        Country=loc_info.country,
                        RemoteType=loc_info.remote_type,
                        EmploymentType=norm_job.employment_type,
                        SalaryText=norm_job.salary_text,
                        SalaryMin=norm_job.salary_min,
                        SalaryMax=norm_job.salary_max,
                        ExperienceLevel=exp_level,
                        SourceId=source.SourceId,
                        SourceJobUrl=norm_job.source_job_url,
                        CompanyCareerUrl=norm_job.company_career_url or company.CareersUrl,
                        ApplyUrl=norm_job.apply_url,
                        PostedDate=norm_job.posted_date or datetime.utcnow(),
                        ClosingDate=norm_job.closing_date,
                        FirstSeenAt=datetime.utcnow(),
                        LastSeenAt=datetime.utcnow(),
                        LastVerifiedAt=datetime.utcnow(),
                        JobStatus="ACTIVE",
                        MatchScore=match_score,
                        QualityScore=quality_score,
                        DuplicateHash=dup_hash
                    )
                    db.add(new_job)
                    db.flush()

                    # 8. Create Sponsorship Evidence record
                    spons_ev = SponsorshipEvidence(
                        JobId=new_job.JobId,
                        SponsorshipStatus=spons_res.status,
                        EvidenceText=spons_res.evidence_text,
                        EvidenceUrl=norm_job.apply_url,
                        EvidenceSource=spons_res.evidence_source,
                        ConfidenceLevel=spons_res.confidence_level,
                        VerifiedAt=datetime.utcnow()
                    )
                    db.add(spons_ev)

                    # 9. Link Skills
                    for tech in matched_techs.get("all", []):
                        norm_tech = tech.lower()
                        skill_obj = skills_dict.get(norm_tech)
                        if not skill_obj:
                            skill_obj = Skill(SkillName=tech, NormalizedSkillName=norm_tech, Category="Extracted")
                            db.add(skill_obj)
                            db.flush()
                            skills_dict[norm_tech] = skill_obj

                        req_pref = "Required" if tech in matched_techs.get("primary", []) else "Preferred"
                        db.add(JobSkill(JobId=new_job.JobId, SkillId=skill_obj.SkillId, RequiredOrPreferred=req_pref))

                    jobs_added += 1

            db.commit()

            scrape_run.CompletedAt = datetime.utcnow()
            scrape_run.JobsFound = jobs_found
            scrape_run.JobsAdded = jobs_added
            scrape_run.JobsUpdated = jobs_updated
            scrape_run.DuplicatesFound = duplicates_found
            scrape_run.JobsRejected = jobs_rejected
            scrape_run.Status = "SUCCESS"
            
            source.LastSuccessfulRun = datetime.utcnow()
            db.commit()

            return {
                "source": source.SourceName,
                "status": "SUCCESS",
                "jobs_found": jobs_found,
                "jobs_added": jobs_added,
                "jobs_updated": jobs_updated,
                "duplicates_found": duplicates_found,
                "jobs_rejected": jobs_rejected
            }
        except Exception as e:
            logger.error(f"Error executing scrape run for {source.SourceName}: {e}", exc_info=True)
            db.rollback()
            scrape_run.Status = "FAILED"
            scrape_run.ErrorMessage = str(e)[:1000]
            scrape_run.CompletedAt = datetime.utcnow()
            db.commit()
            return {
                "source": source.SourceName,
                "status": "FAILED",
                "error": str(e)
            }

    @classmethod
    async def refresh_all_sources(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Refreshes all enabled job sources sequentially or concurrently with error isolation.
        """
        sources = db.query(JobSource).filter(JobSource.IsEnabled == True).all()
        results = []
        for src in sources:
            res = await cls.process_single_source(db, src)
            results.append(res)
        return results
