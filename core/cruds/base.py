from bson import ObjectId
from fastapi import HTTPException

def oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value): raise HTTPException(status_code=404, detail="Resource not found")
    return ObjectId(value)

def serialize(document):
    if not document: return None
    document["id"] = str(document.pop("_id"))
    for key, value in list(document.items()):
        if isinstance(value, ObjectId): document[key] = str(value)
    return document
