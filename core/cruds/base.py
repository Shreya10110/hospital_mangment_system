from fastapi import HTTPException
import uuid

def oid(value: str) -> str:
    try: return str(uuid.UUID(str(value)))
    except (ValueError,TypeError,AttributeError): raise HTTPException(status_code=404, detail="Resource not found")

def serialize(document):
    if not document: return None
    document["id"] = str(document.pop("_id"))
    return document
