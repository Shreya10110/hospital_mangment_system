"""Create or refresh the explicitly configured local administrator account."""
import asyncio, os
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
from commons.auth import hash_password
from core.database.database import get_database

async def main():
    email=os.getenv("ADMIN_EMAIL","admin@citycare.local").lower()
    password=os.getenv("ADMIN_PASSWORD")
    if not password: raise SystemExit("ADMIN_PASSWORD is required")
    db=get_database(); now=datetime.now(timezone.utc)
    await db.users.update_one({"email":email},{"$set":{"first_name":"CityCare","last_name":"Admin","email":email,"mobile":"9999999999","password":hash_password(password),"role":"admin","updated_at":now},"$setOnInsert":{"created_at":now}},upsert=True)
    print(f"Admin account ready: {email}")

asyncio.run(main())
