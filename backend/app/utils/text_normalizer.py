import re
import html
from typing import Optional

LEGAL_SUFFIXES = [
    r"\blimited\b", r"\bltd\b", r"\bplc\b", r"\bllc\b", r"\bllp\b", r"\blp\b", r"\binc\b", r"\bcorp\b", 
    r"\bcorporation\b", r"\buk\b", r"\bgroup\b", r"\btechnologies\b", 
    r"\btechnology\b", r"\bservices\b", r"\bsolutions\b", r"\bsoftware\b",
    r"\bholdings\b", r"\bco\b", r"\bcompany\b", r"\binternational\b", r"\bglobal\b"
]

def clean_html(raw_html: Optional[str]) -> str:
    """Strip HTML tags, unescape entities, and clean up excess whitespace."""
    if not raw_html:
        return ""
    # Unescape HTML entities
    text = html.unescape(raw_html)
    # Remove script and style elements
    text = re.sub(r"<(script|style).*?>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags and line breaks with spaces/newlines
    text = re.sub(r"<(p|br|div|li|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Replace multiple spaces/newlines with single space/newline
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()

def normalize_company_name(name: Optional[str]) -> str:
    """
    Normalizes company names for deduplication and sponsor register lookup.
    Example: 'Monzo Bank Limited (UK)' -> 'monzo bank'
    """
    if not name:
        return ""
    
    text = name.lower().strip()
    
    # Remove parentheses and contents if they contain 'uk', 'ltd', etc.
    text = re.sub(r"\([^)]*\)", "", text)
    
    # Remove punctuation except alphanumeric and whitespace
    text = re.sub(r"[^\w\s]", " ", text)
    
    # Remove legal suffixes
    for suffix in LEGAL_SUFFIXES:
        text = re.sub(suffix, " ", text, flags=re.IGNORECASE)
        
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_job_title(title: Optional[str]) -> str:
    """
    Normalizes job titles for categorization and search.
    Example: 'Senior Full Stack .NET Developer - London / Remote' -> 'Full Stack .NET Developer'
    """
    if not title:
        return ""
    
    text = title.strip()
    # Remove common trailing tags like '(m/f/d)', '(Remote)', '- London', etc.
    text = re.sub(r"\((m/f/d|m/w/d|all genders|remote|hybrid|uk|london|manchester)\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[-–—/|]\s*(remote|hybrid|london|manchester|uk|full.?time|contract|permanent).*$", "", text, flags=re.IGNORECASE)
    # Collapse spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def create_duplicate_hash(company: str, title: str, location: str) -> str:
    """Generates an MD5/SHA256 duplicate fingerprint hash."""
    import hashlib
    norm_comp = normalize_company_name(company)
    norm_title = normalize_job_title(title).lower()
    norm_loc = location.lower().replace(" ", "").replace(",", "")
    
    # Also extract core role words (e.g. software engineer)
    fingerprint = f"{norm_comp}|{norm_title}|{norm_loc}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
