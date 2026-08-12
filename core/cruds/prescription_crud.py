"""MongoDB operations for prescription documents."""
from core.database.database import get_database
from core.cruds.base import oid

class PrescriptionCRUD:
    @property
    def collection(self): return get_database().prescriptions
    async def get_by_id(self, prescription_id: str): return await self.collection.find_one({"_id": oid(prescription_id)})
    async def get_for_patient(self, prescription_id: str, patient_id: str): return await self.collection.find_one({"_id": oid(prescription_id), "patient_id": patient_id})
    async def create(self, data: dict): result=await self.collection.insert_one(data); data["_id"]=result.inserted_id; return data
