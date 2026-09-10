import logging
from typing import List, Dict, Any, Optional
from backend.app.providers.base_provider import BaseJobProvider, NormalizedJob

logger = logging.getLogger(__name__)

class CompanyCareerProvider(BaseJobProvider):
    """
    Generic company career page provider for custom structured endpoints or feeds.
    """
    def __init__(self):
        super().__init__("company_career", "")

    async def fetch_jobs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Supports custom direct feeds or webhook payloads
        return config.get("custom_jobs", [])

    def parse_job(self, raw_data: Dict[str, Any], company_name: str = "") -> Optional[NormalizedJob]:
        try:
            return NormalizedJob(**raw_data)
        except Exception as e:
            logger.error(f"[CompanyCareer] Error parsing: {e}")
            return None
