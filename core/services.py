import re
from datetime import date, timedelta
from core.database.database import get_database
from core.cruds.base import oid, serialize

SLOTS = ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30"]

def prescription_intent(question: str) -> bool:
    normalized=question.lower().replace("follow-up","follow up")
    words=set(re.findall(r"[a-z0-9]+",normalized))
    terms={"prescription","prescribed","medicine","medicines","medication","medications","tablet","tablets","dose","dosage","frequency","duration","diagnosis","diagnosed","instruction","instructions","followup","doctor","hospital","appointment"}
    return bool(words & terms) or "follow up" in normalized or "can i take" in normalized

def validate_booking_date(value: str):
    try: selected = date.fromisoformat(value)
    except ValueError: raise ValueError("Date must use YYYY-MM-DD format")
    today = date.today()
    if selected < today or selected > today + timedelta(days=7): raise ValueError("Appointments can only be booked within the next 7 days")
    return selected

async def available_slots(hospital_id: str, doctor_id: str, booking_date: str):
    validate_booking_date(booking_date)
    db = get_database()
    booked = await db.appointments.distinct("slot", {"hospital_id": hospital_id, "doctor_id": doctor_id, "date": booking_date, "status": {"$in": ["booked", "confirmed"]}})
    return [slot for slot in SLOTS if slot not in booked]

async def patient_context(patient_id: str, question: str, prescription_id: str | None = None):
    db=get_database(); query={"patient_id":patient_id}
    if prescription_id: query["_id"]=oid(prescription_id)
    docs=await db.prescriptions.find(query).sort("created_at",-1).to_list(10)
    if not docs:return "I could not find prescription information in your record. Please contact your doctor for guidance."
    normalized=question.lower().replace("follow-up","follow up"); words=set(re.findall(r"[a-z0-9]+",normalized))
    urgent={"chest pain","cannot breathe","can't breathe","unconscious","severe bleeding","suicidal","overdose"}
    if any(term in normalized for term in urgent):return "This may need urgent medical attention. Contact your local emergency service or go to the nearest emergency department now."
    if words & {"change","increase","decrease","stop","replace","side","effects","safe","pregnant","allergy"} or "can i take" in normalized:
        return "I cannot recommend medicine changes or assess safety. Please contact your doctor or pharmacist; I can only repeat what is written in your prescription."

    def medicines(doc):
        result=[]
        for medicine in doc.get("medicines",[]):
            if isinstance(medicine,dict):
                result.append({key:str(medicine.get(key) or "").strip() for key in ("name","dosage","frequency","duration")})
            elif medicine:result.append({"name":str(medicine),"dosage":"","frequency":"","duration":""})
        return result
    all_medicines=[medicine for doc in docs for medicine in medicines(doc)]
    named=[medicine for medicine in all_medicines if medicine["name"] and set(re.findall(r"[a-z0-9]+",medicine["name"].lower())) & words]
    selected=named or all_medicines
    lines=[" — ".join(value for value in (item["name"],item["dosage"],item["frequency"],item["duration"]) if value) for item in selected]
    summary_terms={"summary","summarize","overview","everything","prescription","details"}
    medicine_terms={"medicine","medicines","medication","medications","drug","drugs","tablet","tablets","dose","dosage","frequency","often","times","take","taking","duration","long"}
    if words & summary_terms:
        doc=docs[0]; answer=f"Your latest prescription records the diagnosis as {doc.get('diagnosis') or 'not specified'}."
        if lines:answer+=f" Medicines: {'; '.join(lines)}."
        if doc.get("instructions"):answer+=f" Instructions: {doc['instructions']}."
        if doc.get("follow_up"):answer+=f" Follow-up: {doc['follow_up']}."
    elif named or words & medicine_terms:
        answer="Your prescription lists: "+"; ".join(lines)+"." if lines else "No medicines are listed in this prescription."
    elif words & {"follow","followup","review","return","again","next"}:
        values=[str(doc["follow_up"]) for doc in docs if doc.get("follow_up")];answer="Your recorded follow-up instruction is: "+"; ".join(values)+"." if values else "No follow-up instruction is recorded."
    elif words & {"instruction","instructions","advice","precaution","precautions","food","rest","care"}:
        values=[str(doc["instructions"]) for doc in docs if doc.get("instructions")];answer="Your doctor's recorded instructions are: "+"; ".join(values)+"." if values else "No additional instructions are recorded."
    elif words & {"diagnosis","diagnosed","condition","illness","problem","disease"}:
        values=[str(doc["diagnosis"]) for doc in docs if doc.get("diagnosis")];answer="The recorded diagnosis is: "+"; ".join(values)+"." if values else "No diagnosis is recorded."
    elif words & {"doctor","hospital","appointment","date"}:
        doc=docs[0]; doctor=await db.doctors.find_one({"_id":oid(doc["doctor_id"])}); hospital=await db.hospitals.find_one({"_id":oid(doc["hospital_id"])}); appointment=await db.appointments.find_one({"_id":oid(doc["appointment_id"])})
        answer=f"This prescription was issued by Dr. {doctor.get('first_name','')} {doctor.get('last_name','')} at {hospital.get('name','your hospital')}"
        if appointment:answer+=f" for your {appointment.get('date')} appointment"
        answer+="."
    else:return "I can explain the diagnosis, medicines, dosage, duration, instructions, follow-up, doctor, hospital, or appointment recorded in your prescriptions."
    return f"{answer} Follow your doctor's directions and contact them before making medical or dosage changes."
