import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Admin credentials and JWT configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()

# Default bcrypt hash for 'admin123' if not set in .env
DEFAULT_PASSWORD_HASH = "$2b$12$iSzMnkeJBEd3vZsNfYeL7uxqK6XOLkYlg4DC46D3uWWAnM2.5sHjm"
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", DEFAULT_PASSWORD_HASH).strip()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ieee-rag-assistant-secret-jwt-key-2026").strip()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 12

security = HTTPBearer(auto_error=False)

def verify_admin_password(plain_password: str) -> bool:
    """Verify plain text password against stored bcrypt hash."""
    if not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            ADMIN_PASSWORD_HASH.encode("utf-8")
        )
    except Exception as e:
        print(f"Bcrypt verification error: {e}")
        return False

def create_admin_token(username: str) -> dict:
    """Generate a signed JWT token with expiration for the authenticated admin."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": username,
        "role": "admin",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": username,
        "expires_in": JWT_EXPIRATION_HOURS * 3600
    }

def get_current_admin(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    FastAPI dependency that enforces admin authentication.
    Returns the admin username if token is valid.
    Raises HTTP 401 Unauthorized for missing, expired, or invalid tokens.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in as an administrator.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        
        if not username or username != ADMIN_USERNAME or role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Administrator privileges required."
            )
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
