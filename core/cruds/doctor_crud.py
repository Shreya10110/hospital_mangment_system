"""MongoDB operations for doctor documents."""
from core.database.database import get_database
from core.cruds.base import oid

class DoctorCRUD:
    @property
    def collection(self): return get_database().doctors
    async def get_by_id(self, doctor_id: str): return await self.collection.find_one({"_id": oid(doctor_id)})
    async def get_by_email(self, email: str): return await self.collection.find_one({"email": email.lower()})
    async def create(self, data: dict): result=await self.collection.insert_one(data); data["_id"]=result.inserted_id; return data
    async def update(self, doctor_id: str, data: dict):
        await self.collection.update_one({"_id": oid(doctor_id)}, {"$set": data}); return await self.get_by_id(doctor_id)
