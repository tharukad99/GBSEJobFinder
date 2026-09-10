import re
from typing import List, Tuple, Dict, Set, Optional

# Target allowed title patterns (inclusive of all Senior, Lead, Principal, Staff, and SE roles)
ALLOWED_TITLE_PATTERNS = [
    r"software\s+(engineer|developer|programmer|architect)",
    r"full\s*stack\s+(engineer|developer|software\s+engineer)",
    r"\.net\s+(engineer|developer|software\s+engineer|architect)",
    r"c#\s+(engineer|developer|software\s+engineer)",
    r"backend\s+(engineer|developer|software\s+engineer)",
    r"frontend\s+(engineer|developer|software\s+engineer|web\s+developer)",
    r"software\s+development\s+engineer",
    r"application\s+(developer|engineer)",
    r"web\s+application\s+(developer|engineer)",
    r"full\s*stack\s+engineer",
    r"web\s+developer",
    r"\bdeveloper\b",
    r"\bsoftware\s+engineer\b",
    r"\bsoftware\s+developer\b",
    r"\bsenior\s+(software\s+)?(engineer|developer|architect)\b",
    r"\bsenior\s+engineer\b",
    r"\bprincipal\s+(software\s+)?(engineer|developer)\b",
    r"\bstaff\s+(software\s+)?(engineer|developer)\b",
    r"\blead\s+(software\s+)?(engineer|developer)\b",
    r"\bplatform\s+engineer\b",
    r"\bcloud\s+(engineer|developer)\b",
    r"\bdevops\s+engineer\b",
    r"\bsite\s+reliability\s+engineer\b",
    r"\bsre\b",
    r"\bdata\s+engineer\b",
    r"\btech(nical)?\s+lead\b",
    r"\bsoftware\s+architect\b",
    r"\bsolutions?\s+architect\b",
    r"\bqa\s+engineer\b",
    r"\bsdet\b",
    r"\btest\s+automation\s+engineer\b",
    r"\bautomation\s+engineer\b",
]


# Strict exclusions
EXCLUDED_TITLE_PATTERNS = [
    r"\bit\s+support\b",
    r"\bhelpdesk\b",
    r"\bbusiness\s+analyst\b",
    r"\bproject\s+manager\b",
    r"\bproduct\s+manager\b",
    r"\bproduct\s+owner\b",
    r"\bnetwork\s+engineer\b",
    r"\bhardware\s+engineer\b",
    r"\bscrum\s+master\b",
    r"\bsales\s+engineer\b",
    r"\bdata\s+analyst\b",
    r"\btechnical\s+recruiter\b",
    r"\bmarketing\b",
    r"\baccountant\b",
    r"\blegal\s+counsel\b",
]

# Senior / Lead tags (to de-prioritize in experience scoring)
SENIOR_PATTERNS = [
    r"\bsenior\b", r"\bsr\.?\b", r"\blead\b", r"\bprincipal\b", 
    r"\bstaff\b", r"\barchitect\b", r"\bhead\s+of\b", r"\bmanager\b", r"\bdirector\b"
]

