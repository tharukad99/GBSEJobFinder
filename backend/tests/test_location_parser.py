import pytest
from backend.app.utils.location_parser import parse_location

def test_uk_locations():
    res = parse_location("London, UK")
    assert res.is_uk is True
    assert res.city == "London"
    assert res.country == "United Kingdom"

    res_mcr = parse_location("Manchester, Greater Manchester")
    assert res_mcr.is_uk is True
    assert res_mcr.city == "Manchester"
    assert res_mcr.region == "North West"

    res_remote = parse_location("Remote, United Kingdom")
    assert res_remote.is_uk is True
    assert res_remote.remote_type == "Remote UK"

    res_hybrid = parse_location("London, Hybrid")
    assert res_hybrid.is_uk is True
    assert res_hybrid.remote_type == "Hybrid"

def test_non_uk_locations_rejected():
    res_us = parse_location("San Francisco, CA, USA")
    assert res_us.is_uk is False
    assert res_us.country == "Non-UK"

    res_india = parse_location("Bangalore, India")
    assert res_india.is_uk is False

    res_germany = parse_location("Berlin, Germany")
    assert res_germany.is_uk is False
