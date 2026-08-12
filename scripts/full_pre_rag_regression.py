"""Destructive-only-to-own-fixtures regression for the complete CityCare pre-RAG flow."""
import json
import os
import sys
from datetime import date, timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from commons.auth import create_token

BASE=os.getenv("CITYCARE_API_URL","http://127.0.0.1:8010")
STAMP="regression.citycare@example.com"


def call(path,method="GET",body=None,token=None):
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    request=Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
    try:
        with urlopen(request,timeout=15) as response:
            raw=response.read(); return response.status,json.loads(raw) if raw and "json" in response.headers.get("content-type","") else raw
    except HTTPError as error:
        raw=error.read(); return error.code,json.loads(raw) if raw else {}


def expect(status,expected,label):
    if status!=expected: raise AssertionError(f"{label}: expected {expected}, received {status}")


def main():
    mongo=MongoClient(os.getenv("MONGO_URL","mongodb://127.0.0.1:27017")); db=mongo[os.getenv("database_name","cliniccare_rag")]
    emails={"patient":f"patient.{STAMP}","patient2":f"patient2.{STAMP}","doctor":f"doctor.{STAMP}","hospital":f"hospital.{STAMP}"}
    for doctor in db.doctors.find({"email":{"$in":list(emails.values())}}):
        did=str(doctor["_id"]); db.applications.delete_many({"doctor_id":did}); db.appointments.delete_many({"doctor_id":did}); db.prescriptions.delete_many({"doctor_id":did})
    db.doctors.delete_many({"email":{"$in":list(emails.values())}})
    for user in db.users.find({"email":{"$in":list(emails.values())}}):
        uid=str(user["_id"]); db.appointments.delete_many({"patient_id":uid}); db.prescriptions.delete_many({"patient_id":uid}); db.hospitals.delete_many({"owner_id":uid})
    db.users.delete_many({"email":{"$in":list(emails.values())}})
    hospital_id=doctor_id=patient_id=patient2_id=appointment_id=prescription_id=None
    try:
        user={"first_name":"Regression","last_name":"Patient","email":emails["patient"],"mobile":"9000000001","password":"CityCareTest@2026"}
        status,patient_auth=call("/signup","POST",user); expect(status,201,"patient signup"); patient_id=patient_auth["user"]["id"]; patient_token=patient_auth["access_token"]
        status,_=call("/doctors/register","POST",{**user,"email":emails["patient"],"qualification":"MBBS","specialization":"Medicine","experience":5,"medical_registration_number":"DUPLICATE-CHECK","consultation_fee":500}); expect(status,400,"cross-role duplicate email")
        status,patient2_auth=call("/signup","POST",{**user,"email":emails["patient2"],"mobile":"9000000002"}); expect(status,201,"second patient signup"); patient2_id=patient2_auth["user"]["id"]
        owner={**user,"email":emails["hospital"],"mobile":"9000000003"}; status,owner_auth=call("/signup","POST",owner); expect(status,201,"hospital owner signup")
        hospital_payload={"name":"Regression Care Hospital","registration_number":"REG-HOSP-2026","email":emails["hospital"],"mobile":"9000000003","address":"1 Test Avenue","city":"Pune","state":"Maharashtra","pincode":"411001","description":"Regression fixture","specializations":["Medicine"],"facilities":["OPD"]}
        status,hospital=call("/hospitals/register","POST",hospital_payload,owner_auth["access_token"]); expect(status,201,"hospital registration"); hospital_id=hospital["id"]
        status,_=call("/hospitals/register","POST",{**hospital_payload,"registration_number":"REG-HOSP-2026-B"},owner_auth["access_token"]); expect(status,409,"duplicate owner hospital")
        admin=db.users.find_one({"role":"admin"}); admin_token=create_token(str(admin["_id"]),"admin")
        status,_=call(f"/admin/hospitals/{hospital_id}/verify","PATCH",token=admin_token); expect(status,200,"admin hospital verification")
        doctor={**user,"first_name":"Regression","last_name":"Doctor","email":emails["doctor"],"mobile":"9000000004","qualification":"MBBS, MD","specialization":"Medicine","experience":7,"medical_registration_number":"REG-DOC-2026","bio":"Regression fixture","consultation_fee":650}
        status,doctor_auth=call("/doctors/register","POST",doctor); expect(status,201,"doctor signup"); doctor_id=doctor_auth["user"]["id"]; doctor_token=doctor_auth["access_token"]
        status,_=call(f"/doctor/hospitals/{hospital_id}/apply","POST",token=doctor_token); expect(status,201,"doctor application")
        hospital_token=create_token(owner_auth["user"]["id"],"hospital")
        status,requests=call("/hospital/doctor-requests",token=hospital_token); expect(status,200,"hospital requests")
        status,_=call(f"/hospital/doctor-requests/{requests[0]['id']}/approve","PATCH",token=hospital_token); expect(status,400,"unverified doctor approval blocked")
        status,_=call(f"/admin/doctors/{doctor_id}/verify","PATCH",token=admin_token); expect(status,200,"admin doctor verification")
        status,_=call(f"/hospital/doctor-requests/{requests[0]['id']}/approve","PATCH",token=hospital_token); expect(status,200,"hospital doctor approval")
        status,public_doctors=call(f"/hospitals/{hospital_id}/doctors"); expect(status,200,"approved public doctor list"); assert any(item["id"]==doctor_id for item in public_doctors)
        booking_date=(date.today()+timedelta(days=1)).isoformat(); status,slot_data=call(f"/hospitals/{hospital_id}/doctors/{doctor_id}/slots?date={booking_date}"); expect(status,200,"slots"); slot=slot_data["slots"][0]
        booking={"hospital_id":hospital_id,"doctor_id":doctor_id,"date":booking_date,"slot":slot,"reason":"Regression consultation appointment","temperature":99.1,"symptoms":["Fever"]}
        status,appointment=call("/appointments","POST",booking,patient_token); expect(status,201,"patient booking"); appointment_id=appointment["id"]
        status,_=call("/appointments","POST",booking,patient2_auth["access_token"]); expect(status,409,"double booking blocked")
        status,doctor_appointments=call("/doctor/appointments",token=doctor_token); expect(status,200,"doctor appointment list"); assert next(x for x in doctor_appointments if x["id"]==appointment_id)["patient"]["name"]=="Regression Patient"
        status,_=call(f"/appointments/{appointment_id}/accept","PATCH",token=doctor_token); expect(status,200,"doctor acceptance")
        prescription={"appointment_id":appointment_id,"diagnosis":"Viral fever","medicines":[{"name":"Paracetamol","dosage":"500 mg","frequency":"Twice daily","duration":"3 days"}],"instructions":"Rest and maintain hydration","follow_up":"Review after 3 days","doctor_notes":"Monitor temperature"}
        status,created=call("/prescriptions","POST",prescription,doctor_token); expect(status,201,"prescription creation"); prescription_id=created["id"]
        status,patient_prescriptions=call("/patient/prescriptions",token=patient_token); expect(status,200,"patient prescriptions"); assert any(x["id"]==prescription_id and x["doctor"]["name"] for x in patient_prescriptions)
        status,pdf=call(f"/patient/prescriptions/{prescription_id}/pdf",token=patient_token); expect(status,200,"prescription PDF"); assert pdf.startswith(b"%PDF")
        status,_=call(f"/patient/prescriptions/{prescription_id}",token=patient2_auth["access_token"]); expect(status,404,"patient prescription isolation")
        status,_=call("/doctor/dashboard",token=patient_token); expect(status,403,"role authorization")
        status,dashboard=call("/patient/dashboard",token=patient_token); expect(status,200,"patient dashboard"); assert dashboard["completed_count"]>=1
        status,schedule=call(f"/doctor/schedule?date={booking_date}",token=doctor_token); expect(status,200,"doctor schedule"); assert any(x["id"]==appointment_id for x in schedule)
        print("PASS: registration, dual verification, role security, booking conflict, acceptance, prescription, PDF, and patient isolation")
    finally:
        if prescription_id: db.rag_chunks.delete_many({"prescription_id":prescription_id})
        ids=[value for value in [patient_id,patient2_id] if value]
        if ids: db.prescriptions.delete_many({"patient_id":{"$in":ids}}); db.appointments.delete_many({"patient_id":{"$in":ids}})
        if doctor_id: db.applications.delete_many({"doctor_id":doctor_id}); db.doctors.delete_one({"_id":__import__('bson').ObjectId(doctor_id)})
        if hospital_id: db.hospitals.delete_one({"_id":__import__('bson').ObjectId(hospital_id)})
        db.users.delete_many({"email":{"$in":list(emails.values())}}); mongo.close()


if __name__=="__main__": main()
