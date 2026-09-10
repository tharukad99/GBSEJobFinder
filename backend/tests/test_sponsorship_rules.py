import pytest
from backend.app.services.sponsorship_service import evaluate_sponsorship

def test_explicit_negative_sponsorship_overrules_sponsor_register():
    # Monzo Bank is on the sponsor register, but if job explicitly denies sponsorship:
    desc = "You will work on our backend systems. Note: We are unable to provide visa sponsorship for this specific position."
    result = evaluate_sponsorship("Monzo Bank Limited", "Software Engineer", desc)
    
    assert result.status == "NO_SPONSORSHIP"
    assert result.confidence_level == "High"
    assert "unable to provide" in (result.evidence_text or "").lower()

def test_sponsor_register_match_without_explicit_job_mention_is_may_offer():
    # Deliveroo is on the sponsor register, but job advert mentions no visa info:
    desc = "We are looking for a C# / .NET Developer to build cloud microservices."
    result = evaluate_sponsorship("Deliveroo UK Limited", "Software Developer", desc)
    
    assert result.status == "MAY_OFFER"
    assert result.company_is_licensed is True
    assert result.confidence_level == "Medium"
    # Must NOT be CONFIRMED!
    assert result.status != "CONFIRMED"

def test_explicit_positive_sponsorship_is_confirmed():
    desc = "Great opportunity for full stack engineers. Skilled Worker visa sponsorship is available for eligible candidates."
    result = evaluate_sponsorship("Some Random Tech Co", "Full Stack Developer", desc)
    
    assert result.status == "CONFIRMED"
    assert result.confidence_level == "High"
    assert "sponsorship is available" in (result.evidence_text or "").lower()

def test_unknown_company_and_no_mention_is_unknown():
    desc = "Standard software engineer vacancy with React and TypeScript."
    result = evaluate_sponsorship("Completely Unregistered Non-Sponsor Org", "Frontend Engineer", desc)
    
    assert result.status == "UNKNOWN"
    assert result.company_is_licensed is False
    assert result.confidence_level == "Low"
