from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from backend.app.database.session import Base

class User(Base):
    __tablename__ = "Users"

    UserId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Username = Column(String(100), unique=True, nullable=False, index=True)
    PasswordHash = Column(String(255), nullable=False)
    Role = Column(String(50), default="ADMIN", nullable=False)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    LastLoginAt = Column(DateTime, nullable=True)
