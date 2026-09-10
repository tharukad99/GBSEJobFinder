import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.providers.base_provider import BaseJobProvider, NormalizedJob
from backend.app.utils.text_normalizer import clean_html

logger = logging.getLogger(__name__)

class WorkableProvider(BaseJobProvider):
    def __init__(self):
        super().__init__("workable", "https://apply.workable.com/api/v1/widget/accounts/")

    async def fetch_jobs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        companies = config.get("companies", ["skyscanner", "tails-com", "secret-escapes"])
        all_raw_jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 UKSEJobFinder/1.0",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
            for company_slug in companies:
                url = f"{self.base_url}{company_slug}"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        jobs = data.get("jobs", [])
                        for j in jobs:
                            j["_company_slug"] = company_slug
                            all_raw_jobs.append(j)
                        logger.info(f"[Workable] Fetched {len(jobs)} jobs for {company_slug}")
                    else:
                        logger.warning(f"[Workable] Failed to fetch {company_slug}: HTTP {res.status_code}")
                except Exception as e:
                    logger.error(f"[Workable] Error fetching {company_slug}: {e}")

        return all_raw_jobs

    def parse_job(self, raw_data: Dict[str, Any], company_name: str = "") -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_data.get("shortcode", "") or raw_data.get("id", ""))
            title = raw_data.get("title", "").strip()
            if not external_id or not title:
                return None

            company = company_name or raw_data.get("_company_slug", "").title()
            
            # Location
            city = raw_data.get("city", "")
            country = raw_data.get("country", "")
            is_telecommuting = raw_data.get("telecommuting", False)
            raw_loc = f"{city}, {country}".strip(", ")
            if is_telecommuting:
                raw_loc = f"Remote, {raw_loc}"

            # Content
            desc = clean_html(raw_data.get("description", ""))

            # URLs
            shortcode = raw_data.get("shortcode", "")
            company_slug = raw_data.get("_company_slug", "")
            source_url = f"https://apply.workable.com/{company_slug}/j/{shortcode}/"
            apply_url = source_url

            # Dates
            published_on = raw_data.get("published_on")
            posted_date = None
            if published_on:
                try:
                    posted_date = datetime.fromisoformat(published_on.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            return NormalizedJob(
                external_job_id=f"workable_{external_id}",
                company_name=company,
                title=title,
                description=desc,
                raw_location=raw_loc or "London, United Kingdom",
                source_job_url=source_url,
                company_career_url=f"https://apply.workable.com/{company_slug}/",
                apply_url=apply_url,
                posted_date=posted_date,
                employment_type=raw_data.get("employment_type", "Full-time"),
                source_name="Workable ATS Feed",
                source_type="ATS_WORKABLE"
            )
        except Exception as e:
            logger.error(f"[Workable] Error parsing job: {e}")
            return None
