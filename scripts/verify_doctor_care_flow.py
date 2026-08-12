"""Exercise the doctor appointment and prescription lifecycle against localhost."""
import json
import os
import sys
from datetime import date, timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bson import ObjectId
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from commons.auth import create_token
from core.services import SLOTS

BASE_URL = os.getenv("CITYCARE_API_URL", "http://127.0.0.1:8010")


def request(path, token, method="GET", body=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(
        f"{BASE_URL}{path}",
        data=payload,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def main():
    client = MongoClient(os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017"))
    db = client[os.getenv("database_name", "cliniccare")]
    application = db.applications.find_one({"status": "approved"})
    if not application:
        raise RuntimeError("A verified doctor-hospital affiliation is required for this check")
    doctor_id, hospital_id = application["doctor_id"], application["hospital_id"]
    patient_id, appointment_id, rejected_id = ObjectId(), ObjectId(), ObjectId()
    test_date = (date.today() + timedelta(days=1)).isoformat()
    occupied = set(db.appointments.distinct("slot", {"doctor_id": doctor_id, "hospital_id": hospital_id, "date": test_date, "status": {"$in": ["booked", "confirmed"]}}))
    free = [slot for slot in SLOTS if slot not in occupied]
    if len(free) < 2:
        raise RuntimeError("Two free appointment slots are required for this check")
    token = create_token(doctor_id, "doctor")
    db.users.insert_one({"_id": patient_id, "first_name": "Workflow", "last_name": "Patient", "email": "workflow.patient@citycare.test", "mobile": "9999999999", "role": "patient"})
    base = {"patient_id": str(patient_id), "doctor_id": doctor_id, "hospital_id": hospital_id, "date": test_date, "reason": "Automated doctor care lifecycle verification", "temperature": None, "symptoms": []}
    db.appointments.insert_one({"_id": appointment_id, **base, "slot": free[0], "status": "booked"})
    db.appointments.insert_one({"_id": rejected_id, **base, "slot": free[1], "status": "booked"})
    try:
        status, appointments = request("/doctor/appointments", token)
        assert status == 200 and any(item["id"] == str(appointment_id) and item["patient"]["name"] == "Workflow Patient" for item in appointments)
        status, _ = request(f"/appointments/{appointment_id}/accept", token, "PATCH")
        assert status == 200 and db.appointments.find_one({"_id": appointment_id})["status"] == "confirmed"
        status, created = request("/prescriptions", token, "POST", {"appointment_id": str(appointment_id), "diagnosis": "Routine clinical review", "medicines": [{"name": "Test medicine", "dosage": "1 unit", "frequency": "Once daily", "duration": "1 day"}], "instructions": "Verification record only", "follow_up": "As required"})
        assert status == 201 and created["appointment_id"] == str(appointment_id)
        assert db.appointments.find_one({"_id": appointment_id})["status"] == "completed"
        status, _ = request("/prescriptions", token, "POST", {"appointment_id": str(appointment_id), "diagnosis": "Duplicate check", "medicines": [{"name": "Test", "dosage": "1", "frequency": "Once", "duration": "1 day"}], "instructions": "Must be rejected"})
        assert status == 409
        status, _ = request(f"/appointments/{rejected_id}/reject", token, "PATCH")
        assert status == 200 and db.appointments.find_one({"_id": rejected_id})["status"] == "rejected"
        print("PASS: pending -> accepted -> prescribed/completed, duplicate blocked, reject verified")
    finally:
        db.prescriptions.delete_many({"appointment_id": {"$in": [str(appointment_id), str(rejected_id)]}})
        db.appointments.delete_many({"_id": {"$in": [appointment_id, rejected_id]}})
        db.users.delete_one({"_id": patient_id})
        client.close()


if __name__ == "__main__":
    main()
