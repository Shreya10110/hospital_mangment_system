from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Response, status
from core.database.database import DuplicateKeyError, get_database
from commons.auth import hash_password, verify_password, create_token, current_user, require
from core.cruds.base import oid, serialize
from core.models.domain import *
from core.services import available_slots, validate_booking_date, SLOTS, patient_context, prescription_intent
from services.pdf_service import prescription_pdf
from services.general_health_service import general_health_answer

router = APIRouter()
def utc(): return datetime.now(timezone.utc)
async def one(collection, resource_id, message="Resource not found"):
    doc = await get_database()[collection].find_one({"_id": oid(resource_id)})
    if not doc: raise HTTPException(404, message)
    return doc
def token_response(user):
    return {"access_token": create_token(str(user["_id"]), user["role"]), "token_type":"bearer", "user":{"id":str(user["_id"]),"name":f'{user.get("first_name", "")} {user.get("last_name", "")}'.strip(),"email":user["email"],"role":user["role"]}}

async def enrich_appointment(appointment: dict):
    db=get_database(); item=serialize(appointment)
    patient=await db.users.find_one({"_id":oid(appointment["patient_id"])})
    doctor=await db.doctors.find_one({"_id":oid(appointment["doctor_id"])})
    hospital_doc=await db.hospitals.find_one({"_id":oid(appointment["hospital_id"])})
    item["patient"]={"id":str(patient["_id"]),"name":f'{patient.get("first_name","")} {patient.get("last_name","")}'.strip(),"email":patient.get("email"),"mobile":patient.get("mobile")} if patient else None
    item["doctor"]={"id":str(doctor["_id"]),"name":f'Dr. {doctor.get("first_name","")} {doctor.get("last_name","")}'.strip(),"specialization":doctor.get("specialization")} if doctor else None
    item["hospital"]={"id":str(hospital_doc["_id"]),"name":hospital_doc.get("name"),"city":hospital_doc.get("city")} if hospital_doc else None
    return item

async def enrich_prescription(prescription_doc: dict):
    db=get_database(); item=serialize(prescription_doc)
    patient=await db.users.find_one({"_id":oid(prescription_doc["patient_id"])})
    doctor=await db.doctors.find_one({"_id":oid(prescription_doc["doctor_id"])})
    hospital_doc=await db.hospitals.find_one({"_id":oid(prescription_doc["hospital_id"])})
    appointment=await db.appointments.find_one({"_id":oid(prescription_doc["appointment_id"])})
    item["patient"]={"id":str(patient["_id"]),"name":f'{patient.get("first_name","")} {patient.get("last_name","")}'.strip(),"email":patient.get("email")} if patient else None
    item["doctor"]={"id":str(doctor["_id"]),"name":f'Dr. {doctor.get("first_name","")} {doctor.get("last_name","")}'.strip(),"qualification":doctor.get("qualification"),"specialization":doctor.get("specialization")} if doctor else None
    item["hospital"]={"id":str(hospital_doc["_id"]),"name":hospital_doc.get("name"),"address":hospital_doc.get("address"),"city":hospital_doc.get("city")} if hospital_doc else None
    item["appointment"]={"date":appointment.get("date"),"slot":appointment.get("slot"),"reason":appointment.get("reason")} if appointment else None
    return item

@router.post("/signup", status_code=201)
async def signup(payload: UserCreate):
    db=get_database(); data=payload.model_dump(); data["email"]=str(data["email"]).lower()
    if await db.doctors.find_one({"email":data["email"]}): raise HTTPException(400,"An account with this email already exists")
    data.update({"password":hash_password(data.pop("password")),"role":"patient","created_at":utc(),"updated_at":utc()})
    try: result=await db.users.insert_one(data)
    except DuplicateKeyError: raise HTTPException(400,"An account with this email already exists")
    data["_id"]=result.inserted_id; return token_response(data)
@router.post("/login")
async def login(payload: Login):
    db = get_database()
    # Doctors are stored in their own collection so their professional data stays
    # separate from a patient's profile; both account types use the same login.
    user=await db.users.find_one({"email":payload.email.lower()}) or await db.doctors.find_one({"email":payload.email.lower()})
    if not user or not verify_password(payload.password,user["password"]): raise HTTPException(401,"Invalid email or password")
    return token_response(user)
