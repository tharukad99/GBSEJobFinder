import re
from typing import NamedTuple, Optional, Tuple

class LocationInfo(NamedTuple):
    is_uk: bool
    city: Optional[str]
    region: Optional[str]
    country: str
    remote_type: str # 'On-site', 'Hybrid', 'Remote UK', 'Unknown'
    normalized_location: str

UK_CITIES = {
    "london": ("London", "Greater London"),
    "manchester": ("Manchester", "North West"),
    "greater manchester": ("Manchester", "North West"),
    "salford": ("Manchester", "North West"),
    "birmingham": ("Birmingham", "West Midlands"),
    "leeds": ("Leeds", "Yorkshire"),
    "bristol": ("Bristol", "South West"),
    "edinburgh": ("Edinburgh", "Scotland"),
    "glasgow": ("Glasgow", "Scotland"),
    "belfast": ("Belfast", "Northern Ireland"),
    "cardiff": ("Cardiff", "Wales"),
    "cambridge": ("Cambridge", "East of England"),
    "oxford": ("Oxford", "South East"),
    "reading": ("Reading", "South East"),
    "sheffield": ("Sheffield", "Yorkshire"),
    "newcastle": ("Newcastle", "North East"),
    "liverpool": ("Liverpool", "North West"),
    "nottingham": ("Nottingham", "East Midlands"),
    "southampton": ("Southampton", "South East"),
    "bath": ("Bath", "South West"),
    "brighton": ("Brighton", "South East"),
    "milton keynes": ("Milton Keynes", "South East"),
    "york": ("York", "Yorkshire"),
    "aberdeen": ("Aberdeen", "Scotland"),
    "swindon": ("Swindon", "South West"),
    "warrington": ("Warrington", "North West"),
    "chester": ("Chester", "North West"),
    "preston": ("Preston", "North West"),
    "bolton": ("Bolton", "North West"),
    "stockport": ("Stockport", "North West"),
}

UK_REGIONS = [
    "north west", "north east", "yorkshire", "west midlands", "east midlands",
    "east of england", "south east", "south west", "greater london",
    "scotland", "wales", "northern ireland", "england", "great britain", "uk", "united kingdom"
]

NON_UK_INDICATORS = [
    r"\busa\b", r"\bunited states\b", r"\bcalifornia\b", r"\bnew york\b", r"\btexas\b",
    r"\bsan francisco\b", r"\baustin\b", r"\bseattle\b", r"\bindia\b", r"\bbangalore\b",
    r"\bhyderabad\b", r"\bpune\b", r"\bgermany\b", r"\bberlin\b", r"\bmunich\b",
    r"\bpoland\b", r"\bkrakow\b", r"\bwarsaw\b", r"\bcanada\b", r"\btoronto\b",
    r"\bvancouver\b", r"\baustralia\b", r"\bsydney\b", r"\bmelbourne\b", r"\bnetherlands\b",
    r"\bamsterdam\b", r"\bfrance\b", r"\bparis\b", r"\bspain\b", r"\bmadrid\b",
    r"\bireland\b", r"\bdublin\b", r"\bsingapore\b", r"\bswitzerland\b", r"\bzurich\b"
]

def parse_location(location_str: Optional[str], description: Optional[str] = "") -> LocationInfo:
    """
    Parses and validates whether a job is located in the UK and identifies
    the specific city, region, and working arrangement (Remote UK, Hybrid, On-site).
    """
    if not location_str:
        location_str = ""
    
    loc_lower = location_str.lower().strip()
    desc_lower = (description or "")[:1000].lower()
    combined = f"{loc_lower} {desc_lower}"

    # Check for explicit non-UK locations
    for pattern in NON_UK_INDICATORS:
        if re.search(pattern, loc_lower):
            # If it explicitly mentions UK or London/Manchester alongside, double check
            if not ("uk" in loc_lower or "united kingdom" in loc_lower or "london" in loc_lower or "manchester" in loc_lower):
                return LocationInfo(
                    is_uk=False,
                    city=None,
                    region=None,
                    country="Non-UK",
                    remote_type="Unknown",
                    normalized_location=location_str.strip() or "Overseas"
                )

    # Determine Remote / Hybrid / On-site status
    remote_type = "Unknown"
    is_remote = bool(re.search(r"\b(remote|work from home|wfh|telecommute|anywhere in the uk|remote uk|uk remote)\b", loc_lower))
    is_hybrid = bool(re.search(r"\b(hybrid|flexible|split between home and office|x days in office|days a week in the office)\b", loc_lower))
    
    if not (is_remote or is_hybrid):
        # Check first part of description
        if re.search(r"\b(remote (uk|within the uk|in the uk|based in the uk)|100% remote|fully remote)\b", desc_lower):
            is_remote = True
        elif re.search(r"\b(hybrid role|hybrid working|hybrid setup|2-3 days in the office)\b", desc_lower):
            is_hybrid = True

    if is_hybrid:
        remote_type = "Hybrid"
    elif is_remote:
        remote_type = "Remote UK"
    elif any(city in loc_lower for city in UK_CITIES) or any(reg in loc_lower for reg in UK_REGIONS):
        remote_type = "On-site"

    # Identify City and Region
    found_city = None
    found_region = None

    for city_key, (city_name, region_name) in UK_CITIES.items():
        if re.search(r"\b" + re.escape(city_key) + r"\b", loc_lower):
            found_city = city_name
            found_region = region_name
            break

    if not found_region:
        for reg in UK_REGIONS:
            if re.search(r"\b" + re.escape(reg) + r"\b", loc_lower):
                found_region = reg.title()
                break

    # Determine if it's UK
    is_uk = False
    if found_city or found_region:
        is_uk = True
    elif "united kingdom" in loc_lower or "uk" in loc_lower or "great britain" in loc_lower or "england" in loc_lower:
        is_uk = True
    elif remote_type == "Remote UK":
        is_uk = True

    # Construct normalized location display string
    if found_city and found_region and found_city != found_region:
        normalized_loc = f"{found_city}, {found_region}, UK"
    elif found_city:
        normalized_loc = f"{found_city}, UK"
    elif found_region:
        normalized_loc = f"{found_region}, UK"
    elif remote_type == "Remote UK":
        normalized_loc = "Remote, United Kingdom"
    elif is_uk:
        normalized_loc = location_str.strip() or "United Kingdom"
    else:
        normalized_loc = location_str.strip() or "Unknown"

    return LocationInfo(
        is_uk=is_uk,
        city=found_city,
        region=found_region,
        country="United Kingdom" if is_uk else "Unknown",
        remote_type=remote_type,
        normalized_location=normalized_loc
    )
