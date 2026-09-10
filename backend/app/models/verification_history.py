from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class JobVerificationHistory(Base):
    __tablename__ = "JobVerificationHistory"

    VerificationId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    JobId = Column(Integer, ForeignKey("Jobs.JobId", ondelete="CASCADE"), nullable=False, index=True)
    VerifiedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    HttpStatus = Column(Integer, nullable=True)
    StillAvailable = Column(Boolean, default=True, nullable=False)
    Notes = Column(String(500), nullable=True)

    job = relationship("Job", back_populates="verification_history")
