import time
import logging
from collections import defaultdict, deque
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.app.database.config import settings

logger = logging.getLogger(__name__)

def get_client_ip(request: Request) -> str:
    """Extract real client IP considering Azure App Service and reverse proxies."""
    # Check X-Forwarded-For header (common in Azure App Service / Load Balancers)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # First IP in the list is the original client IP
        return forwarded_for.split(",")[0].strip()
    
    # Check Azure-specific client IP header
    azure_client_ip = request.headers.get("x-azure-clientip")
    if azure_client_ip:
        return azure_client_ip.strip()

    # Check X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection host
    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


class SlidingWindowRateLimiter:
    """High-performance sliding-window in-memory rate limiter."""
    
    def __init__(self):
        # Map of key -> deque of timestamps
        self.requests = defaultdict(deque)
        self.last_cleanup = time.time()

    def _cleanup_old_keys(self, now: float, window_seconds: int = 60):
        """Periodically clean up stale client records to prevent memory growth."""
        if now - self.last_cleanup < 300:  # Run cleanup every 5 minutes
            return
        self.last_cleanup = now
        stale_cutoff = now - (window_seconds * 2)
        keys_to_remove = []
        for key, timestamps in self.requests.items():
            while timestamps and timestamps[0] < stale_cutoff:
                timestamps.popleft()
            if not timestamps:
                keys_to_remove.append(key)
        for k in keys_to_remove:
            del self.requests[k]

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed under sliding window limit.
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        self._cleanup_old_keys(now, window_seconds)
        
        timestamps = self.requests[key]
        cutoff = now - window_seconds

        # Evict timestamps older than sliding window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        current_count = len(timestamps)
        if current_count >= max_requests:
            oldest = timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return False, 0, retry_after

        # Record this request
        timestamps.append(now)
        remaining = max(0, max_requests - (current_count + 1))
        return True, remaining, 0

    def reset_key(self, key: str):
        """Reset history for a specific key (e.g. after successful admin action)."""
        if key in self.requests:
            del self.requests[key]


# Global instance
limiter = SlidingWindowRateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60, bucket_name: Optional[str] = None):
    """
    FastAPI dependency for endpoint-specific rate limiting.
    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))])
    """
    async def dependency(request: Request):
        if not settings.ENABLE_RATE_LIMITING:
            return

        client_ip = get_client_ip(request)
        bucket = bucket_name or request.url.path
        key = f"{client_ip}:{bucket}"

        allowed, remaining, retry_after = limiter.check_rate_limit(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds
        )

        if not allowed:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {bucket} (limit: {max_requests}/{window_seconds}s)")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Please retry in {retry_after} seconds.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                }
            )

    return dependency


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limit middleware for API endpoints.
    Protects all /api/* routes with a baseline limit.
    """
    async def dispatch(self, request: Request, call_next):
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)

        path = request.url.path

        # Only apply global rate limit to API routes; ignore static assets, health checks, docs
        if not path.startswith("/api") or path == "/api/health":
            return await call_next(request)

        client_ip = get_client_ip(request)
        global_key = f"{client_ip}:global_api"
        max_req = settings.RATE_LIMIT_GLOBAL_PER_MINUTE
        window = 60

        allowed, remaining, retry_after = limiter.check_rate_limit(
            key=global_key,
            max_requests=max_req,
            window_seconds=window
        )

        if not allowed:
            logger.warning(f"Global API rate limit exceeded for {client_ip} on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit exceeded. Maximum {max_req} requests per minute. Retry in {retry_after}s.",
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_req),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