@router.get("/me")
async def me(user=Depends(current_user)):
    collection = "doctors" if user["role"] == "doctor" else "users"
    profile = await one(collection,user["id"],"User not found")
    profile.pop("password", None)
    return serialize(profile)

@router.post("/hospitals/register", status_code=201)
async def register_hospital(payload: HospitalCreate, user=Depends(current_user)):
    """Create a hospital profile and turn the authenticated owner into a hospital account.

    The profile remains pending until an administrator verifies it; changing the
    account role does not make the hospital patient-visible.
    """
    if user["role"] not in {"patient","hospital"}: raise HTTPException(403,"This account cannot register a hospital")
    if await get_database().hospitals.find_one({"owner_id":user["id"]}): raise HTTPException(409,"This account already has a hospital profile")
    data=payload.model_dump(); data.update({"owner_id":user["id"],"verification_status":"pending","created_at":utc(),"updated_at":utc()})
    try: result=await get_database().hospitals.insert_one(data)
    except DuplicateKeyError: raise HTTPException(400,"This registration number is already registered")
    await get_database().users.update_one({"_id": oid(user["id"])}, {"$set": {"role": "hospital", "updated_at": utc()}})
    data["_id"]=result.inserted_id; return serialize(data)
@router.get("/hospitals")
async def hospitals(search:str="",city:str="",state:str="",specialization:str=""):
    query={"verification_status":"verified"}
    if city: query["city"]={"$regex":city,"$options":"i"}
    if state: query["state"]={"$regex":state,"$options":"i"}
    if specialization: query["specializations"]={"$regex":specialization,"$options":"i"}
    if search: query["$or"]=[{"name":{"$regex":search,"$options":"i"}},{"city":{"$regex":search,"$options":"i"}}]
    return [serialize(d) async for d in get_database().hospitals.find(query)]
@router.get("/hospitals/me")
async def my_hospital_profile(user=Depends(require("hospital"))):
    return serialize(await owned_hospital(user))
@router.get("/hospitals/{hospital_id}")
async def hospital(hospital_id:str):
    doc=await one("hospitals",hospital_id)
    if doc["verification_status"]!="verified": raise HTTPException(404,"Hospital not found")
    return serialize(doc)
@router.get("/admin/hospitals/pending")
async def pending_hospitals(user=Depends(require("admin"))): return [serialize(d) async for d in get_database().hospitals.find({"verification_status":"pending"})]
@router.patch("/admin/hospitals/{hospital_id}/{action}")
async def hospital_action(hospital_id:str,action:str,user=Depends(require("admin"))):
    if action not in {"verify","reject","suspend"}: raise HTTPException(400,"Invalid verification action")
    result=await get_database().hospitals.update_one({"_id":oid(hospital_id)},{"$set":{"verification_status":"verified" if action=="verify" else action+"ed","updated_at":utc()}})
    if not result.matched_count: raise HTTPException(404,"Hospital not found")
    return {"message":f"Hospital {action}ed"}

@router.post("/doctors/register",status_code=201)
async def register_doctor(payload:DoctorCreate):
    db=get_database(); data=payload.model_dump(); data["email"]=str(data["email"]).lower()
    if await db.users.find_one({"email":data["email"]}): raise HTTPException(400,"An account with this email already exists")
    data.update({"password":hash_password(data.pop("password")),"role":"doctor","verification_status":"pending","created_at":utc(),"updated_at":utc()})
    try: result=await get_database().doctors.insert_one(data)
    except DuplicateKeyError: raise HTTPException(400,"An account with this email already exists")
    data["_id"]=result.inserted_id; return token_response(data)
@router.get("/doctors/{doctor_id}")
async def doctor_profile(doctor_id:str):
    doctor=await one("doctors",doctor_id,"Doctor not found")
    if doctor["verification_status"]!="verified": raise HTTPException(404,"Doctor not found")
    applications=[a async for a in get_database().applications.find({"doctor_id":doctor_id,"status":"approved"})]
    doctor.pop("password",None); doctor["hospitals"]=[serialize(await one("hospitals",a["hospital_id"])) for a in applications]
    return serialize(doctor)
