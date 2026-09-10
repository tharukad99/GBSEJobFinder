import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database.config import settings
from backend.app.api.jobs import router as jobs_router
from backend.app.api.companies import router as companies_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.sources import router as sources_router
from backend.app.api.admin import router as admin_router
from backend.app.api.sponsorship import router as sponsorship_router
from backend.app.api.auth import router as auth_router
from backend.app.scheduler.job_scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SEJobFinder")

# Path to static frontend assets
STATIC_DIR = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing UK Software Engineering Job Finder App...")
    # Start scheduler
    start_scheduler()
    yield
    # Stop scheduler
    stop_scheduler()
    logger.info("Application shut down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade UK Software Engineering Job Finder with Skilled Worker Visa Verification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

from backend.app.utils.rate_limiter import RateLimitMiddleware

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# Mount API routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(companies_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(sources_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(sponsorship_router, prefix=settings.API_V1_STR)


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

# Mount static asset directory
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/jobs")
    async def serve_jobs():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/companies")
    async def serve_companies():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/admin")
    async def serve_admin():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/monitor")
    async def serve_monitor():
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "name": settings.PROJECT_NAME,
            "status": "online",
            "docs": "/docs",
            "version": "1.0.0"
        }

