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
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"
    DB_TRUSTED_CONNECTION: str = "no"
    DB_TRUST_SERVER_CERTIFICATE: str = "no"
    DB_ENCRYPT: str = "yes"
    DB_CONNECTION_TIMEOUT: int = 30
    DB_SCHEMA: str = "job"
    SQL_ECHO: bool = False

    # Scheduler
    JOB_REFRESH_MINUTES: int = 5
    JOB_REFRESH_HOURS: Optional[int] = None
    ENABLE_SCHEDULER: bool = True


    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_GLOBAL_PER_MINUTE: int = 120
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_ADMIN_PER_MINUTE: int = 20
    RATE_LIMIT_LOOKUP_PER_MINUTE: int = 30

    # Security
    SECRET_KEY: str = "supersecretkey_change_in_production_uk_se_jobs_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "adminpassword123"

    @property
    def resolved_driver(self) -> str:
        try:
            import pyodbc
            available = pyodbc.drivers()
            if self.DB_DRIVER in available:
                return self.DB_DRIVER
            if "ODBC Driver 18 for SQL Server" in available:
                return "ODBC Driver 18 for SQL Server"
            if "ODBC Driver 17 for SQL Server" in available:
                return "ODBC Driver 17 for SQL Server"
            if "SQL Server" in available:
                return "SQL Server"
        except Exception:
            pass
        return self.DB_DRIVER

    @property
    def database_url(self) -> str:
        driver = self.resolved_driver
        if self.DB_USERNAME and self.DB_PASSWORD:
            params = (
                f"DRIVER={{{driver}}};"
                f"SERVER={self.DB_SERVER};"
                f"DATABASE={self.DB_DATABASE};"
                f"UID={self.DB_USERNAME};"
                f"PWD={self.DB_PASSWORD};"
                f"Encrypt={self.DB_ENCRYPT};"
                f"TrustServerCertificate={self.DB_TRUST_SERVER_CERTIFICATE};"
                f"Connection Timeout={self.DB_CONNECTION_TIMEOUT};"
            )
        else:
            params = (
                f"DRIVER={{{driver}}};"
                f"SERVER={self.DB_SERVER};"
                f"DATABASE={self.DB_DATABASE};"
                f"Trusted_Connection={self.DB_TRUSTED_CONNECTION};"
                f"Encrypt={self.DB_ENCRYPT};"
                f"TrustServerCertificate={self.DB_TRUST_SERVER_CERTIFICATE};"
                f"Connection Timeout={self.DB_CONNECTION_TIMEOUT};"
            )
        
        quoted_params = urllib.parse.quote_plus(params)
        return f"mssql+pyodbc:///?odbc_connect={quoted_params}"

    class Config:
        env_file = str(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
        extra = "ignore"

settings = Settings()
