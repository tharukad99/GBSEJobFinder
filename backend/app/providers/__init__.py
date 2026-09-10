from backend.app.providers.base_provider import BaseJobProvider, NormalizedJob
from backend.app.providers.greenhouse_provider import GreenhouseProvider
from backend.app.providers.lever_provider import LeverProvider
from backend.app.providers.workable_provider import WorkableProvider
from backend.app.providers.smartrecruiters_provider import SmartRecruitersProvider
from backend.app.providers.ashby_provider import AshbyProvider
from backend.app.providers.company_career_provider import CompanyCareerProvider

PROVIDERS = {
    "greenhouse": GreenhouseProvider(),
    "lever": LeverProvider(),
    "workable": WorkableProvider(),
    "smartrecruiters": SmartRecruitersProvider(),
    "ashby": AshbyProvider(),
    "company_career": CompanyCareerProvider()
}

def get_provider(provider_name: str) -> BaseJobProvider:
    return PROVIDERS.get(provider_name.lower())
