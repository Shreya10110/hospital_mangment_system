"""PostgreSQL operations for hospital records."""
from core.database.database import get_database
from core.cruds.base import oid

class HospitalCRUD:
    @property
    def collection(self): return get_database().hospitals
    async def get_by_id(self, hospital_id: str): return await self.collection.find_one({"_id": oid(hospital_id)})
    async def get_by_owner(self, owner_id: str): return await self.collection.find_one({"owner_id": owner_id})
    async def create(self, data: dict): result=await self.collection.insert_one(data); data["_id"]=result.inserted_id; return data
    async def update(self, hospital_id: str, data: dict):
        await self.collection.update_one({"_id": oid(hospital_id)}, {"$set": data}); return await self.get_by_id(hospital_id)
