import os
import re
import json
import csv
import logging
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
from backend.app.utils.text_normalizer import normalize_company_name

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE = DATA_DIR / "sponsor_register.json"

DEFAULT_SPONSORS = [
    {"name": "Monzo Bank Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Deliveroo UK Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Starling Bank Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Revolut Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Snyk Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Google UK Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Microsoft Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Reading"},
    {"name": "Amazon UK Services Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
]

class SponsorRegisterService:
    _instance = None
    _sponsors_cache: Dict[str, Dict[str, Any]] = {}
    _is_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SponsorRegisterService, cls).__new__(cls)
            cls._instance._load_sponsors()
        return cls._instance

    def _load_sponsors(self):
        """Loads sponsor register into memory indexed by normalized company name from CSV or JSON."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._sponsors_cache = {}

            # 1. Prefer full CSV register if present in data directory
            csv_files = list(DATA_DIR.glob("*.csv"))
            if csv_files:
                latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
                logger.info(f"Loading sponsor register from CSV: {latest_csv.name}")
                with open(latest_csv, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    
                    name_idx, town_idx, rating_idx, route_idx = 0, 1, 3, 4
                    if header:
                        header_lower = [h.strip().lower() for h in header]
                        for idx, h in enumerate(header_lower):
                            if "organisation" in h or "company" in h or (h == "name" and idx == 0):
                                name_idx = idx
                            elif "town" in h or "city" in h:
                                town_idx = idx
                            elif "rating" in h or "type" in h:
                                rating_idx = idx
                            elif "route" in h:
                                route_idx = idx

                    for row in reader:
                        if not row or len(row) <= name_idx:
                            continue
                        name = row[name_idx].strip()
                        town = row[town_idx].strip() if len(row) > town_idx else ""
                        rating = row[rating_idx].strip() if len(row) > rating_idx else "Worker (A rating)"
                        route = row[route_idx].strip() if len(row) > route_idx else "Skilled Worker"
                        
                        norm_name = normalize_company_name(name)
                        if norm_name:
                            # If already present, prefer 'Skilled Worker' route over temporary routes
                            if norm_name in self._sponsors_cache:
                                if "Skilled" in route and "Skilled" not in self._sponsors_cache[norm_name]["route"]:
                                    self._sponsors_cache[norm_name] = {
                                        "name": name,
                                        "town": town,
                                        "rating": rating,
                                        "route": route
                                    }
                            else:
                                self._sponsors_cache[norm_name] = {
                                    "name": name,
                                    "town": town,
                                    "rating": rating,
                                    "route": route
                                }
                self._is_loaded = True
                logger.info(f"Loaded {len(self._sponsors_cache)} UK licensed sponsors from CSV into memory.")
                return

            # 2. Fallback to sponsor_register.json or DEFAULT_SPONSORS
            if DATA_FILE.exists():
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    sponsors = json.load(f)
            else:
                sponsors = DEFAULT_SPONSORS
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(sponsors, f, indent=2)

            for item in sponsors:
                norm_name = normalize_company_name(item.get("name", ""))
                if norm_name:
                    self._sponsors_cache[norm_name] = {
                        "name": item.get("name"),
                        "route": item.get("route", "Skilled Worker"),
                        "rating": item.get("rating", "A rating"),
                        "town": item.get("town", "UK")
                    }
            self._is_loaded = True
            logger.info(f"Loaded {len(self._sponsors_cache)} UK licensed sponsors into memory.")
        except Exception as e:
            logger.error(f"Failed to load sponsor register: {e}")

    def lookup_company(self, raw_company_name: str) -> Optional[Dict[str, Any]]:
        """
        Looks up whether a company is on the UK Home Office register of licensed sponsors.
        Returns details if matched, None otherwise.
        """
        if not raw_company_name or not self._is_loaded:
            return None

        norm_query = normalize_company_name(raw_company_name)
        if not norm_query:
            return None

        # 1. Exact normalized match
        if norm_query in self._sponsors_cache:
            return self._sponsors_cache[norm_query]

        # 2. Key token matching (if query is a significant substring or vice versa)
        if len(norm_query) >= 4:
            for norm_key, details in self._sponsors_cache.items():
                if norm_query == norm_key:
                    return details
                # Check word boundaries
                if f" {norm_query} " in f" {norm_key} " or f" {norm_key} " in f" {norm_query} ":
                    return details

        return None

    def get_total_sponsors(self) -> int:
        return len(self._sponsors_cache)

    async def update_from_gov_uk(self, csv_url: Optional[str] = None) -> int:
        """
        Download and update the sponsor register from GOV.UK CSV feed.
        """
        url = csv_url
        try:
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                if not url:
                    # Dynamically discover latest CSV link from GOV.UK publication page
                    pub_page = await client.get("https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers")
                    if pub_page.status_code == 200:
                        csv_matches = re.findall(r'href=[\'"](https://assets\.publishing\.service\.gov\.uk/media/[^\'"]+\.csv)[\'"]', pub_page.text)
                        if csv_matches:
                            url = csv_matches[0]
                
                if not url:
                    url = "https://assets.publishing.service.gov.uk/media/6aa3bcb05f6e942efe37f156/SP_-_Worker_and_Temporary_Worker_Web_Register_-_2026-09-11.csv"

                response = await client.get(url)
                if response.status_code == 200:
                    csv_target = DATA_DIR / "SP_-_Worker_and_Temporary_Worker_Web_Register_latest.csv"
                    with open(csv_target, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    self._load_sponsors()
                    return len(self._sponsors_cache)
        except Exception as e:
            logger.warning(f"Could not fetch live CSV from GOV.UK ({e}). Keeping active dataset.")
        return len(self._sponsors_cache)

sponsor_register = SponsorRegisterService()
