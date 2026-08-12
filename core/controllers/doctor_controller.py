"""Doctor-facing data access operations."""
from core.cruds.base import serialize
from core.cruds.doctor_crud import DoctorCRUD

class DoctorController:
    def __init__(self): self.doctors = DoctorCRUD()
    async def get_profile(self, doctor_id: str):
        doc = await self.doctors.get_by_id(doctor_id)
        if doc: doc.pop("password", None)
        return serialize(doc)
