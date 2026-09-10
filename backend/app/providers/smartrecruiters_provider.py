import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.providers.base_provider import BaseJobProvider, NormalizedJob
from backend.app.utils.text_normalizer import clean_html

logger = logging.getLogger(__name__)

class SmartRecruitersProvider(BaseJobProvider):
    def __init__(self):
        super().__init__("smartrecruiters", "https://api.smartrecruiters.com/v1/companies/")

    async def fetch_jobs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        companies = config.get("companies", ["square", "visa", "bupa", "publicisgroupe"])
        all_raw_jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 UKSEJobFinder/1.0",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
            for company_slug in companies:
                url = f"{self.base_url}{company_slug}/postings"
                try:
                    res = await client.get(url, params={"limit": 100})
                    if res.status_code == 200:
                        data = res.json()
                        jobs = data.get("content", [])
                        for j in jobs:
                            j["_company_slug"] = company_slug
                            all_raw_jobs.append(j)
                        logger.info(f"[SmartRecruiters] Fetched {len(jobs)} jobs for {company_slug}")
                    else:
                        logger.warning(f"[SmartRecruiters] Failed to fetch {company_slug}: HTTP {res.status_code}")
                except Exception as e:
                    logger.error(f"[SmartRecruiters] Error fetching {company_slug}: {e}")

        return all_raw_jobs

    def parse_job(self, raw_data: Dict[str, Any], company_name: str = "") -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_data.get("id", ""))
            title = raw_data.get("name", "").strip()
            if not external_id or not title:
                return None

            company = company_name or raw_data.get("company", {}).get("name") or raw_data.get("_company_slug", "").title()
            
            # Location
            loc = raw_data.get("location", {})
            city = loc.get("city", "")
            region = loc.get("region", "")
            country = loc.get("country", "")
            remote = loc.get("remote", False)
            raw_loc = f"{city}, {country}".strip(", ")
            if remote:
                raw_loc = f"Remote, {raw_loc}"

            # URLs
            posting_url = f"https://jobs.smartrecruiters.com/{raw_data.get('_company_slug', '')}/{external_id}"
            apply_url = posting_url

            # Dates
            created_on = raw_data.get("releasedDate") or raw_data.get("createdOn")
            posted_date = None
            if created_on:
                try:
                    posted_date = datetime.fromisoformat(created_on.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            type_of_emp = raw_data.get("typeOfEmployment", {}).get("label", "Full-time")

            return NormalizedJob(
                external_job_id=f"sr_{external_id}",
                company_name=company,
                title=title,
                description=f"Job vacancy at {company}: {title}. Apply directly via SmartRecruiters.",
                raw_location=raw_loc or "London, United Kingdom",
                source_job_url=posting_url,
                company_career_url=f"https://jobs.smartrecruiters.com/{raw_data.get('_company_slug', '')}",
                apply_url=apply_url,
                posted_date=posted_date,
                employment_type=type_of_emp,
                source_name="SmartRecruiters Feed",
                source_type="ATS_SMARTRECRUITERS"
            )
        except Exception as e:
            logger.error(f"[SmartRecruiters] Error parsing job: {e}")
            return None
