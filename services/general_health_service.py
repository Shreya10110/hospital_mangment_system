"""Safe, record-free general health education through Google Gemini."""
import asyncio
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


EMERGENCY_TERMS = (
    "chest pain", "cannot breathe", "can't breathe", "difficulty breathing",
    "unconscious", "severe bleeding", "suicidal", "overdose", "stroke",
)
PERSONAL_MEDICAL_TERMS = (
    "diagnose me", "what do i have", "which medicine should i take",
    "what medicine should i take", "prescribe", "change my dose",
    "increase my dose", "decrease my dose", "stop my medicine",
)


def _unavailable_answer() -> str:
    return (
        "General health information is temporarily unavailable. "
        "Please try again later or ask a licensed healthcare professional."
    )


def _gemini_request(question: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return _unavailable_answer()

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(model, safe='-_.')}:generateContent"
    )
    system_instruction = """You are CityCare's general health education assistant.
Answer only with general, educational health information. Never diagnose the user,
interpret personal symptoms or test results, prescribe or recommend a medicine,
treatment, or dosage, or tell the user to change existing care. Do not claim access
to medical records, prescriptions, or patient data. For personal symptoms or care
decisions, recommend a licensed healthcare professional. If the question could be
an emergency, direct the user to local emergency services. Be concise, calm, and
plain-language. Start with 'General health information:' and end with
'This is general information, not a diagnosis.'"""
    body = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 350},
    }
    request = Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return _unavailable_answer()

    parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    answer = "\n".join(part.get("text", "").strip() for part in parts if part.get("text")).strip()
    return answer or _unavailable_answer()


async def general_health_answer(question: str) -> str:
    normalized = " ".join(question.lower().split())
    if any(term in normalized for term in EMERGENCY_TERMS):
        return (
            "This may need urgent medical attention. Contact your local emergency "
            "service or go to the nearest emergency department now."
        )
    if any(term in normalized for term in PERSONAL_MEDICAL_TERMS):
        return (
            "I cannot diagnose you or recommend medicines, treatments, or dosage "
            "changes. Please contact a licensed doctor or pharmacist for personal advice."
        )
    return await asyncio.to_thread(_gemini_request, question)
