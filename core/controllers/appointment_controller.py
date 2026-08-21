"""Appointment scheduling helpers backed by PostgreSQL uniqueness constraints."""
from core.database.database import get_database
from core.cruds.base import serialize
from core.cruds.appointment_crud import AppointmentCRUD

class AppointmentController:
    def __init__(self): self.appointments = AppointmentCRUD()
    async def for_patient(self, patient_id: str):
        return [serialize(doc) async for doc in get_database().appointments.find({"patient_id": patient_id}).sort("created_at", -1)]
    async def for_doctor(self, doctor_id: str):
        return [serialize(doc) async for doc in get_database().appointments.find({"doctor_id": doctor_id}).sort("date", 1)]
    async def get(self, appointment_id: str):
        return serialize(await self.appointments.get_by_id(appointment_id))
