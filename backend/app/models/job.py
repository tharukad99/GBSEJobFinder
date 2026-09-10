from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Job(Base):
    __tablename__ = "Jobs"

    JobId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ExternalJobId = Column(String(255), nullable=True, index=True)
    CompanyId = Column(Integer, ForeignKey("Companies.CompanyId", ondelete="CASCADE"), nullable=False, index=True)
    
    # Titles & descriptions
    Title = Column(String(300), nullable=False, index=True)
    NormalizedTitle = Column(String(300), nullable=False, index=True)
    Description = Column(Text, nullable=True)

    # Location
    Location = Column(String(300), nullable=False, index=True)
    City = Column(String(100), nullable=True, index=True)
    Region = Column(String(100), nullable=True, index=True)
    Country = Column(String(100), default="United Kingdom", nullable=False, index=True)
    RemoteType = Column(String(50), default="Unknown", nullable=False, index=True) # On-site, Hybrid, Remote UK, Unknown
    EmploymentType = Column(String(50), default="Full-time", nullable=True) # Full-time, Contract, etc.

    # Compensation
    SalaryMin = Column(Float, nullable=True)
    SalaryMax = Column(Float, nullable=True)
    SalaryCurrency = Column(String(10), default="GBP", nullable=True)
    SalaryText = Column(String(200), nullable=True)
    ExperienceLevel = Column(String(50), default="Mid", nullable=True) # Junior, Mid, Senior, etc.

    # Source and URLs
    SourceId = Column(Integer, ForeignKey("JobSources.SourceId", ondelete="SET NULL"), nullable=True, index=True)
    SourceJobUrl = Column(String(1000), nullable=False)
    CompanyCareerUrl = Column(String(1000), nullable=True)
    ApplyUrl = Column(String(1000), nullable=False)

    # Dates
    PostedDate = Column(DateTime, nullable=True, index=True)
    ClosingDate = Column(DateTime, nullable=True)
    FirstSeenAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    LastSeenAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    LastVerifiedAt = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Status & Scores
    JobStatus = Column(String(50), default="ACTIVE", nullable=False, index=True) # ACTIVE, POSSIBLY_REMOVED, CLOSED, EXPIRED
    MatchScore = Column(Integer, default=0, nullable=False, index=True) # 0-100
    QualityScore = Column(Integer, default=0, nullable=False) # 0-100
    DuplicateHash = Column(String(64), nullable=True, index=True)
    VerificationFailureCount = Column(Integer, default=0, nullable=False)

    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="jobs")
    source = relationship("JobSource", back_populates="jobs")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    sponsorship_evidence = relationship("SponsorshipEvidence", back_populates="job", cascade="all, delete-orphan", uselist=False)
    verification_history = relationship("JobVerificationHistory", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("IX_Jobs_Status_MatchScore", "JobStatus", "MatchScore"),
    )
