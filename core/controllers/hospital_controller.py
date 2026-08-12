"""Hospital listing and lookup business operations."""
from core.database.database import get_database
from core.cruds.base import serialize
from core.cruds.hospital_crud import HospitalCRUD

class HospitalController:
    def __init__(self): self.hospitals = HospitalCRUD()
    async def get_verified(self, hospital_id: str):
        doc = await self.hospitals.get_by_id(hospital_id)
        if doc and doc.get("verification_status") != "verified": doc = None
        return serialize(doc)
    async def list_verified(self, query: dict):
        return [serialize(doc) async for doc in get_database().hospitals.find(query)]
