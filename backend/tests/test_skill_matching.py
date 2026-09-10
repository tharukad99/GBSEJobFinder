import pytest
from backend.app.services.matching_service import extract_technologies, calculate_match_score

def test_extract_technologies():
    title = "Senior C# .NET Core & React Developer"
    desc = "We use ASP.NET Core, TypeScript, SQL Server, Azure, and Docker with CI/CD pipelines."
    techs = extract_technologies(title, desc)
    
    assert "C#" in techs["primary"]
    assert ".NET Core" in techs["primary"]
    assert "React" in techs["primary"]
    assert "TypeScript" in techs["primary"]
    assert "SQL Server" in techs["primary"]
    assert "Azure" in techs["primary"]
    assert "Docker" in techs["secondary"]
    assert "CI/CD" in techs["secondary"]

def test_calculate_match_score_range_and_weights():
    techs = {
        "primary": ["C#", ".NET Core", "React", "Azure"],
        "secondary": ["Docker", "Git"],
        "all": ["C#", ".NET Core", "React", "Azure", "Docker", "Git"]
    }
    score_confirmed = calculate_match_score(
        title="Software Engineer",
        matched_skills=techs,
        sponsorship_status="CONFIRMED",
        city="London",
        region="Greater London",
        remote_type="Hybrid",
        experience_level="Mid"
    )
    assert 70 <= score_confirmed <= 100

    score_no_spons = calculate_match_score(
        title="Software Engineer",
        matched_skills=techs,
        sponsorship_status="NO_SPONSORSHIP",
        city="London",
        region="Greater London",
        remote_type="Hybrid",
        experience_level="Mid"
    )
    assert score_no_spons < score_confirmed
