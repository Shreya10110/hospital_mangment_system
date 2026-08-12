"""Create or remove a deterministic doctor UI fixture in the local database."""
import os
import sys
from datetime import date

from bson import ObjectId
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from commons.auth import hash_password

EMAIL = "doctor.ui.citycare@example.com"
PATIENT_EMAIL = "patient.ui.citycare@example.com"
LEGACY_EMAILS = ["doctor.ui@citycare.test", "patient.ui@citycare.test"]


def main():
    client = MongoClient(os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017"))
    db = client[os.getenv("database_name", "cliniccare_rag")]
    legacy_doctor = db.doctors.find_one({"email": LEGACY_EMAILS[0]})
    if legacy_doctor:
        legacy_id = str(legacy_doctor["_id"])
        db.prescriptions.delete_many({"doctor_id": legacy_id})
        db.appointments.delete_many({"doctor_id": legacy_id})
        db.applications.delete_many({"doctor_id": legacy_id})
        db.doctors.delete_one({"_id": legacy_doctor["_id"]})
    db.users.delete_many({"email": LEGACY_EMAILS[1]})
    existing = db.doctors.find_one({"email": EMAIL})
    if existing:
        doctor_id = str(existing["_id"])
        db.prescriptions.delete_many({"doctor_id": doctor_id})
        db.appointments.delete_many({"doctor_id": doctor_id})
        db.applications.delete_many({"doctor_id": doctor_id})
        db.doctors.delete_one({"_id": existing["_id"]})
    patient = db.users.find_one({"email": PATIENT_EMAIL})
    if patient:
        db.users.delete_one({"_id": patient["_id"]})
    if "--cleanup" in sys.argv:
        print("Doctor UI fixture removed")
        return
    hospital = db.hospitals.find_one({"verification_status": "verified"})
    if not hospital:
        raise RuntimeError("A verified hospital is required")
    doctor_id, patient_id, appointment_id = ObjectId(), ObjectId(), ObjectId()
    db.doctors.insert_one({"_id": doctor_id, "first_name": "Aarav", "last_name": "Mehta", "email": EMAIL, "mobile": "9876543210", "password": hash_password("CityCareDoctor@2026"), "role": "doctor", "verification_status": "verified", "qualification": "MBBS, MD", "specialization": "General Medicine", "experience": 8, "medical_registration_number": "UI-TEST-2026", "bio": "Local UI verification doctor", "consultation_fee": 700})
    db.applications.insert_one({"doctor_id": str(doctor_id), "hospital_id": str(hospital["_id"]), "status": "approved"})
    db.users.insert_one({"_id": patient_id, "first_name": "Ananya", "last_name": "Sharma", "email": PATIENT_EMAIL, "mobile": "9123456789", "role": "patient"})
    db.appointments.insert_one({"_id": appointment_id, "patient_id": str(patient_id), "doctor_id": str(doctor_id), "hospital_id": str(hospital["_id"]), "date": date.today().isoformat(), "slot": "10:30", "reason": "General check-up for a five month old baby", "temperature": None, "symptoms": [], "status": "booked"})
    print("Doctor UI fixture created")


if __name__ == "__main__":
    main()
