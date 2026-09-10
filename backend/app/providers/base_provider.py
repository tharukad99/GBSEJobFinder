import abc
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class NormalizedJob(BaseModel):
    external_job_id: str
    company_name: str
    title: str
    description: str
    raw_location: str
    source_job_url: str
    company_career_url: Optional[str] = None
    apply_url: str
    posted_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    employment_type: Optional[str] = "Full-time"
    salary_text: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    source_name: str
    source_type: str

class BaseJobProvider(abc.ABC):
    """
    Common base interface for all modular job providers.
    """
    def __init__(self, provider_name: str, base_url: str = ""):
        self.provider_name = provider_name
        self.base_url = base_url

    @abc.abstractmethod
    async def fetch_jobs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch raw job records from remote API or structured endpoint."""
        pass

    @abc.abstractmethod
    def parse_job(self, raw_data: Dict[str, Any], company_name: str) -> Optional[NormalizedJob]:
        """Parse raw job into NormalizedJob standard structure."""
        pass
