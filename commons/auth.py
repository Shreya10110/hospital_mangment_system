"""Password and token helpers. Never trust identity values from a request body."""
import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
import bcrypt

_scheme = HTTPBearer(auto_error=False)
SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or os.getenv("secret") or "change-this-development-secret"
ALGORITHM = os.getenv("JWT_ALGORITHM") or os.getenv("algorithm", "HS256")

def hash_password(password: str) -> str:
    encoded=password.encode("utf-8")
    if len(encoded)>72: raise ValueError("Password must be at most 72 bytes")
    return bcrypt.hashpw(encoded,bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try: return bcrypt.checkpw(password.encode("utf-8"),password_hash.encode("utf-8"))
    except (ValueError,TypeError): return False

def create_token(user_id: str, role: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=12)
    return jwt.encode({"sub": user_id, "role": role, "exp": expires}, SECRET, algorithm=ALGORITHM)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGORITHM])
        return {"id": payload["sub"], "role": payload["role"]}
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

def require(*roles: str):
    def dependency(user: dict = Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")
        return user
    return dependency
