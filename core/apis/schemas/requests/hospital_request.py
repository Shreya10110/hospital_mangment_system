"""Validated request body for hospital registration and profile edits."""
from core.models.domain import HospitalCreate

class HospitalRegistrationRequest(HospitalCreate):
    pass
class HospitalProfileUpdateRequest(HospitalCreate):
    pass
