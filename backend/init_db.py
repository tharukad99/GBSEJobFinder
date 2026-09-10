import sys
import os
import logging
import hashlib
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyodbc
from backend.app.database.config import settings
from backend.app.database.session import engine, SessionLocal, Base
from backend.app.models import (
    User, Company, Job, Skill, JobSkill, SponsorshipEvidence, JobSource, ScrapeRun, JobVerificationHistory
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    # Use SHA-256 with salt for simplicity or standard bcrypt
    import hashlib
    salt = "se_job_finder_salt_2026_"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def ensure_database_exists():
    """Ensure that the MSSQL database exists, creating it if necessary."""
    logger.info(f"Checking if database '{settings.DB_DATABASE}' exists on server '{settings.DB_SERVER}'...")
    
    if settings.DB_USERNAME and settings.DB_PASSWORD:
        conn_str = f"DRIVER={{{settings.DB_DRIVER}}};SERVER={settings.DB_SERVER};DATABASE=master;UID={settings.DB_USERNAME};PWD={settings.DB_PASSWORD};TrustServerCertificate={settings.DB_TRUST_SERVER_CERTIFICATE};"
    else:
        conn_str = f"DRIVER={{{settings.DB_DRIVER}}};SERVER={settings.DB_SERVER};DATABASE=master;Trusted_Connection={settings.DB_TRUSTED_CONNECTION};TrustServerCertificate={settings.DB_TRUST_SERVER_CERTIFICATE};"

    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{settings.DB_DATABASE}'")
        row = cursor.fetchone()
        if not row:
            logger.info(f"Creating database '{settings.DB_DATABASE}'...")
            cursor.execute(f"CREATE DATABASE [{settings.DB_DATABASE}]")
            logger.info(f"Database '{settings.DB_DATABASE}' created successfully.")
        else:
            logger.info(f"Database '{settings.DB_DATABASE}' already exists.")
        conn.close()
    except Exception as e:
        logger.error(f"Error checking/creating database: {e}")
        raise

def seed_skills(db):
    """Seed predefined primary and secondary skills."""
    skills_data = [
        # Primary
        ("C#", "c#", "Primary"),
        (".NET", ".net", "Primary"),
        (".NET Core", ".net core", "Primary"),
        ("ASP.NET Core", "asp.net core", "Primary"),
        ("React", "react", "Primary"),
        ("JavaScript", "javascript", "Primary"),
        ("TypeScript", "typescript", "Primary"),
        ("SQL Server", "sql server", "Primary"),
        ("MSSQL", "mssql", "Primary"),
        ("Azure", "azure", "Primary"),
        ("Python", "python", "Primary"),
        # Secondary
        ("REST API", "rest api", "Secondary"),
        ("Entity Framework", "entity framework", "Secondary"),
        ("Azure SQL", "azure sql", "Secondary"),
        ("Git", "git", "Secondary"),
        ("GitHub", "github", "Secondary"),
        ("CI/CD", "ci/cd", "Secondary"),
        ("Docker", "docker", "Secondary"),
        ("Microservices", "microservices", "Secondary"),
        ("HTML", "html", "Secondary"),
        ("CSS", "css", "Secondary"),
        ("SQL", "sql", "Secondary"),
        ("Node.js", "node.js", "Secondary"),
        ("FastAPI", "fastapi", "Secondary"),
        ("Kubernetes", "kubernetes", "Secondary"),
        ("AWS", "aws", "Secondary"),
    ]
    
    count = 0
    for name, norm, cat in skills_data:
        existing = db.query(Skill).filter(Skill.NormalizedSkillName == norm).first()
        if not existing:
            db.add(Skill(SkillName=name, NormalizedSkillName=norm, Category=cat))
            count += 1
    db.commit()
    logger.info(f"Seeded {count} new skills (total: {db.query(Skill).count()}).")

def seed_sources(db):
    """Seed initial trusted job sources and ATS providers."""
    sources_data = [
        {
            "SourceName": "Greenhouse ATS Feed",
            "SourceType": "ATS_GREENHOUSE",
            "BaseUrl": "https://boards-api.greenhouse.io/v1/boards/",
            "ProviderName": "greenhouse",
            "ConfigJson": json.dumps({
                "companies": [
                    "monzo", "deliveroo", "starlingbank", "revolut", "snyk", 
                    "checkout", "primer", "hometree", "multiverse", "synthesia",
                    "hopin", "marshmallow", "motorway", "depop", "cleo"
                ]
            }),
            "IsEnabled": True
        },
        {
            "SourceName": "Lever ATS Feed",
            "SourceType": "ATS_LEVER",
            "BaseUrl": "https://api.lever.co/v0/postings/",
            "ProviderName": "lever",
            "ConfigJson": json.dumps({
                "companies": [
                    "spotify", "atlan", "pleo", "gocardless", "kroo", 
                    "thoughtmachine", "kraken", "omnipresent", "papier"
                ]
            }),
            "IsEnabled": True
        },
        {
            "SourceName": "Workable ATS Feed",
            "SourceType": "ATS_WORKABLE",
            "BaseUrl": "https://apply.workable.com/api/v1/widget/accounts/",
            "ProviderName": "workable",
            "ConfigJson": json.dumps({
                "companies": [
                    "skyscanner", "bloom-wild", "tails-com", "secret-escapes"
                ]
            }),
            "IsEnabled": True
        },
        {
            "SourceName": "SmartRecruiters Feed",
            "SourceType": "ATS_SMARTRECRUITERS",
            "BaseUrl": "https://api.smartrecruiters.com/v1/companies/",
            "ProviderName": "smartrecruiters",
            "ConfigJson": json.dumps({
                "companies": [
                    "square", "visa", "cisco", "bupa", "publicisgroupe"
                ]
            }),
            "IsEnabled": True
        },
        {
            "SourceName": "Ashby ATS Feed",
            "SourceType": "ATS_ASHBY",
            "BaseUrl": "https://api.ashbyhq.com/posting-api/job-board/",
            "ProviderName": "ashby",
            "ConfigJson": json.dumps({
                "companies": [
                    "ramp", "linear", "postman", "deel", "ironclad", "glide"
                ]
            }),
            "IsEnabled": True
        }
    ]

    count = 0
    for src in sources_data:
        existing = db.query(JobSource).filter(JobSource.SourceName == src["SourceName"]).first()
        if not existing:
            db.add(JobSource(**src))
            count += 1
    db.commit()
    logger.info(f"Seeded {count} new job sources (total: {db.query(JobSource).count()}).")

def seed_admin_user(db):
    """Seed default admin user."""
    admin = db.query(User).filter(User.Username == settings.ADMIN_USERNAME).first()
    if not admin:
        hashed = hash_password(settings.ADMIN_PASSWORD)
        db.add(User(Username=settings.ADMIN_USERNAME, PasswordHash=hashed, Role="ADMIN"))
        db.commit()
        logger.info(f"Created default admin user '{settings.ADMIN_USERNAME}'.")
    else:
        logger.info(f"Admin user '{settings.ADMIN_USERNAME}' exists.")

def init_all():
    ensure_database_exists()
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

    db = SessionLocal()
    try:
        seed_skills(db)
        seed_sources(db)
        seed_admin_user(db)
        logger.info("Database initialization and seeding completed successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    init_all()
