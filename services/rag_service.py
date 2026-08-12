"""Patient-isolated prescription retrieval.

The store deliberately filters by the JWT-derived patient ID before scoring, so
no prompt or client-provided identifier can cross patient boundaries. The
lightweight lexical scorer is a dependable offline fallback; replace the
embedding adapter with a hosted/vector implementation without changing this
security boundary.
"""
import re
from datetime import datetime, timezone
from core.database.database import get_database
from core.cruds.base import oid, serialize

def _tokens(text: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[a-zA-Z0-9]+", text) if len(word) > 2}

async def ingest_prescription(prescription: dict) -> None:
    db = get_database(); prescription_id = str(prescription["_id"])
    await db.rag_chunks.delete_many({"prescription_id": prescription_id})
    text = prescription.get("text", "")
    chunks = [text[i:i + 700] for i in range(0, len(text), 700)] or [text]
    entries = [{"patient_id": prescription["patient_id"], "prescription_id": prescription_id, "doctor_id": prescription["doctor_id"], "hospital_id": prescription["hospital_id"], "appointment_id": prescription["appointment_id"], "source": "prescription", "text": chunk, "tokens": list(_tokens(chunk)), "created_at": datetime.now(timezone.utc)} for chunk in chunks]
    if entries: await db.rag_chunks.insert_many(entries)

async def retrieve(patient_id: str, question: str, prescription_id: str | None = None) -> list[dict]:
    query = {"patient_id": patient_id}
    if prescription_id: query["prescription_id"] = prescription_id
    wanted = _tokens(question); chunks = [chunk async for chunk in get_database().rag_chunks.find(query)]
    chunks.sort(key=lambda chunk: len(wanted.intersection(set(chunk.get("tokens", [])))), reverse=True)
    return chunks[:4]

async def answer(patient_id: str, question: str, prescription_id: str | None = None) -> str:
    if prescription_id:
        # Avoid responding from a caller-supplied ID unless it belongs to this patient.
        prescription = await get_database().prescriptions.find_one({"_id": oid(prescription_id), "patient_id": patient_id})
        if not prescription: return "I could not find that prescription in your record."
    chunks = await retrieve(patient_id, question, prescription_id)
    if not chunks: return "I could not find prescription information for that question. Please contact your doctor for guidance."
    context = " ".join(chunk["text"] for chunk in chunks)
    if not _tokens(question).intersection(_tokens(context)):
        return "That information is not present in your prescription. Please contact your doctor for guidance."
    return f"According to your prescription: {context} For medical decisions, dosage changes, or urgent concerns, please contact your doctor."
