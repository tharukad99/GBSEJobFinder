import pytest
from backend.app.services.matching_service import is_target_job_title, determine_experience_level

def test_allowed_software_engineering_titles():
    allowed_titles = [
        "Software Engineer",
        "Software Developer",
        "Full Stack Developer",
        "Full Stack Software Engineer",
        ".NET Developer",
        ".NET Software Engineer",
        "C# Developer",
        "C# Software Engineer",
        "Backend Developer",
        "Backend Software Engineer",
        "Frontend Developer",
        "Frontend Software Engineer",
        "Software Engineer II",
        "Software Development Engineer",
        "Application Developer",
        "Web Application Developer",
        "Full Stack Engineer",
        "Junior Software Engineer",
        "Junior Developer"
    ]
    for title in allowed_titles:
        assert is_target_job_title(title) is True, f"Expected '{title}' to be allowed"

def test_excluded_unrelated_titles():
    excluded_titles = [
        "IT Support Engineer",
        "Helpdesk Technician",
        "Senior Business Analyst",
        "Technical Project Manager",
        "Product Manager",
        "Network Engineer",
        "Hardware Engineer",
        "Scrum Master",
        "Sales Engineer",
        "Accountant",
        "Marketing Specialist"
    ]
    for title in excluded_titles:
        assert is_target_job_title(title) is False, f"Expected '{title}' to be excluded"

def test_experience_level_detection():
    assert determine_experience_level("Junior .NET Developer") == "Junior"
    assert determine_experience_level("Graduate Software Engineer") == "Junior"
    assert determine_experience_level("Software Engineer") == "Mid"
    assert determine_experience_level("Senior Full Stack Developer") == "Senior"
    assert determine_experience_level("Staff Software Engineer") == "Senior"
    assert determine_experience_level("Lead Developer") == "Senior"
