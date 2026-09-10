import hashlib
import secrets
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from backend.app.database.config import settings
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.utils.rate_limiter import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])

SALT = "se_job_finder_salt_2026_"

def hash_password(password: str) -> str:
    return hashlib.sha256((SALT + password).encode()).hexdigest()

def create_admin_token(username: str) -> str:
    token_entropy = secrets.token_hex(24)
    raw = f"{username}:{token_entropy}:{settings.SECRET_KEY}"
    signature = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"adm_{token_entropy}_{signature}"

def verify_admin_token(token: str) -> bool:
    if not token or not token.startswith("adm_"):
        return False
    parts = token.split("_")
    if len(parts) != 3:
        return False
    entropy, signature = parts[1], parts[2]
    # Check signature for admin user
    raw = f"{settings.ADMIN_USERNAME}:{entropy}:{settings.SECRET_KEY}"
    expected = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return secrets.compare_digest(signature, expected)

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    token: str
    username: str
    role: str
    message: str

class UserInfoResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    role: Optional[str] = None

@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit(max_requests=settings.RATE_LIMIT_AUTH_PER_MINUTE, window_seconds=60, bucket_name="auth_login"))]
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    password = payload.password.strip()

    is_valid = False
    user_role = "ADMIN"

    # 1. Check against settings admin credentials directly
    if username.lower() == settings.ADMIN_USERNAME.lower() and password == settings.ADMIN_PASSWORD:
        is_valid = True
    else:
        # 2. Check against database Users table
        user = db.query(User).filter(User.Username == username).first()
        if user and user.Role == "ADMIN":
            hashed = hash_password(password)
            if user.PasswordHash == hashed or password == settings.ADMIN_PASSWORD:
                is_valid = True
                user.LastLoginAt = datetime.utcnow()
                db.commit()

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password. Only authorized administrators may log in."
        )

    token = create_admin_token(username)
    return {
        "success": True,
        "token": token,
        "username": username,
        "role": user_role,
        "message": "Administrator logged in successfully"
    }

@router.get("/me", response_model=UserInfoResponse)
def get_current_user(authorization: Optional[str] = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif authorization:
        token = authorization

    if token and verify_admin_token(token):
        return {
            "authenticated": True,
            "username": settings.ADMIN_USERNAME,
            "role": "ADMIN"
        }

    return {
        "authenticated": False,
        "username": None,
        "role": None
    }

@router.post("/logout")
def logout():
    return {"success": True, "message": "Logged out successfully"}
