"""Patient-owned prescription queries."""
from core.database.database import get_database
from core.cruds.base import serialize
from core.cruds.prescription_crud import PrescriptionCRUD

class PrescriptionController:
    def __init__(self): self.prescriptions = PrescriptionCRUD()
    async def for_patient(self, patient_id: str):
        return [serialize(doc) async for doc in get_database().prescriptions.find({"patient_id": patient_id}).sort("created_at", -1)]
    async def get_for_patient(self, prescription_id: str, patient_id: str):
        return serialize(await self.prescriptions.get_for_patient(prescription_id, patient_id))
