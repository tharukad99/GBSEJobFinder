import os
import json
import csv
import logging
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
from backend.app.utils.text_normalizer import normalize_company_name

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "sponsor_register.json"

# Comprehensive initial seed of UK registered sponsors (Worker and Temporary Worker routes)
DEFAULT_SPONSORS = [
    {"name": "Monzo Bank Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Deliveroo UK Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Starling Bank Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Revolut Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Snyk Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Checkout Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Thought Machine Group Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Spotify UK Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "GoCardless Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Skyscanner Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Edinburgh"},
    {"name": "Squareup Europe Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Visa Europe Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Cisco International Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Feltham"},
    {"name": "Bupa Care Services", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Publicis Groupe UK Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Deel UK Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Postman UK Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Linear Technology Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Pleo Technologies UK Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Kroo Bank Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Atlan UK Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Kraken Technologies Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Synthesia Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Motorway Online Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Marshmallow Financial Services Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Depop Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Cleo AI Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Microsoft Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Reading"},
    {"name": "Google UK Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Amazon UK Services Ltd", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Meta Platforms Ireland Limited (UK Branch)", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Apple Europe Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Bloomberg LP", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Goldman Sachs International", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "JPMorgan Chase Bank, N.A.", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Barclays Services Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "NatWest Group Plc", "route": "Skilled Worker", "rating": "A rating", "town": "Edinburgh"},
    {"name": "HSBC Global Services (UK) Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Lloyds Bank Plc", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
    {"name": "Sage (UK) Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Newcastle"},
    {"name": "Softcat PLC", "route": "Skilled Worker", "rating": "A rating", "town": "Marlow"},
    {"name": "Auto Trader Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Manchester"},
    {"name": "The Hut Group Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Manchester"},
    {"name": "Booking.com Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Manchester"},
    {"name": "ARM Limited", "route": "Skilled Worker", "rating": "A rating", "town": "Cambridge"},
    {"name": "Wise Payments Limited", "route": "Skilled Worker", "rating": "A rating", "town": "London"},
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
        """Loads sponsor register into memory indexed by normalized company name."""
        try:
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            if DATA_FILE.exists():
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    sponsors = json.load(f)
            else:
                sponsors = DEFAULT_SPONSORS
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(sponsors, f, indent=2)

            self._sponsors_cache = {}
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
        # We ensure the token has sufficient length to prevent false positives (min 4 chars)
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
        Optionally download and update the sponsor register from GOV.UK CSV feed.
        """
        # Official Home Office register CSV URL pattern
        url = csv_url or "https://assets.publishing.service.gov.uk/media/65df19f563630800115dbde5/2024-02-28_-_Worker_and_Temporary_Worker.csv"
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    lines = response.text.splitlines()
                    reader = csv.reader(lines)
                    header = next(reader, None)
                    
                    new_sponsors = []
                    for row in reader:
                        if len(row) >= 4:
                            org_name = row[0].strip()
                            town = row[1].strip() if len(row) > 1 else ""
                            route = row[3].strip() if len(row) > 3 else "Skilled Worker"
                            rating = row[2].strip() if len(row) > 2 else "A rating"
                            if org_name and ("Worker" in route or "Skilled" in route):
                                new_sponsors.append({
                                    "name": org_name,
                                    "town": town,
                                    "route": route,
                                    "rating": rating
                                })

                    if new_sponsors:
                        with open(DATA_FILE, "w", encoding="utf-8") as f:
                            json.dump(new_sponsors, f, indent=2)
                        self._load_sponsors()
                        return len(new_sponsors)
        except Exception as e:
            logger.warning(f"Could not fetch live CSV from GOV.UK ({e}). Keeping active dataset.")
        return len(self._sponsors_cache)

sponsor_register = SponsorRegisterService()
