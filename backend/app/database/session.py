import logging
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.database.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_engine():
    try:
        engine = create_engine(
            settings.database_url,
            echo=settings.SQL_ECHO,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        return engine
    except Exception as e:
        logger.error(f"Error initializing database engine: {e}")
        raise

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
