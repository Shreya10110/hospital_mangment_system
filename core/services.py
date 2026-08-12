import re
from datetime import date, timedelta
from core.database.database import get_database
from core.cruds.base import oid, serialize

SLOTS = ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30"]

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
    db = get_database(); query = {"patient_id": patient_id}
    if prescription_id: query["_id"] = oid(prescription_id)
    docs = await db.prescriptions.find(query).sort("created_at", -1).to_list(10)
    if not docs: return "I could not find prescription information in your record. Please contact your doctor for guidance."
    words=set(re.findall(r"[a-z0-9]+",question.lower()))
    medicine_terms={"medicine","medicines","medication","medications","drug","drugs","tablet","tablets"}
    dosage_terms={"dose","dosage","frequency","often","times","take","taking","duration"}
    instruction_terms={"instruction","instructions","advice","precaution","precautions","food"}
    follow_up_terms={"follow","followup","review","return","again","next"}
    diagnosis_terms={"diagnosis","diagnosed","condition","illness","problem"}

    def medicine_lines(doc):
        lines=[]
        for medicine in doc.get("medicines",[]):
            if isinstance(medicine,dict):
                parts=[medicine.get("name"),medicine.get("dosage"),medicine.get("frequency"),medicine.get("duration")]
                lines.append(" — ".join(str(value) for value in parts if value))
            elif medicine: lines.append(str(medicine))
        return lines

    if words & (medicine_terms|dosage_terms):
        medicines=[line for doc in docs for line in medicine_lines(doc)]
        answer="Your prescription lists: " + "; ".join(medicines) + "." if medicines else "No medicines are listed in this prescription."
    elif words & follow_up_terms or ("follow" in words and "up" in words):
        values=[str(doc.get("follow_up")) for doc in docs if doc.get("follow_up")]
        answer="Your recorded follow-up instruction is: " + "; ".join(values) + "." if values else "No follow-up instruction is recorded in this prescription."
    elif words & instruction_terms:
        values=[str(doc.get("instructions")) for doc in docs if doc.get("instructions")]
        answer="Your doctor's recorded instructions are: " + "; ".join(values) + "." if values else "No additional instructions are recorded in this prescription."
    elif words & diagnosis_terms:
        values=[str(doc.get("diagnosis")) for doc in docs if doc.get("diagnosis")]
        answer="The recorded diagnosis is: " + "; ".join(values) + "." if values else "No diagnosis is recorded in this prescription."
    else:
        return "I can only help with the diagnosis, medicines, dosage, instructions, and follow-up recorded in your prescriptions. Please contact your doctor for other questions."
    return f"{answer} Follow your doctor's directions and contact them before making medical or dosage changes."
