import json
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from backend.app.database.config import settings
from backend.app.models.source import JobSource
from backend.app.models.company import Company
from backend.app.utils.text_normalizer import normalize_company_name

logger = logging.getLogger(__name__)

# Curated catalog of top UK tech employers, fintechs, and high-growth startups
UK_TECH_SOURCE_CATALOG = {
    "greenhouse": [
        "monzo", "deliveroo", "snyk", "checkout", "synthesia", "multiverse", "cleo",
        "thoughtmachine", "improbable", "cazoo", "depop", "onfido", "zego", "gousto",
        "marshmallow", "cmrsurgical", "darktrace", "oaknorth", "zilch", "tide", "curve",
        "blockchain", "primer", "paddle", "hopin", "beam", "wayve", "tractable",
        "matillion", "truelayer", "motorway", "lendable", "harrisonai", "starlingbank",
        "secretescapes", "tesco", "ocado", "sky", "babylonhealth"
    ],
    "lever": [
        "gocardless", "spotify", "atlan", "kroo", "pleo", "kraken", "revolut",
        "sensat", "fluro", "habito", "moneybox", "cauldron", "juro", "yulife",
        "kytopen", "flux", "babbel", "cuvva", "complyadvantage"
    ],
    "ashby": [
        "linear", "ramp", "postman", "deel", "ironclad", "glide", "incidentio",
        "retool", "vanta", "brex", "elevenlabs",
        "omnipresent", "baseten", "scaleai", "modal", "remote"
    ],
    "workable": [
        "vitality", "transfergo", "chip", "currensea", "proximie", "koyo",
        "wearenova", "inflow", "plum", "rooster", "unmind", "freetrade",
        "tails", "huma"
    ],
    "smartrecruiters": [
        "smartrecruiters", "visa", "bosch", "atos", "dxc", "experian",
        "equifax", "publicisgroupe", "vodafone", "dentsuaegisnetwork"
    ]
}

