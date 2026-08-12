"""Doctor document shape, separate from a patient's user profile."""
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field
from core.models.domain import Verification

class Doctor(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    mobile: str
    password: str
    qualification: str
    specialization: str
    experience: int = Field(ge=0)
    medical_registration_number: str
    bio: str = ""
    profile_image: str | None = None
    consultation_fee: float = Field(ge=0)
    verification_status: Verification = Verification.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
