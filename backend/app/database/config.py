import os
import urllib.parse
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "UK Software Engineering Job Finder"
    API_V1_STR: str = "/api"
    ENV: str = "development"

    # Database
    DB_SERVER: str = "localhost"
    DB_DATABASE: str = "SEJobFinderDB"
    DB_USERNAME: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_TRUSTED_CONNECTION: str = "yes"
    DB_TRUST_SERVER_CERTIFICATE: str = "yes"
    SQL_ECHO: bool = False

    # Scheduler
    JOB_REFRESH_MINUTES: int = 5
    JOB_REFRESH_HOURS: Optional[int] = None
    ENABLE_SCHEDULER: bool = True


    # Security
    SECRET_KEY: str = "supersecretkey_change_in_production_uk_se_jobs_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "adminpassword123"

    @property
    def database_url(self) -> str:
        # Build ODBC connection string
        if self.DB_USERNAME and self.DB_PASSWORD:
            params = f"DRIVER={{{self.DB_DRIVER}}};SERVER={self.DB_SERVER};DATABASE={self.DB_DATABASE};UID={self.DB_USERNAME};PWD={self.DB_PASSWORD};TrustServerCertificate={self.DB_TRUST_SERVER_CERTIFICATE};"
        else:
            params = f"DRIVER={{{self.DB_DRIVER}}};SERVER={self.DB_SERVER};DATABASE={self.DB_DATABASE};Trusted_Connection={self.DB_TRUSTED_CONNECTION};TrustServerCertificate={self.DB_TRUST_SERVER_CERTIFICATE};"
        
        quoted_params = urllib.parse.quote_plus(params)
        return f"mssql+pyodbc:///?odbc_connect={quoted_params}"

    class Config:
        env_file = str(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
        extra = "ignore"

settings = Settings()
