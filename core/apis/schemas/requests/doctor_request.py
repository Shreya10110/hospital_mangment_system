"""Validated request body for doctor registration and profile edits."""
from core.models.domain import DoctorCreate

class DoctorRegistrationRequest(DoctorCreate):
    pass
class DoctorProfileUpdateRequest(DoctorCreate):
    pass
