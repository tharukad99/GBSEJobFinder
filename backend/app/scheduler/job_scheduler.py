import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.app.database.config import settings
from backend.app.database.session import SessionLocal
from backend.app.services.job_service import JobService
from backend.app.services.verification_service import VerificationService
from backend.app.models.job import Job

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def scheduled_job_refresh():
    """Periodic job to refresh all enabled ATS job feeds and verify freshness."""
    logger.info("Starting scheduled job refresh cycle...")
    db = SessionLocal()
    try:
        results = await JobService.refresh_all_sources(db)
        logger.info(f"Completed scheduled job refresh for {len(results)} sources.")

        # Also verify a batch of active jobs that haven't been verified recently
        one_day_ago = datetime.utcnow() - timedelta(hours=12)
        unverified_jobs = (
            db.query(Job)
            .filter(Job.JobStatus == "ACTIVE", Job.LastVerifiedAt < one_day_ago)
            .limit(20)
            .all()
        )
        for job in unverified_jobs:
            try:
                await VerificationService.verify_job(db, job)
            except Exception as e:
                logger.warning(f"Error checking job {job.JobId}: {e}")

    except Exception as e:
        logger.error(f"Error during scheduled refresh: {e}", exc_info=True)
    finally:
        db.close()

def start_scheduler():
    if not settings.ENABLE_SCHEDULER:
        logger.info("Scheduler is disabled by configuration.")
        return

    if not scheduler.running:
        minutes_interval = settings.JOB_REFRESH_MINUTES if settings.JOB_REFRESH_MINUTES else (settings.JOB_REFRESH_HOURS * 60 if settings.JOB_REFRESH_HOURS else 5)
        scheduler.add_job(
            scheduled_job_refresh,
            trigger=IntervalTrigger(minutes=minutes_interval),
            id="job_refresh_task",
            name="Periodic Job Ingestion and Freshness Check",
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(seconds=10) # Run initial ingestion shortly after startup
        )
        scheduler.start()
        logger.info(f"Background Job Scheduler started (interval: recurring every {minutes_interval} minutes).")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background Job Scheduler shut down.")
