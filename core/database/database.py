import os
from motor.motor_asyncio import AsyncIOMotorClient

_client = None

def get_database():
    global _client
    if _client is None:
        url = os.getenv("MONGO_URL")
        if not url:
            raise RuntimeError("MONGO_URL is not configured")
        _client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
    return _client[os.getenv("database_name", "cliniccare")]

async def create_indexes():
    db = get_database()
    await db.users.create_index("email", unique=True)
    await db.hospitals.create_index("registration_number", unique=True)
    await db.hospitals.create_index("owner_id", unique=True)
    await db.doctors.create_index("email", unique=True)
    await db.applications.create_index([("doctor_id", 1), ("hospital_id", 1)], unique=True)
    await db.appointments.create_index([( "hospital_id", 1), ("doctor_id", 1), ("date", 1), ("slot", 1)], unique=True, partialFilterExpression={"status": {"$in": ["booked", "confirmed"]}})
    await db.prescriptions.create_index("appointment_id", unique=True)
