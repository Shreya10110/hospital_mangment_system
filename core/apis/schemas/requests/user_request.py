"""Validated request bodies for authentication routes."""
from core.models.domain import UserCreate, Login

class UserSignUpRequest(UserCreate):
    """Patient sign-up data. Role is deliberately not client controlled."""
class UserLoginRequest(Login):
    """Email/password login payload."""
