import re
from typing import NamedTuple, Optional, Tuple
from backend.app.services.sponsor_register_service import sponsor_register

class SponsorshipResult(NamedTuple):
    status: str # 'CONFIRMED', 'MAY_OFFER', 'NO_SPONSORSHIP', 'UNKNOWN'
    evidence_text: Optional[str]
    evidence_source: str
    confidence_level: str # 'High', 'Medium', 'Low'
    company_is_licensed: bool
    company_sponsor_route: Optional[str]
    company_sponsor_rating: Optional[str]

# Strict explicit negative indicators (Job says NO)
NEGATIVE_PATTERNS = [
    r"no\s+(visa\s+)?sponsorship(\s+is)?\s+available",
    r"sponsorship\s+(is\s+)?not\s+available",
    r"we\s+(are\s+)?(unable|cannot|can\s+not)\s+to\s+sponsor",
    r"we\s+(cannot|can\s+not)\s+provide\s+(visa\s+)?sponsorship",
    r"we\s+(are\s+)?unable\s+to\s+provide\s+(visa\s+)?sponsorship",
    r"cannot\s+sponsor\s+(visas?|work\s+permits?|candidates?|this\s+position)",
    r"must\s+already\s+have\s+(the\s+)?(right|permission|unrestricted\s+right)\s+to\s+work\s+in\s+the\s+uk",
    r"must\s+have\s+an\s+existing\s+right\s+to\s+work\s+in\s+the\s+uk",
    r"must\s+have\s+valid\s+uk\s+right\s+to\s+work\s+without\s+(visa\s+)?sponsorship",
    r"without\s+the\s+need\s+for\s+(visa\s+)?sponsorship",
    r"applicants?\s+requiring\s+sponsorship\s+will\s+not\s+be\s+considered",
    r"not\s+able\s+to\s+sponsor",
    r"not\s+offering\s+sponsorship",
    r"do\s+not\s+offer\s+(visa\s+)?sponsorship",
    r"we\s+do\s+not\s+sponsor",
    r"require\s+candidates\s+to\s+have\s+uk\s+work\s+authorisation",
    r"not\s+eligible\s+for\s+visa\s+sponsorship",
]

# Explicit positive indicators (Job says YES)
POSITIVE_PATTERNS = [
    r"skilled\s+worker\s+(visa\s+)?sponsorship\s+(is\s+)?available",
    r"visa\s+sponsorship\s+(is\s+)?available",
    r"sponsorship\s+(is\s+)?available\s+for\s+(this\s+role|eligible\s+candidates|the\s+right\s+candidate)",
    r"certificate\s+of\s+sponsorship\s+(is\s+)?available",
    r"skilled\s+worker\s+visa\s+(supported|offered|provided)",
    r"uk\s+visa\s+sponsorship\s+available",
    r"we\s+(can|are\s+able\s+to|do)\s+provide\s+(visa\s+)?sponsorship",
    r"we\s+(can|are\s+able\s+to)\s+sponsor\s+(skilled\s+worker|visas?|eligible\s+candidates|relocation)",
    r"visa\s+support\s+and\s+relocation\s+available",
    r"relocation\s+and\s+visa\s+sponsorship",
    r"sponsorship\s+is\s+supported",
    r"we\s+sponsor\s+skilled\s+worker\s+visas",
    r"eligible\s+for\s+skilled\s+worker\s+visa\s+sponsorship",
    r"can\s+offer\s+(visa\s+)?sponsorship",
    r"tier\s+2\s+/\s+skilled\s+worker\s+sponsorship",
]

def extract_evidence_sentence(text: str, match_pattern: str) -> str:
    """Extracts the sentence or surrounding context around a match."""
    sentences = re.split(r"(?<=[.!?\n])\s+", text)
    for sent in sentences:
        if re.search(match_pattern, sent, re.IGNORECASE):
            return sent.strip()
    return "Sponsorship requirement stated in job advert."

def evaluate_sponsorship(
    company_name: str,
    job_title: str,
    job_description: Optional[str]
) -> SponsorshipResult:
    """
    Evaluates sponsorship status strictly adhering to the specification:
    1. If job advert explicitly states negative sponsorship -> NO_SPONSORSHIP (High confidence)
    2. If job advert explicitly states positive sponsorship -> CONFIRMED (High confidence)
    3. If company is on UK Home Office sponsor register -> MAY_OFFER (Medium confidence)
    4. Otherwise -> UNKNOWN (Low confidence)
    """
    desc = (job_description or "")
    
    # 1. Check company sponsor licence on UK Home Office register
    company_sponsor_info = sponsor_register.lookup_company(company_name)
    is_licensed = company_sponsor_info is not None
    route = company_sponsor_info.get("route") if is_licensed else None
    rating = company_sponsor_info.get("rating") if is_licensed else None

    # 2. Check for explicit negative keywords in the job description
    for pattern in NEGATIVE_PATTERNS:
        match = re.search(pattern, desc, re.IGNORECASE)
        if match:
            evidence = extract_evidence_sentence(desc, pattern)
            return SponsorshipResult(
                status="NO_SPONSORSHIP",
                evidence_text=evidence,
                evidence_source="Job Description (Explicit exclusion)",
                confidence_level="High",
                company_is_licensed=is_licensed,
                company_sponsor_route=route,
                company_sponsor_rating=rating
            )

    # 3. Check for explicit positive keywords in the job description
    for pattern in POSITIVE_PATTERNS:
        match = re.search(pattern, desc, re.IGNORECASE)
        if match:
            evidence = extract_evidence_sentence(desc, pattern)
            return SponsorshipResult(
                status="CONFIRMED",
                evidence_text=evidence,
                evidence_source="Job Description (Explicit confirmation)",
                confidence_level="High",
                company_is_licensed=is_licensed,
                company_sponsor_route=route,
                company_sponsor_rating=rating
            )

    # 4. Check if company is on sponsor register
    if is_licensed:
        evidence = f"Company is listed on UK Government licensed sponsor register ({route}, {rating}). Job advert does not explicitly guarantee sponsorship."
        return SponsorshipResult(
            status="MAY_OFFER",
            evidence_text=evidence,
            evidence_source="UK Home Office Register of Licensed Sponsors",
            confidence_level="Medium",
            company_is_licensed=True,
            company_sponsor_route=route,
            company_sponsor_rating=rating
        )

    # 5. Unknown
    return SponsorshipResult(
        status="UNKNOWN",
        evidence_text="Insufficient sponsorship information in job advert and company not found on government register.",
        evidence_source="Default",
        confidence_level="Low",
        company_is_licensed=False,
        company_sponsor_route=None,
        company_sponsor_rating=None
    )
