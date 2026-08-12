from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field

def now(): return datetime.now(timezone.utc)
class Role(str, Enum): patient="patient"; doctor="doctor"; hospital="hospital"; admin="admin"
class Verification(str, Enum): pending="pending"; verified="verified"; rejected="rejected"; suspended="suspended"
class UserCreate(BaseModel):
    first_name: str = Field(min_length=2, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    mobile: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")
    password: str = Field(min_length=8, max_length=72)
class Login(BaseModel): email: EmailStr; password: str
class HospitalCreate(BaseModel):
    name: str = Field(min_length=2); registration_number: str = Field(min_length=3)
    email: EmailStr; mobile: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$"); address: str; city: str; state: str; pincode: str
    description: str = ""; specializations: list[str] = []; facilities: list[str] = []; logo: str | None = None
class DoctorCreate(UserCreate):
    qualification: str; specialization: str; experience: int = Field(ge=0, le=80)
    medical_registration_number: str; bio: str = ""; consultation_fee: float = Field(ge=0)
    profile_image: str | None = None
class ApplicationCreate(BaseModel): hospital_id: str
class AppointmentCreate(BaseModel):
    hospital_id: str; doctor_id: str; date: str; slot: str
    reason: str = Field(min_length=10, max_length=1000); temperature: float | None = Field(default=None, ge=95, le=110)
    symptoms: list[str] = []
class PrescriptionCreate(BaseModel):
    appointment_id: str
    diagnosis: str = Field(min_length=2, max_length=1000)
    medicines: list[dict] = Field(min_length=1)
    instructions: str = Field(min_length=2, max_length=3000)
    follow_up: str | None = Field(default=None, max_length=500)
    doctor_notes: str | None = Field(default=None, max_length=2000)
class AskCreate(BaseModel): question: str = Field(min_length=2, max_length=1000); prescription_id: str | None = None