PRIMARY_SKILLS = {
    "C#": [r"(?i)(?:^|[\s,.(/])c#(?=[\s,.)/]|$)", r"\bc-sharp\b"],
    ".NET": [r"(?i)(?:^|[\s,.(/])\.net(?=[\s,.)/]|$)", r"\bdotnet\b", r"\basp\.net\b"],
    ".NET Core": [r"(?i)\.net\s+core\b", r"\bdotnet\s+core\b"],
    "ASP.NET Core": [r"(?i)asp\.net\s+core\b"],
    "React": [r"\breact\b", r"\breact\.js\b", r"\breactjs\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b", r"\bes6\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
    "SQL Server": [r"\bsql\s+server\b", r"\bmssql\b", r"\bms-sql\b", r"\bt-sql\b"],
    "MSSQL": [r"\bmssql\b", r"\bms\s+sql\b"],
    "Azure": [r"\bazure\b", r"\bmicrosoft\s+azure\b"],
    "Python": [r"\bpython\b", r"\bpython3\b", r"\bdjango\b", r"\bfastapi\b", r"\bflask\b"]
}

SECONDARY_SKILLS = {
    "REST API": [r"\brest\b", r"\brestful\b", r"\brest\s+apis?\b", r"\bweb\s+apis?\b"],
    "Entity Framework": [r"\bentity\s+framework\b", r"\bef\s+core\b"],
    "Azure SQL": [r"\bazure\s+sql\b"],
    "Git": [r"\bgit\b"],
    "GitHub": [r"\bgithub\b"],
    "CI/CD": [r"\bci/cd\b", r"\bci\s*-\s*cd\b", r"\bpipelines?\b", r"\bgithub\s+actions\b"],
    "Docker": [r"\bdocker\b", r"\bcontainers?\b"],
    "Microservices": [r"\bmicroservices?\b", r"\bmicro-services?\b"],
    "HTML": [r"\bhtml\b", r"\bhtml5\b"],
    "CSS": [r"\bcss\b", r"\bcss3\b", r"\bsass\b", r"\bscss\b"],
    "Node.js": [r"\bnode\.?js\b", r"\bnodejs\b"],
    "FastAPI": [r"\bfastapi\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "AWS": [r"\baws\b", r"\bamazon\s+web\s+services\b"],
    "SQL": [r"\bsql\b", r"\bpostgres\b", r"\bpostgresql\b", r"\bmysql\b"]
}

def is_target_job_title(title: str) -> bool:
    """
    Validates if job title matches allowed Software Engineering roles
    and does NOT contain excluded titles (IT support, PM, BA, etc.).
    """
    if not title:
        return False
    
    t_lower = title.lower()

    # Check exclusions first
    for exc in EXCLUDED_TITLE_PATTERNS:
        if re.search(exc, t_lower):
            return False

    # Check target patterns
    for pattern in ALLOWED_TITLE_PATTERNS:
        if re.search(pattern, t_lower):
            return True

    return False

def determine_experience_level(title: str, description: Optional[str] = "") -> str:
    """Detects if job is Junior, Mid, or Senior/Lead."""
    combined = f"{title} {description or ''}".lower()
    
    if any(re.search(p, title.lower()) for p in SENIOR_PATTERNS):
        return "Senior"
    
    if re.search(r"\b(junior|graduate|entry\s+level|associate|trainee|apprentice)\b", combined):
        return "Junior"
    
    return "Mid"

def extract_technologies(title: str, description: Optional[str] = "") -> Dict[str, List[str]]:
    """Extracts identified primary and secondary tech keywords from title and text."""
    combined = f"{title} {description or ''}"
    
    matched_primary: List[str] = []
    matched_secondary: List[str] = []

    for tech_name, patterns in PRIMARY_SKILLS.items():
        if any(re.search(p, combined, re.IGNORECASE) for p in patterns):
            matched_primary.append(tech_name)

    for tech_name, patterns in SECONDARY_SKILLS.items():
        if any(re.search(p, combined, re.IGNORECASE) for p in patterns):
            matched_secondary.append(tech_name)

    return {
        "primary": matched_primary,
        "secondary": matched_secondary,
        "all": list(set(matched_primary + matched_secondary))
    }

def calculate_match_score(
    title: str,
    matched_skills: Dict[str, List[str]],
    sponsorship_status: str,
    city: Optional[str],
    region: Optional[str],
    remote_type: str,
    experience_level: str
) -> int:
    """
    Calculates deterministic Job Match Score from 0 to 100 based on:
    - Sponsorship Status (up to 35 points)
    - Matching Technologies (up to 30 points)
    - Role & Experience Level (up to 20 points, favouring Junior & Mid)
    - Location Preference (up to 15 points, favouring London, Manchester, Remote UK)
    """
    score = 0

    # 1. Sponsorship Score (35%)
    if sponsorship_status == "CONFIRMED":
        score += 35
    elif sponsorship_status == "MAY_OFFER":
        score += 25
    elif sponsorship_status == "UNKNOWN":
        score += 10
    else: # NO_SPONSORSHIP
        score += 0

    # 2. Technology Match Score (30%)
    # Primary skills: up to 24 pts (6 pts per matched primary skill, max 4)
    prim_count = len(matched_skills.get("primary", []))
    score += min(prim_count * 6, 24)

    # Secondary skills: up to 6 pts (2 pts per matched secondary skill, max 3)
    sec_count = len(matched_skills.get("secondary", []))
    score += min(sec_count * 2, 6)

    # 3. Role & Experience Level Score (20%)
    # Equal full weight across all valid engineering levels
    if experience_level in ("Senior", "Lead", "Principal", "Staff", "Junior", "Mid"):
        score += 20
    else:
        score += 15


    # 4. Location Preference Score (15%)
    city_lower = (city or "").lower()
    reg_lower = (region or "").lower()
    
    if city_lower == "london" or reg_lower == "greater london":
        score += 15
    elif city_lower == "manchester" or "north west" in reg_lower:
        score += 15
    elif remote_type == "Remote UK":
        score += 15
    elif remote_type == "Hybrid":
        score += 12
    else: # Other UK
        score += 10

    return min(max(score, 0), 100)

def calculate_quality_score(
    source_type: str,
    has_apply_url: bool,
    description_len: int,
    has_posted_date: bool,
    has_sponsorship_evidence: bool,
    is_company_licensed: bool
) -> int:
    """Calculates internal confidence/quality score (0-100)."""
    score = 0
    if "ATS" in source_type or "COMPANY" in source_type:
        score += 25
    else:
        score += 10
    
    if has_apply_url:
        score += 20
    if description_len > 200:
        score += 20
    if has_posted_date:
        score += 15
    if has_sponsorship_evidence or is_company_licensed:
        score += 20

    return min(max(score, 0), 100)
