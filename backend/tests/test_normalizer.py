import pytest
from backend.app.utils.text_normalizer import normalize_company_name, normalize_job_title, create_duplicate_hash

def test_normalize_company_names():
    assert normalize_company_name("ABC Technologies Ltd") == "abc"
    assert normalize_company_name("Monzo Bank Limited (UK)") == "monzo bank"
    assert normalize_company_name("Deliveroo UK Limited") == "deliveroo"
    assert normalize_company_name("Spotify UK Ltd.") == "spotify"
    assert normalize_company_name("Wise Payments Limited") == "wise payments"

def test_normalize_job_title():
    assert normalize_job_title("Software Engineer (m/f/d)") == "Software Engineer"
    assert normalize_job_title("Full Stack Developer - London") == "Full Stack Developer"
    assert normalize_job_title(".NET Software Engineer / Remote") == ".NET Software Engineer"

def test_duplicate_hash_consistency():
    hash1 = create_duplicate_hash("Monzo Bank Ltd", "Software Engineer", "London, UK")
    hash2 = create_duplicate_hash("Monzo Bank Limited", "Software Engineer (London)", "London, UK")
    assert hash1 == hash2
