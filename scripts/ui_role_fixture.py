"""Create/remove deterministic temporary accounts for all-role browser regression."""
import os
import sys
from datetime import date

from bson import ObjectId
from pymongo import MongoClient

sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from commons.auth import hash_password

PASSWORD="CityCareUITest@2026"
EMAILS=["ui.patient@example.com","ui.doctor@example.com","ui.hospital@example.com"]


def cleanup(db):
    doctor=db.doctors.find_one({"email":EMAILS[1]}); users=list(db.users.find({"email":{"$in":[EMAILS[0],EMAILS[2]]}}))
    doctor_id=str(doctor["_id"]) if doctor else None; user_ids=[str(user["_id"]) for user in users]
    query={"$or":[]}
    if doctor_id: query["$or"].append({"doctor_id":doctor_id})
    if user_ids: query["$or"].append({"patient_id":{"$in":user_ids}})
    if query["$or"]:
        appointment_ids=[str(item) for item in db.appointments.distinct("_id",query)]
        db.rag_chunks.delete_many({"appointment_id":{"$in":appointment_ids}}); db.prescriptions.delete_many({"appointment_id":{"$in":appointment_ids}}); db.appointments.delete_many(query)
    if doctor_id: db.applications.delete_many({"doctor_id":doctor_id}); db.doctors.delete_one({"_id":doctor["_id"]})
    if user_ids: db.hospitals.delete_many({"owner_id":{"$in":user_ids}})
    db.users.delete_many({"email":{"$in":EMAILS}})


def main():
    client=MongoClient(os.getenv("MONGO_URL","mongodb://127.0.0.1:27017")); db=client[os.getenv("database_name","cliniccare_rag")]; cleanup(db)
    if "--cleanup" in sys.argv: print("UI role fixtures removed"); return
    patient_id,owner_id,doctor_id,hospital_id=ObjectId(),ObjectId(),ObjectId(),ObjectId()
    hashed=hash_password(PASSWORD)
    db.users.insert_many([
        {"_id":patient_id,"first_name":"UI","last_name":"Patient","email":EMAILS[0],"mobile":"9111111111","password":hashed,"role":"patient"},
        {"_id":owner_id,"first_name":"UI","last_name":"Hospital","email":EMAILS[2],"mobile":"9222222222","password":hashed,"role":"hospital"},
    ])
    db.hospitals.insert_one({"_id":hospital_id,"owner_id":str(owner_id),"name":"UI Verification Hospital","registration_number":"UI-HOSP-2026","email":EMAILS[2],"mobile":"9222222222","address":"10 Care Road","city":"Pune","state":"Maharashtra","pincode":"411001","description":"Temporary browser verification hospital","specializations":["General Medicine"],"facilities":["OPD","Diagnostics"],"verification_status":"verified"})
    db.doctors.insert_one({"_id":doctor_id,"first_name":"UI","last_name":"Doctor","email":EMAILS[1],"mobile":"9333333333","password":hashed,"role":"doctor","verification_status":"verified","qualification":"MBBS, MD","specialization":"General Medicine","experience":8,"medical_registration_number":"UI-DOC-2026","bio":"Temporary browser verification doctor","consultation_fee":600})
    db.applications.insert_one({"doctor_id":str(doctor_id),"hospital_id":str(hospital_id),"status":"approved"})
    booked_id,completed_id=ObjectId(),ObjectId()
    base={"patient_id":str(patient_id),"doctor_id":str(doctor_id),"hospital_id":str(hospital_id),"date":date.today().isoformat(),"temperature":99.0,"symptoms":["Fever"]}
    db.appointments.insert_many([
        {"_id":booked_id,**base,"slot":"10:30","reason":"Browser verification appointment request","status":"booked"},
        {"_id":completed_id,**base,"slot":"11:00","reason":"Completed browser verification consultation","status":"completed"},
    ])
    prescription_id=ObjectId(); pdf_url=f"/patient/prescriptions/{prescription_id}/pdf"
    db.prescriptions.insert_one({"_id":prescription_id,"appointment_id":str(completed_id),"patient_id":str(patient_id),"doctor_id":str(doctor_id),"hospital_id":str(hospital_id),"diagnosis":"Seasonal viral fever","medicines":[{"name":"Paracetamol","dosage":"500 mg","frequency":"Twice daily","duration":"3 days"}],"instructions":"Rest and maintain hydration","follow_up":"Review after 3 days","doctor_notes":"Monitor temperature","pdf_url":pdf_url,"text":"Diagnosis: Seasonal viral fever. Medicines: Paracetamol 500 mg twice daily for 3 days. Instructions: Rest and maintain hydration."})
    print("UI role fixtures created")


if __name__=="__main__": main()
