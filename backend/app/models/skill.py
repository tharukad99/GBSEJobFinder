from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Skill(Base):
    __tablename__ = "Skills"

    SkillId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    SkillName = Column(String(100), unique=True, nullable=False, index=True)
    NormalizedSkillName = Column(String(100), unique=True, nullable=False, index=True)
    Category = Column(String(50), default="General", nullable=False) # Primary, Secondary, Tooling, etc.

    job_skills = relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")

class JobSkill(Base):
    __tablename__ = "JobSkills"

    JobSkillId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    JobId = Column(Integer, ForeignKey("Jobs.JobId", ondelete="CASCADE"), nullable=False, index=True)
    SkillId = Column(Integer, ForeignKey("Skills.SkillId", ondelete="CASCADE"), nullable=False, index=True)
    RequiredOrPreferred = Column(String(20), default="Required", nullable=False) # Required, Preferred

    __table_args__ = (UniqueConstraint("JobId", "SkillId", name="UQ_Job_Skill"),)

    job = relationship("Job", back_populates="skills")
    skill = relationship("Skill", back_populates="job_skills")
