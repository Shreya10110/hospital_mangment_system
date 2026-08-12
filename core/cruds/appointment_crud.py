"""MongoDB operations for appointment documents."""
from core.database.database import get_database
from core.cruds.base import oid

class AppointmentCRUD:
    @property
    def collection(self): return get_database().appointments
    async def get_by_id(self, appointment_id: str): return await self.collection.find_one({"_id": oid(appointment_id)})
    async def create(self, data: dict): result=await self.collection.insert_one(data); data["_id"]=result.inserted_id; return data
    async def update(self, appointment_id: str, data: dict):
        await self.collection.update_one({"_id": oid(appointment_id)}, {"$set": data}); return await self.get_by_id(appointment_id)
