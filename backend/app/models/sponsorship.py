from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class SponsorshipEvidence(Base):
    __tablename__ = "SponsorshipEvidence"

    SponsorshipEvidenceId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    JobId = Column(Integer, ForeignKey("Jobs.JobId", ondelete="CASCADE"), nullable=False, index=True)
    SponsorshipStatus = Column(String(50), nullable=False, index=True) # CONFIRMED, MAY_OFFER, NO_SPONSORSHIP, UNKNOWN
    EvidenceText = Column(Text, nullable=True)
    EvidenceUrl = Column(String(500), nullable=True)
    EvidenceSource = Column(String(100), nullable=True) # Job Description, Company Career Page, UK Home Office Sponsor Register, Manual Override
    ConfidenceLevel = Column(String(20), default="Medium", nullable=False) # High, Medium, Low
    VerifiedAt = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="sponsorship_evidence")
