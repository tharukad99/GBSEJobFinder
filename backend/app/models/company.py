from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Company(Base):
    __tablename__ = "Companies"

    CompanyId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    CompanyName = Column(String(255), nullable=False, index=True)
    NormalizedCompanyName = Column(String(255), nullable=False, index=True)
    WebsiteUrl = Column(String(500), nullable=True)
    CareersUrl = Column(String(500), nullable=True)
    Industry = Column(String(150), nullable=True)
    SponsorLicenceStatus = Column(String(50), default="UNKNOWN", nullable=False) # LICENSED, NOT_LICENSED, UNKNOWN, NEEDS_VERIFICATION
    SponsorRoute = Column(String(100), nullable=True) # Skilled Worker, Worker (A rating), etc.
    SponsorRating = Column(String(50), nullable=True) # A rating, etc.
    SponsorVerifiedAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
