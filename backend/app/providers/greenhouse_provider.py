import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.providers.base_provider import BaseJobProvider, NormalizedJob
from backend.app.utils.text_normalizer import clean_html

logger = logging.getLogger(__name__)

class GreenhouseProvider(BaseJobProvider):
    def __init__(self):
        super().__init__("greenhouse", "https://boards-api.greenhouse.io/v1/boards/")

    async def fetch_jobs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        companies = config.get("companies", ["monzo", "deliveroo", "snyk", "checkout", "synthesia", "multiverse", "cleo"])
        all_raw_jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 UKSEJobFinder/1.0",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
            for company_slug in companies:
                url = f"{self.base_url}{company_slug}/jobs?content=true"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        jobs = data.get("jobs", [])
                        for j in jobs:
                            j["_company_slug"] = company_slug
                            all_raw_jobs.append(j)
                        logger.info(f"[Greenhouse] Fetched {len(jobs)} jobs for {company_slug}")
                    else:
                        logger.warning(f"[Greenhouse] Failed to fetch {company_slug}: HTTP {res.status_code}")
                except Exception as e:
                    logger.error(f"[Greenhouse] Error fetching {company_slug}: {e}")

        return all_raw_jobs

    def parse_job(self, raw_data: Dict[str, Any], company_name: str = "") -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_data.get("id", ""))
            title = raw_data.get("title", "").strip()
            if not external_id or not title:
                return None

            company = company_name or raw_data.get("_company_slug", "").title()
            
            # Location
            location_obj = raw_data.get("location", {})
            raw_loc = location_obj.get("name", "") if isinstance(location_obj, dict) else str(location_obj)
            
            # Content
            raw_content = raw_data.get("content", "")
            clean_desc = clean_html(raw_content)

            # URLs
            source_url = raw_data.get("absolute_url", "")
            apply_url = source_url

            # Dates
            updated_at = raw_data.get("updated_at")
            posted_date = None
            if updated_at:
                try:
                    posted_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            return NormalizedJob(
                external_job_id=f"gh_{external_id}",
                company_name=company,
                title=title,
                description=clean_desc,
                raw_location=raw_loc or "London, United Kingdom",
                source_job_url=source_url,
                company_career_url=f"https://boards.greenhouse.io/{raw_data.get('_company_slug', '')}",
                apply_url=apply_url,
                posted_date=posted_date,
                employment_type="Full-time",
                source_name="Greenhouse ATS Feed",
                source_type="ATS_GREENHOUSE"
            )
        except Exception as e:
            logger.error(f"[Greenhouse] Error parsing job: {e}")
            return None