@router.get("/hospitals/{hospital_id}/doctors")
async def hospital_doctors(hospital_id:str):
    await hospital(hospital_id); apps=[a async for a in get_database().applications.find({"hospital_id":hospital_id,"status":"approved"})]
    ids=[oid(a["doctor_id"]) for a in apps]; results=[]
    async for doc in get_database().doctors.find({"_id":{"$in":ids},"verification_status":"verified"}): doc.pop("password",None); results.append(serialize(doc))
    return results
@router.post("/doctor/hospitals/{hospital_id}/apply",status_code=201)
async def apply_to_hospital(hospital_id:str,user=Depends(require("doctor"))):
    doctor=await one("doctors",user["id"])
    if doctor.get("verification_status") != "verified":
        raise HTTPException(403,"Your doctor account must be verified by an admin before requesting a hospital affiliation")
    target=await one("hospitals",hospital_id)
    if target["verification_status"]!="verified": raise HTTPException(400,"Hospital is not accepting applications")
    try: await get_database().applications.insert_one({"doctor_id":user["id"],"hospital_id":hospital_id,"status":"pending","created_at":utc()})
    except DuplicateKeyError: raise HTTPException(409,"An application already exists")
    return {"message":"Application sent"}

@router.get("/hospitals/{hospital_id}/doctors/{doctor_id}/slots")
async def slots(hospital_id:str,doctor_id:str,date:str):
    try: validate_booking_date(date)
    except ValueError as error: raise HTTPException(status_code=422,detail=str(error))
    hospital_doc=await one("hospitals",hospital_id,"Hospital not found")
    doctor_doc=await one("doctors",doctor_id,"Doctor not found")
    approved=await get_database().applications.find_one({"doctor_id":doctor_id,"hospital_id":hospital_id,"status":"approved"})
    if hospital_doc.get("verification_status")!="verified" or doctor_doc.get("verification_status")!="verified" or not approved:
        raise HTTPException(status_code=404,detail="Doctor is not available at this hospital")
    return {"date":date,"slots":await available_slots(hospital_id,doctor_id,date)}
@router.post("/appointments",status_code=201)
async def book(payload:AppointmentCreate,user=Depends(require("patient"))):
    try: validate_booking_date(payload.date)
    except ValueError as e: raise HTTPException(422,str(e))
    if payload.slot not in SLOTS: raise HTTPException(422,"Invalid appointment slot")
    hospital_doc=await one("hospitals",payload.hospital_id); doctor_doc=await one("doctors",payload.doctor_id)
    approved=await get_database().applications.find_one({"doctor_id":payload.doctor_id,"hospital_id":payload.hospital_id,"status":"approved"})
    if hospital_doc["verification_status"]!="verified" or doctor_doc["verification_status"]!="verified" or not approved: raise HTTPException(400,"This doctor is not available at this hospital")
    data=payload.model_dump(); data.update({"patient_id":user["id"],"status":"booked","created_at":utc(),"updated_at":utc()})
    try: result=await get_database().appointments.insert_one(data)
    except DuplicateKeyError: raise HTTPException(409,"That slot just got booked — please pick another")
    data["_id"]=result.inserted_id; return serialize(data)
@router.get("/appointments/me")
async def my_appointments(user=Depends(require("patient"))):
    return [await enrich_appointment(doc) async for doc in get_database().appointments.find({"patient_id":user["id"]}).sort("created_at",-1)]

@router.get("/appointments/upcoming")
async def upcoming_appointments(user=Depends(require("patient"))):
    query={"patient_id":user["id"],"date":{"$gte":date.today().isoformat()},"status":{"$in":["booked","confirmed"]}}
    return [await enrich_appointment(doc) async for doc in get_database().appointments.find(query).sort([("date",1),("slot",1)])]

@router.get("/appointments/completed")
async def completed_appointments(user=Depends(require("patient"))):
    return [await enrich_appointment(doc) async for doc in get_database().appointments.find({"patient_id":user["id"],"status":"completed"}).sort("date",-1)]

@router.get("/patient/dashboard")
async def patient_dashboard(user=Depends(require("patient"))):
    db=get_database(); upcoming=await upcoming_appointments(user)
    return {"upcoming_count":len(upcoming),"completed_count":await db.appointments.count_documents({"patient_id":user["id"],"status":"completed"}),"cancelled_count":await db.appointments.count_documents({"patient_id":user["id"],"status":"cancelled"}),"next_appointment":upcoming[0] if upcoming else None}
