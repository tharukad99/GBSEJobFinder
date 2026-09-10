import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from backend.app.models.job import Job
from backend.app.models.company import Company
from backend.app.utils.text_normalizer import create_duplicate_hash, normalize_company_name, normalize_job_title

logger = logging.getLogger(__name__)

# Source priority ordering (lower index = higher priority)
SOURCE_PRIORITY = {
    "COMPANY_CAREER": 1,
    "ATS_GREENHOUSE": 2,
    "ATS_LEVER": 2,
    "ATS_WORKABLE": 2,
    "ATS_SMARTRECRUITERS": 2,
    "ATS_ASHBY": 2,
    "PUBLIC_FEED": 3,
    "AGGREGATOR": 4
}

class DeduplicationService:
    @staticmethod
    def generate_hash(company_name: str, title: str, location: str) -> str:
        return create_duplicate_hash(company_name, title, location)

    @staticmethod
    def find_duplicate(db: Session, duplicate_hash: str, external_job_id: Optional[str] = None) -> Optional[Job]:
        """
        Checks if a job already exists in the database by duplicate hash or external ID.
        """
        if external_job_id:
            existing = db.query(Job).filter(Job.ExternalJobId == external_job_id).first()
            if existing:
                return existing

        if duplicate_hash:
            existing = db.query(Job).filter(Job.DuplicateHash == duplicate_hash).first()
            if existing:
                return existing

        return None

    @staticmethod
    def should_replace_source(existing_job: Job, incoming_source_type: str) -> bool:
        """
        Decides whether to upgrade/replace the source details based on provider tier priority.
        """
        existing_source_type = existing_job.source.SourceType if existing_job.source else "AGGREGATOR"
        existing_rank = SOURCE_PRIORITY.get(existing_source_type, 99)
        incoming_rank = SOURCE_PRIORITY.get(incoming_source_type, 99)
        return incoming_rank < existing_rank
