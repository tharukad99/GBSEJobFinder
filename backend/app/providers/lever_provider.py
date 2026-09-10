import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.providers.base_provider import BaseJobProvider, NormalizedJob
from backend.app.utils.text_normalizer import clean_html

logger = logging.getLogger(__name__)

class LeverProvider(BaseJobProvider):
    def __init__(self):
        super().__init__("lever", "https://api.lever.co/v0/postings/")

    async def fetch_jobs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        companies = config.get("companies", ["gocardless", "spotify", "atlan", "kroo", "pleo", "kraken"])
        all_raw_jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 UKSEJobFinder/1.0",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
            for company_slug in companies:
                url = f"{self.base_url}{company_slug}?mode=json"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        jobs = res.json()
                        for j in jobs:
                            j["_company_slug"] = company_slug
                            all_raw_jobs.append(j)
                        logger.info(f"[Lever] Fetched {len(jobs)} jobs for {company_slug}")
                    else:
                        logger.warning(f"[Lever] Failed to fetch {company_slug}: HTTP {res.status_code}")
                except Exception as e:
                    logger.error(f"[Lever] Error fetching {company_slug}: {e}")

        return all_raw_jobs

    def parse_job(self, raw_data: Dict[str, Any], company_name: str = "") -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_data.get("id", ""))
            title = raw_data.get("text", "").strip()
            if not external_id or not title:
                return None

            company = company_name or raw_data.get("_company_slug", "").title()
            
            # Location
            categories = raw_data.get("categories", {})
            raw_loc = categories.get("location", "") or raw_data.get("country", "")

            # Content
            desc = raw_data.get("descriptionPlain", "") or clean_html(raw_data.get("description", ""))
            additional = raw_data.get("additionalPlain", "")
            full_desc = f"{desc}\n\n{additional}".strip()

            # URLs
            source_url = raw_data.get("hostedUrl", "") or raw_data.get("applyUrl", "")
            apply_url = raw_data.get("applyUrl", "") or source_url

            # Dates
            created_at = raw_data.get("createdAt")
            posted_date = None
            if created_at:
                try:
                    posted_date = datetime.fromtimestamp(created_at / 1000.0)
                except Exception:
                    pass

            # Workplace type
            workplace_type = raw_data.get("workplaceType", "unspecified")
            commitment = categories.get("commitment", "Full-time")

            return NormalizedJob(
                external_job_id=f"lever_{external_id}",
                company_name=company,
                title=title,
                description=full_desc,
                raw_location=raw_loc or "London, UK",
                source_job_url=source_url,
                company_career_url=f"https://jobs.lever.co/{raw_data.get('_company_slug', '')}",
                apply_url=apply_url,
                posted_date=posted_date,
                employment_type=commitment,
                source_name="Lever ATS Feed",
                source_type="ATS_LEVER"
            )
        except Exception as e:
            logger.error(f"[Lever] Error parsing job: {e}")
            return None