@router.patch("/appointments/{appointment_id}/cancel")
async def cancel(appointment_id:str,user=Depends(current_user)):
    appointment=await one("appointments",appointment_id)
    if user["role"]=="patient" and appointment["patient_id"]!=user["id"]: raise HTTPException(403,"This appointment does not belong to you")
    if user["role"]=="doctor" and appointment["doctor_id"]!=user["id"]: raise HTTPException(403,"This appointment is not assigned to you")
    if user["role"] not in {"patient","doctor"}: raise HTTPException(403,"You do not have permission for this action")
    if appointment["status"] not in {"booked","confirmed"}: raise HTTPException(409,"Only an active appointment can be cancelled")
    await get_database().appointments.update_one({"_id":appointment["_id"]},{"$set":{"status":"cancelled","updated_at":utc()}}); return {"message":"Appointment cancelled"}
@router.patch("/appointments/{appointment_id}/accept")
async def accept(appointment_id:str,user=Depends(require("doctor"))):
    appointment=await one("appointments",appointment_id)
    if appointment["doctor_id"]!=user["id"]: raise HTTPException(403,"This appointment is not assigned to you")
    if appointment["status"]!="booked": raise HTTPException(409,"Only a booked appointment request can be accepted")
    await get_database().appointments.update_one({"_id":appointment["_id"]},{"$set":{"status":"confirmed","updated_at":utc()}}); return {"message":"Appointment confirmed"}

@router.patch("/appointments/{appointment_id}/reject")
async def reject_appointment(appointment_id:str,user=Depends(require("doctor"))):
    appointment=await one("appointments",appointment_id)
    if appointment["doctor_id"]!=user["id"]: raise HTTPException(403,"This appointment is not assigned to you")
    if appointment["status"]!="booked": raise HTTPException(409,"Only a booked appointment request can be rejected")
    await get_database().appointments.update_one({"_id":appointment["_id"]},{"$set":{"status":"rejected","updated_at":utc()}})
    return {"message":"Appointment request rejected"}

@router.patch("/appointments/{appointment_id}/complete")
async def complete_appointment(appointment_id:str,user=Depends(require("doctor"))):
    appointment=await one("appointments",appointment_id)
    if appointment["doctor_id"]!=user["id"]: raise HTTPException(403,"This appointment is not assigned to you")
    if appointment["status"]!="confirmed": raise HTTPException(409,"Accept the appointment before completing it")
    await get_database().appointments.update_one({"_id":appointment["_id"]},{"$set":{"status":"completed","updated_at":utc()}})
    return {"message":"Appointment completed"}

@router.get("/doctor/appointments")
async def doctor_appointments(user=Depends(require("doctor"))):
    db=get_database(); results=[]
    async for appointment in db.appointments.find({"doctor_id":user["id"]}).sort([("date",1),("slot",1)]):
        item=await enrich_appointment(appointment)
        existing=await db.prescriptions.find_one({"appointment_id":item["id"]},{"_id":1})
        item["prescription_id"]=str(existing["_id"]) if existing else None
        results.append(item)
    return results

@router.get("/doctor/schedule")
async def doctor_schedule(date:str,user=Depends(require("doctor"))):
    try: datetime.strptime(date,"%Y-%m-%d")
    except ValueError: raise HTTPException(422,"Date must use YYYY-MM-DD format")
    return [await enrich_appointment(doc) async for doc in get_database().appointments.find({"doctor_id":user["id"],"date":date}).sort("slot",1)]

@router.post("/prescriptions",status_code=201)
async def prescription(payload:PrescriptionCreate,user=Depends(require("doctor"))):
    appointment=await one("appointments",payload.appointment_id)
    if appointment["doctor_id"]!=user["id"]: raise HTTPException(403,"This appointment is not assigned to you")
    if appointment["status"] not in {"confirmed","completed"}: raise HTTPException(400,"Confirm the appointment before creating a prescription")
    data=payload.model_dump(); data.update({k:appointment[k] for k in ("patient_id","doctor_id","hospital_id")}); data.update({"created_at":utc(),"text":""})
    data["text"]=f"Diagnosis: {data['diagnosis']}. Medicines: {data['medicines']}. Instructions: {data['instructions']}. Follow up: {data['follow_up'] or 'Not specified'}. Doctor notes: {data['doctor_notes'] or 'Not specified'}."
    try: result=await get_database().prescriptions.insert_one(data)
    except DuplicateKeyError: raise HTTPException(409,"A prescription already exists for this appointment")
    data["_id"]=result.inserted_id; data["pdf_url"]=f"/patient/prescriptions/{result.inserted_id}/pdf"
    await get_database().prescriptions.update_one({"_id":result.inserted_id},{"$set":{"pdf_url":data["pdf_url"]}})
    await get_database().appointments.update_one({"_id":appointment["_id"]},{"$set":{"status":"completed","updated_at":utc()}})
    return serialize(data)
