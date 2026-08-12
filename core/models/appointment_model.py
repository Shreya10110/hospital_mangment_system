"""Appointment lifecycle document model."""
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

class AppointmentStatus(str, Enum):
    booked="booked"; confirmed="confirmed"; completed="completed"; cancelled="cancelled"; rejected="rejected"

class Appointment(BaseModel):
    patient_id: str
    hospital_id: str
    doctor_id: str
    date: str
    slot: str
    reason: str = Field(min_length=10)
    temperature: float | None = None
    symptoms: list[str] = []
    status: AppointmentStatus = AppointmentStatus.booked
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
