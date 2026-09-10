from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class ScrapeRun(Base):
    __tablename__ = "ScrapeRuns"

    ScrapeRunId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    SourceId = Column(Integer, ForeignKey("JobSources.SourceId", ondelete="CASCADE"), nullable=True, index=True)
    StartedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    CompletedAt = Column(DateTime, nullable=True)
    JobsFound = Column(Integer, default=0, nullable=False)
    JobsAdded = Column(Integer, default=0, nullable=False)
    JobsUpdated = Column(Integer, default=0, nullable=False)
    DuplicatesFound = Column(Integer, default=0, nullable=False)
    JobsRejected = Column(Integer, default=0, nullable=False)
    Status = Column(String(50), default="RUNNING", nullable=False) # RUNNING, SUCCESS, FAILED, PARTIAL
    ErrorMessage = Column(Text, nullable=True)

    source = relationship("JobSource", back_populates="scrape_runs")
