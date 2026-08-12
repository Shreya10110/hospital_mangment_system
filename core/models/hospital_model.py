"""Hospital document shape and verification values."""
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field
from core.models.domain import Verification

class Hospital(BaseModel):
    name: str
    registration_number: str
    email: EmailStr
    mobile: str
    address: str
    city: str
    state: str
    pincode: str
    description: str = ""
    specializations: list[str] = []
    facilities: list[str] = []
    logo: str | None = None
    verification_status: Verification = Verification.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