class SourceDiscoveryService:
    @classmethod
    async def probe_ats_slug(cls, provider: str, slug: str) -> bool:
        """
        Asynchronously probes whether a company slug is valid and public on the specified ATS.
        """
        slug = slug.strip().lower()
        if not slug:
            return False

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UKSEJobFinder/1.0",
            "Accept": "application/json"
        }

        url_map = {
            "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            "lever": f"https://api.lever.co/v0/postings/{slug}?mode=json",
            "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            "workable": f"https://apply.workable.com/api/v3/accounts/{slug}/jobs",
            "smartrecruiters": f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        }

        url = url_map.get(provider.lower())
        if not url:
            return False

        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    try:
                        data = res.json()
                        if isinstance(data, list) and len(data) > 0:
                            return True
                        elif isinstance(data, dict):
                            jobs = data.get("jobs", []) or data.get("postings", []) or data.get("results", [])
                            if isinstance(jobs, list) and len(jobs) > 0:
                                return True
                            elif "jobs" in data or "title" in data or "name" in data or "departments" in data:
                                return True
                    except Exception:
                        return False
        except Exception as e:
            logger.debug(f"Probe failed for {provider}/{slug}: {e}")

        return False

    @classmethod
    async def query_gemini_for_sources(cls, api_key: str) -> List[Dict[str, str]]:
        """
        Queries Google Gemini API for newly hiring UK Software Engineering companies and their ATS slugs.
        """
        discovered = []
        prompt = (
            "List 20 prominent tech companies, scaleups, and fintechs with software engineering offices in the UK (London, Manchester, Cambridge, Bristol, Oxford, Edinburgh). "
            "For each company, identify their ATS job board provider ('greenhouse', 'lever', 'ashby', 'workable', or 'smartrecruiters') and their exact public job board company slug identifier. "
            "Output ONLY valid JSON as a list of objects with keys: 'company_name', 'provider', 'company_slug'. No surrounding markdown."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(text)
                        if isinstance(parsed, list):
                            for item in parsed:
                                if isinstance(item, dict) and "provider" in item and "company_slug" in item:
                                    discovered.append({
                                        "company_name": item.get("company_name", item.get("company_slug")).title(),
                                        "provider": item.get("provider", "").lower().strip(),
                                        "company_slug": item.get("company_slug", "").lower().strip()
                                    })
            logger.info(f"Gemini API returned {len(discovered)} candidate UK job sources.")
        except Exception as e:
            logger.warning(f"Error querying Gemini API for job sources: {e}")

        return discovered

    @classmethod
    async def query_openai_for_sources(cls, api_key: str) -> List[Dict[str, str]]:
        """
        Queries OpenAI API for UK Software Engineering company ATS feeds.
        """
        discovered = []
        prompt = (
            "List 20 prominent tech companies, scaleups, and fintechs hiring software engineers in the UK. "
            "For each company, identify their ATS job board ('greenhouse', 'lever', 'ashby', 'workable', 'smartrecruiters') and their exact public board slug. "
            "Output ONLY valid JSON as a list of objects with keys: 'company_name', 'provider', 'company_slug'."
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    parsed = json.loads(content)
                    items = parsed if isinstance(parsed, list) else parsed.get("companies", parsed.get("sources", []))
                    for item in items:
                        if isinstance(item, dict) and "provider" in item and "company_slug" in item:
                            discovered.append({
                                "company_name": item.get("company_name", item.get("company_slug")).title(),
                                "provider": item.get("provider", "").lower().strip(),
                                "company_slug": item.get("company_slug", "").lower().strip()
                            })
            logger.info(f"OpenAI API returned {len(discovered)} candidate UK job sources.")
        except Exception as e:
            logger.warning(f"Error querying OpenAI API for job sources: {e}")

        return discovered

    @classmethod
    async def run_discovery_cycle(cls, db: Session, use_ai: bool = True) -> Dict[str, Any]:
        """
        Executes a complete automated source discovery cycle:
        1. Gathers candidate company slugs from AI (Gemini/OpenAI) + curated high-yield UK tech catalog.
        2. Probes the ATS APIs to ensure they are live and valid.
        3. Appends verified slugs to the corresponding JobSource records in the database.
        4. Registers company records into job.Companies.
        """
        logger.info("Starting Automated UK Job Source Discovery Cycle...")
        candidates: List[Dict[str, str]] = []

        # 1. Gather from Curated Catalog
        for provider, slugs in UK_TECH_SOURCE_CATALOG.items():
            for slug in slugs:
                candidates.append({
                    "company_name": slug.title(),
                    "provider": provider,
                    "company_slug": slug
                })

        # 2. Gather from AI if configured
        if use_ai:
            if settings.GEMINI_API_KEY:
                ai_sources = await cls.query_gemini_for_sources(settings.GEMINI_API_KEY)
                candidates.extend(ai_sources)
            elif settings.OPENAI_API_KEY:
                ai_sources = await cls.query_openai_for_sources(settings.OPENAI_API_KEY)
                candidates.extend(ai_sources)

        # 3. Ensure providers exist in database
        provider_sources: Dict[str, JobSource] = {}
        for p in ["greenhouse", "lever", "ashby", "workable", "smartrecruiters"]:
            src = db.query(JobSource).filter(JobSource.ProviderName == p).first()
            if not src:
                src = JobSource(
                    SourceName=f"{p.title()} ATS Feed",
                    SourceType=f"ATS_{p.upper()}",
                    ProviderName=p,
                    ConfigJson=json.dumps({"companies": []}),
                    IsEnabled=True
                )
                db.add(src)
                db.flush()
            provider_sources[p] = src

        added_companies = []
        already_tracked = 0
        failed_probes = 0

        for candidate in candidates:
            provider = candidate["provider"].lower()
            slug = candidate["company_slug"].lower().strip()
            name = candidate.get("company_name", slug.title())

            if provider not in provider_sources or not slug:
                continue

            src = provider_sources[provider]
            config = {}
            if src.ConfigJson:
                try:
                    config = json.loads(src.ConfigJson)
                except Exception:
                    config = {}

            existing_companies: List[str] = [c.lower() for c in config.get("companies", [])]

            if slug in existing_companies:
                already_tracked += 1
                continue

            # Probe ATS endpoint
            is_valid = await cls.probe_ats_slug(provider, slug)
            if not is_valid:
                failed_probes += 1
                continue

            # Add to source config
            existing_companies.append(slug)
            config["companies"] = sorted(list(set(existing_companies)))
            src.ConfigJson = json.dumps(config)
            src.UpdatedAt = datetime.utcnow()

            # Ensure company record exists in DB
            norm_name = normalize_company_name(name)
            comp = db.query(Company).filter(Company.NormalizedCompanyName == norm_name).first()
            if not comp:
                comp = Company(
                    CompanyName=name,
                    NormalizedCompanyName=norm_name,
                    SponsorLicenceStatus="UNKNOWN"
                )
                db.add(comp)

            added_companies.append({
                "company_name": name,
                "company_slug": slug,
                "provider": provider
            })

        db.commit()
        logger.info(f"Discovery Cycle complete: Added {len(added_companies)} new sources, {already_tracked} already tracked, {failed_probes} inactive.")

        return {
            "status": "SUCCESS",
            "new_sources_added": len(added_companies),
            "already_tracked": already_tracked,
            "failed_probes": failed_probes,
            "added_companies": added_companies[:30]
        }

    @classmethod
    async def add_custom_company(cls, db: Session, provider: str, company_slug: str, company_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Allows manually adding or probing a single custom ATS company source.
        """
        provider = provider.lower().strip()
        slug = company_slug.lower().strip()
        name = company_name.strip() if company_name else slug.title()

        if provider not in ["greenhouse", "lever", "ashby", "workable", "smartrecruiters"]:
            raise ValueError(f"Unsupported ATS provider '{provider}'. Must be greenhouse, lever, ashby, workable, or smartrecruiters.")

        if not slug:
            raise ValueError("Company slug cannot be empty.")

        # Probe ATS
        is_valid = await cls.probe_ats_slug(provider, slug)
        if not is_valid:
            logger.warning(f"Probe warning for custom source {provider}/{slug}, registering anyway.")

        src = db.query(JobSource).filter(JobSource.ProviderName == provider).first()
        if not src:
            src = JobSource(
                SourceName=f"{provider.title()} ATS Feed",
                SourceType=f"ATS_{provider.upper()}",
                ProviderName=provider,
                ConfigJson=json.dumps({"companies": []}),
                IsEnabled=True
            )
            db.add(src)
            db.flush()

        config = {}
        if src.ConfigJson:
            try:
                config = json.loads(src.ConfigJson)
            except Exception:
                config = {}

        companies_list = config.get("companies", [])
        if slug not in [c.lower() for c in companies_list]:
            companies_list.append(slug)
            config["companies"] = companies_list
            src.ConfigJson = json.dumps(config)
            src.UpdatedAt = datetime.utcnow()

        norm_name = normalize_company_name(name)
        comp = db.query(Company).filter(Company.NormalizedCompanyName == norm_name).first()
        if not comp:
            comp = Company(
                CompanyName=name,
                NormalizedCompanyName=norm_name,
                SponsorLicenceStatus="UNKNOWN"
            )
            db.add(comp)

        db.commit()

        return {
            "success": True,
            "message": f"Successfully registered '{name}' ({slug}) under {provider.title()}!",
            "provider": provider,
            "company_slug": slug,
            "is_valid_ats": is_valid
        }
