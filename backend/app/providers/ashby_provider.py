import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.providers.base_provider import BaseJobProvider, NormalizedJob
from backend.app.utils.text_normalizer import clean_html

logger = logging.getLogger(__name__)

class AshbyProvider(BaseJobProvider):
    def __init__(self):
        super().__init__("ashby", "https://api.ashbyhq.com/posting-api/job-board/")

    async def fetch_jobs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        companies = config.get("companies", ["linear", "ramp", "postman", "deel", "ironclad", "glide"])
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
                        logger.info(f"[Ashby] Fetched {len(jobs)} jobs for {company_slug}")
                    else:
                        logger.warning(f"[Ashby] Failed to fetch {company_slug}: HTTP {res.status_code}")
                except Exception as e:
                    logger.error(f"[Ashby] Error fetching {company_slug}: {e}")

        return all_raw_jobs

    def parse_job(self, raw_data: Dict[str, Any], company_name: str = "") -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_data.get("id", ""))
            title = raw_data.get("title", "").strip()
            if not external_id or not title:
                return None

            company = company_name or raw_data.get("_company_slug", "").title()
            
            # Location
            raw_loc = raw_data.get("location", "")
            is_remote = raw_data.get("isRemote", False)
            if is_remote and "remote" not in raw_loc.lower():
                raw_loc = f"Remote, {raw_loc}".strip(", ")

            # Content
            desc = clean_html(raw_data.get("descriptionHtml", "") or raw_data.get("descriptionPlain", ""))

            # URLs
            source_url = raw_data.get("jobUrl", "") or f"https://jobs.ashbyhq.com/{raw_data.get('_company_slug', '')}/{external_id}"
            apply_url = raw_data.get("applyUrl", "") or source_url

            # Dates
            published_at = raw_data.get("publishedAt")
            posted_date = None
            if published_at:
                try:
                    posted_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            return NormalizedJob(
                external_job_id=f"ashby_{external_id}",
                company_name=company,
                title=title,
                description=desc,
                raw_location=raw_loc or "London, United Kingdom",
                source_job_url=source_url,
                company_career_url=f"https://jobs.ashbyhq.com/{raw_data.get('_company_slug', '')}",
                apply_url=apply_url,
                posted_date=posted_date,
                employment_type=raw_data.get("employmentType", "Full-time"),
                source_name="Ashby ATS Feed",
                source_type="ATS_ASHBY"
            )
        except Exception as e:
            logger.error(f"[Ashby] Error parsing job: {e}")
            return None
