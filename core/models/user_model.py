"""User persistence and request models for patient/admin accounts."""
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    mobile: str
    password: str
    role: str = "patient"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