@router.get("/patient/prescriptions")
async def patient_prescriptions(user=Depends(require("patient"))):
    return [await enrich_prescription(doc) async for doc in get_database().prescriptions.find({"patient_id":user["id"]}).sort("created_at",-1)]

@router.get("/patient/prescriptions/{prescription_id}")
async def patient_prescription_detail(prescription_id:str,user=Depends(require("patient"))):
    doc=await get_database().prescriptions.find_one({"_id":oid(prescription_id),"patient_id":user["id"]})
    if not doc: raise HTTPException(404,"Prescription not found")
    return await enrich_prescription(doc)

@router.get("/patient/prescriptions/{prescription_id}/pdf")
async def patient_prescription_pdf(prescription_id:str,user=Depends(require("patient"))):
    doc=await get_database().prescriptions.find_one({"_id":oid(prescription_id),"patient_id":user["id"]})
    if not doc: raise HTTPException(404,"Prescription not found")
    return Response(content=prescription_pdf(await enrich_prescription(doc)),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="citycare-prescription-{prescription_id}.pdf"'})

@router.get("/prescriptions/{prescription_id}")
async def prescription_detail(prescription_id:str,user=Depends(current_user)):
    doc=await one("prescriptions",prescription_id,"Prescription not found")
    if user["role"]=="patient" and doc["patient_id"]!=user["id"]: raise HTTPException(403,"This prescription does not belong to you")
    if user["role"]=="doctor" and doc["doctor_id"]!=user["id"]: raise HTTPException(403,"This prescription is not assigned to you")
    if user["role"] not in {"patient","doctor"}: raise HTTPException(403,"You do not have permission for this prescription")
    return await enrich_prescription(doc)
@router.post("/chatbot/ask")
async def ask(payload:AskCreate,user=Depends(require("patient"))):
    if payload.prescription_id or prescription_intent(payload.question):
        answer=await patient_context(user["id"],payload.question,payload.prescription_id); source="prescription"
    else:
        answer=await general_health_answer(payload.question); source="general_health"
    return {"answer":answer,"source":source,"disclaimer":"Prescription answers repeat stored records; general answers are educational only. Consult your doctor for medical decisions."}

# --- T12–T28: administration, workspaces, and complete care lifecycle -------
async def owned_hospital(user: dict, verified: bool = False):
    hospital_doc = await get_database().hospitals.find_one({"owner_id": user["id"]})
    if not hospital_doc:
        raise HTTPException(404, "Hospital profile not found")
    if verified and hospital_doc["verification_status"] != "verified":
        raise HTTPException(403, "Your hospital must be verified for this action")
    return hospital_doc

@router.get("/admin/hospitals")
async def admin_hospitals(user=Depends(require("admin"))):
    return [serialize(doc) async for doc in get_database().hospitals.find().sort("created_at", -1)]

@router.get("/admin/hospitals/verified")
async def admin_verified_hospitals(user=Depends(require("admin"))):
    return [serialize(doc) async for doc in get_database().hospitals.find({"verification_status":"verified"}).sort("updated_at", -1)]

@router.get("/admin/hospitals/{hospital_id}")
async def admin_hospital(hospital_id: str, user=Depends(require("admin"))):
    return serialize(await one("hospitals", hospital_id, "Hospital not found"))

@router.get("/admin/doctors/pending")
async def pending_doctors(user=Depends(require("admin"))):
    docs = []
    async for doc in get_database().doctors.find({"verification_status": "pending"}).sort("created_at", -1):
        doc.pop("password", None); docs.append(serialize(doc))
    return docs

@router.get("/admin/doctors/verified")
async def admin_verified_doctors(user=Depends(require("admin"))):
    db=get_database(); results=[]
    async for doctor in db.doctors.find({"verification_status":"verified"}).sort("updated_at", -1):
        doctor.pop("password",None); item=serialize(doctor); affiliations=[]
        async for application in db.applications.find({"doctor_id":item["id"]}):
            hospital_doc=await db.hospitals.find_one({"_id":oid(application["hospital_id"])})
            affiliations.append({"hospital_id":application["hospital_id"],"hospital_name":hospital_doc.get("name") if hospital_doc else "Unavailable hospital","hospital_approval_status":application.get("status","pending")})
        item["admin_verification_status"]="verified"; item["affiliations"]=affiliations; results.append(item)
    return results

@router.patch("/admin/doctors/{doctor_id}/{action}")
async def doctor_verification(doctor_id: str, action: str, user=Depends(require("admin"))):
    statuses = {"verify": "verified", "reject": "rejected", "suspend": "suspended"}
    if action not in statuses: raise HTTPException(400, "Invalid verification action")
    result = await get_database().doctors.update_one({"_id": oid(doctor_id)}, {"$set": {"verification_status": statuses[action], "updated_at": utc()}})
    if not result.matched_count: raise HTTPException(404, "Doctor not found")
    return {"message": f"Doctor {statuses[action]}"}

@router.get("/hospital/profile")
async def hospital_profile(user=Depends(require("hospital"))):
    return serialize(await owned_hospital(user))

@router.patch("/hospital/profile")
async def update_hospital_profile(payload: HospitalCreate, user=Depends(require("hospital"))):
    profile = await owned_hospital(user)
    data = payload.model_dump(); data["updated_at"] = utc()
    await get_database().hospitals.update_one({"_id": profile["_id"]}, {"$set": data})
    profile.update(data); return serialize(profile)

@router.get("/hospital/doctor-requests")
async def hospital_doctor_requests(user=Depends(require("hospital"))):
    profile = await owned_hospital(user, verified=True); results=[]
    async for application in get_database().applications.find({"hospital_id": str(profile["_id"]), "status": "pending"}):
        doctor = await get_database().doctors.find_one({"_id": oid(application["doctor_id"])})
        if doctor:
            doctor.pop("password", None); item=serialize(application); item["request_status"]=item.get("status","pending"); item["doctor"]=serialize(doctor); item["doctor"]["admin_verification_status"]=item["doctor"].get("verification_status"); results.append(item)
    return results

@router.patch("/hospital/doctor-requests/{application_id}/{action}")
async def review_doctor_request(application_id: str, action: str, user=Depends(require("hospital"))):
    if action not in {"approve", "reject"}: raise HTTPException(400, "Invalid application action")
    profile = await owned_hospital(user, verified=True)
    application = await get_database().applications.find_one({"_id": oid(application_id), "hospital_id": str(profile["_id"]), "status":"pending"})
    if not application: raise HTTPException(404, "Application not found")
    doctor = await one("doctors", application["doctor_id"], "Doctor not found")
    if action == "approve" and doctor["verification_status"] != "verified":
        raise HTTPException(400, "Only admin-verified doctors can be approved")
    status_value = "approved" if action == "approve" else "rejected"
    await get_database().applications.update_one({"_id": application["_id"]}, {"$set": {"status": status_value, "updated_at": utc()}})
    return {"message": f"Doctor application {status_value}"}

@router.get("/hospital/doctors")
@router.get("/hospital/doctors/verified")
async def hospital_workspace_doctors(user=Depends(require("hospital"))):
    profile = await owned_hospital(user, verified=True); app_ids=[]
    async for app in get_database().applications.find({"hospital_id": str(profile["_id"]), "status": "approved"}): app_ids.append(oid(app["doctor_id"]))
    results=[]
    async for doctor in get_database().doctors.find({"_id": {"$in": app_ids},"verification_status":"verified"}):
        doctor.pop("password", None); item=serialize(doctor); item["hospital_approval_status"]="approved"; results.append(item)
    return results

@router.get("/hospital/appointments")
async def hospital_appointments(user=Depends(require("hospital"))):
    profile = await owned_hospital(user, verified=True)
    return [await enrich_appointment(doc) async for doc in get_database().appointments.find({"hospital_id": str(profile["_id"])}).sort([("date", 1), ("slot", 1)])]

@router.get("/hospital/stats")
async def hospital_stats(user=Depends(require("hospital"))):
    profile = await owned_hospital(user, verified=True); hid=str(profile["_id"]); today=date.today().isoformat(); db=get_database()
    return {"total_verified_doctors": await db.applications.count_documents({"hospital_id":hid,"status":"approved"}), "pending_doctor_requests": await db.applications.count_documents({"hospital_id":hid,"status":"pending"}), "todays_appointments": await db.appointments.count_documents({"hospital_id":hid,"date":today,"status":{"$in":["booked","confirmed"]}}), "upcoming_appointments": await db.appointments.count_documents({"hospital_id":hid,"date":{"$gt":today},"status":{"$in":["booked","confirmed"]}})}

@router.get("/hospital/dashboard")
async def hospital_dashboard(user=Depends(require("hospital"))):
    profile=await owned_hospital(user, verified=True); hid=str(profile["_id"]); db=get_database(); stats=await hospital_stats(user)
    return {"hospital": serialize(profile), "stats": stats, "doctor_requests": [serialize(doc) async for doc in db.applications.find({"hospital_id":hid,"status":"pending"}).limit(5)], "todays_appointments": [serialize(doc) async for doc in db.appointments.find({"hospital_id":hid,"date":date.today().isoformat()}).sort("slot",1)]}

@router.get("/doctor/me")
@router.get("/doctor/profile")
async def doctor_me(user=Depends(require("doctor"))):
    doctor=await one("doctors", user["id"], "Doctor not found"); doctor.pop("password", None); return serialize(doctor)

@router.patch("/doctor/me")
@router.patch("/doctor/profile")
async def update_doctor_profile(payload: DoctorCreate, user=Depends(require("doctor"))):
    doctor=await one("doctors", user["id"], "Doctor not found"); data=payload.model_dump(exclude={"password"}); data["updated_at"]=utc()
    await get_database().doctors.update_one({"_id":doctor["_id"]},{"$set":data}); doctor.update(data); doctor.pop("password",None); return serialize(doctor)

@router.get("/doctor/hospital-applications")
async def doctor_applications(user=Depends(require("doctor"))):
    apps=[]
    async for app in get_database().applications.find({"doctor_id":user["id"]}).sort("created_at", -1):
        item=serialize(app); hospital_doc=await get_database().hospitals.find_one({"_id":oid(app["hospital_id"])}); item["hospital"]=serialize(hospital_doc) if hospital_doc else None; apps.append(item)
    return apps

@router.get("/doctor/hospitals")
async def doctor_hospitals(user=Depends(require("doctor"))):
    hospitals=[]
    async for app in get_database().applications.find({"doctor_id":user["id"],"status":"approved"}):
        hospital_doc=await get_database().hospitals.find_one({"_id":oid(app["hospital_id"])});
        if hospital_doc: hospitals.append(serialize(hospital_doc))
    return hospitals

@router.get("/doctor/dashboard")
@router.get("/doctor/stats")
async def doctor_dashboard(user=Depends(require("doctor"))):
    db=get_database(); did=user["id"]; today=date.today().isoformat()
    return {"todays_appointments": await db.appointments.count_documents({"doctor_id":did,"date":today,"status":{"$in":["booked","confirmed"]}}), "upcoming_appointments": await db.appointments.count_documents({"doctor_id":did,"date":{"$gt":today},"status":{"$in":["booked","confirmed"]}}), "completed_patients": len(await db.appointments.distinct("patient_id", {"doctor_id":did,"status":"completed"})), "total_patients": len(await db.appointments.distinct("patient_id", {"doctor_id":did}))}

@router.get("/doctor/completed-patients")
async def completed_patients(user=Depends(require("doctor"))):
    ids=await get_database().appointments.distinct("patient_id", {"doctor_id":user["id"],"status":"completed"}); results=[]
    for patient_id in ids:
        patient=await get_database().users.find_one({"_id":oid(patient_id)});
        if patient: patient.pop("password",None); results.append(serialize(patient))
    return results

@router.get("/doctor/prescriptions")
async def doctor_prescriptions(user=Depends(require("doctor"))):
    db=get_database(); results=[]
    async for prescription_doc in db.prescriptions.find({"doctor_id":user["id"]}).sort("created_at",-1):
        results.append(await enrich_prescription(prescription_doc))
    return results
