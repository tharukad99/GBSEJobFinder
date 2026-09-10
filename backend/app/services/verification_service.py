import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.job import Job
from backend.app.models.verification_history import JobVerificationHistory

logger = logging.getLogger(__name__)

class VerificationService:
    @staticmethod
    async def verify_job_url(url: str, timeout: float = 10.0) -> Tuple[bool, int, str]:
        """
        Attempts to verify if a job URL is still accessible.
        Returns: (still_available, http_status, notes)
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 UKSEJobFinder/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        try:
            async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
                # Try HEAD first
                try:
                    res = await client.head(url)
                    status = res.status_code
                except Exception:
                    res = await client.get(url)
                    status = res.status_code

                if status in (200, 301, 302, 307, 308):
                    return (True, status, "Page accessible and active")
                elif status in (404, 410):
                    return (False, status, "Vacancy link no longer found (404/410)")
                elif status in (403, 429):
                    # Rate-limited or blocked, don't immediately declare dead
                    return (True, status, f"Received status {status}, keeping active")
                else:
                    return (False, status, f"Received unexpected HTTP status: {status}")
        except httpx.TimeoutException:
            return (True, 0, "Verification request timed out; retaining current status")
        except Exception as e:
            return (False, 0, f"Connection error: {str(e)[:200]}")

    @classmethod
    async def verify_job(cls, db: Session, job: Job) -> Dict[str, Any]:
        """
        Verifies a single job, records history, and updates active status.
        """
        now = datetime.utcnow()
        
        # Check closing date first
        if job.ClosingDate and job.ClosingDate < now:
            job.JobStatus = "EXPIRED"
            job.LastVerifiedAt = now
            db.commit()
            return {"job_id": job.JobId, "status": "EXPIRED", "notes": "Closing date passed"}

        target_url = job.ApplyUrl or job.SourceJobUrl
        is_alive, http_code, notes = await cls.verify_job_url(target_url)

        # Log history
        history = JobVerificationHistory(
            JobId=job.JobId,
            VerifiedAt=now,
            HttpStatus=http_code,
            StillAvailable=is_alive,
            Notes=notes
        )
        db.add(history)

        job.LastVerifiedAt = now

        if is_alive:
            job.JobStatus = "ACTIVE"
            job.VerificationFailureCount = 0
        else:
            job.VerificationFailureCount += 1
            if job.VerificationFailureCount >= 2 or http_code in (404, 410):
                job.JobStatus = "CLOSED"
            else:
                job.JobStatus = "POSSIBLY_REMOVED"

        db.commit()
        return {
            "job_id": job.JobId,
            "job_status": job.JobStatus,
            "http_status": http_code,
            "still_available": is_alive,
            "notes": notes
        }
