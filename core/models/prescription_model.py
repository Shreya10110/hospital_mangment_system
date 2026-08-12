"""Prescription document model used by PDF/RAG integrations."""
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class Prescription(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    hospital_id: str
    diagnosis: str = ""
    medicines: list[dict] = []
    instructions: str = ""
    follow_up: str | None = None
    pdf_url: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
