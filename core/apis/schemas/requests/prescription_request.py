"""Validated request body for a doctor's prescription."""
from core.models.domain import PrescriptionCreate

class PrescriptionCreateRequest(PrescriptionCreate):
    pass
