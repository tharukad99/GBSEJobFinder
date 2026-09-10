from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class JobSource(Base):
    __tablename__ = "JobSources"

    SourceId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    SourceName = Column(String(150), unique=True, nullable=False, index=True)
    SourceType = Column(String(50), nullable=False) # ATS_GREENHOUSE, ATS_LEVER, ATS_WORKABLE, ATS_SMARTRECRUITERS, ATS_ASHBY, COMPANY_CAREER, PUBLIC_FEED
    BaseUrl = Column(String(500), nullable=True)
    ProviderName = Column(String(100), nullable=False) # greenhouse, lever, workable, smartrecruiters, ashby, company_career
    ConfigJson = Column(Text, nullable=True) # JSON configuration (e.g. company tokens, endpoints)
    IsEnabled = Column(Boolean, default=True, nullable=False)
    LastSuccessfulRun = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    jobs = relationship("Job", back_populates="source")
    scrape_runs = relationship("ScrapeRun", back_populates="source", cascade="all, delete-orphan")
