"""Supabase PostgreSQL persistence with readable, relational CityCare tables."""
import json, os, re, uuid
from datetime import date, datetime
from urllib.parse import urlparse
import asyncpg

class DuplicateKeyError(Exception): pass

TABLES={
 "users":("users",{"first_name":"text","last_name":"text","email":"text","mobile":"text","password":"password_hash:text","role":"text","created_at":"timestamptz","updated_at":"timestamptz"}),
 "doctors":("doctors",{"first_name":"text","last_name":"text","email":"text","mobile":"text","password":"password_hash:text","role":"text","verification_status":"text","qualification":"text","specialization":"text","experience":"int","medical_registration_number":"text","bio":"text","consultation_fee":"float","profile_image":"text","created_at":"timestamptz","updated_at":"timestamptz"}),
 "hospitals":("hospitals",{"owner_id":"uuid","name":"text","registration_number":"text","email":"text","mobile":"text","address":"text","city":"text","state":"text","pincode":"text","description":"text","specializations":"array","facilities":"array","logo":"text","verification_status":"text","created_at":"timestamptz","updated_at":"timestamptz"}),
 "applications":("doctor_hospital_applications",{"doctor_id":"uuid","hospital_id":"uuid","status":"text","created_at":"timestamptz","updated_at":"timestamptz"}),
 "appointments":("appointments",{"patient_id":"uuid","doctor_id":"uuid","hospital_id":"uuid","date":"date","slot":"text","reason":"text","patient_age":"int","temperature":"float","symptoms":"array","status":"text","created_at":"timestamptz","updated_at":"timestamptz"}),
 "prescriptions":("prescriptions",{"appointment_id":"uuid","patient_id":"uuid","doctor_id":"uuid","hospital_id":"uuid","diagnosis":"text","medicines":"json","instructions":"text","follow_up":"text","doctor_notes":"text","pdf_url":"text","text":"text","created_at":"timestamptz"}),
 "rag_chunks":("prescription_context_chunks",{"prescription_id":"uuid","patient_id":"uuid","doctor_id":"uuid","hospital_id":"uuid","appointment_id":"uuid","source":"text","text":"text","tokens":"array","created_at":"timestamptz"})}

DDL=[
"CREATE TABLE IF NOT EXISTS users(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),first_name text NOT NULL,last_name text NOT NULL,email text NOT NULL,mobile text NOT NULL,password_hash text,role text NOT NULL CHECK(role IN ('patient','hospital','admin')),created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now())",
"CREATE UNIQUE INDEX IF NOT EXISTS users_email_uq ON users(lower(email))",
"CREATE TABLE IF NOT EXISTS doctors(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),first_name text NOT NULL,last_name text NOT NULL,email text NOT NULL,mobile text NOT NULL,password_hash text,role text NOT NULL DEFAULT 'doctor',verification_status text NOT NULL DEFAULT 'pending',qualification text,specialization text,experience integer,medical_registration_number text,bio text,consultation_fee double precision,profile_image text,created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now())",
"CREATE UNIQUE INDEX IF NOT EXISTS doctors_email_uq ON doctors(lower(email))",
"CREATE TABLE IF NOT EXISTS hospitals(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,name text NOT NULL,registration_number text NOT NULL,email text NOT NULL,mobile text,address text,city text,state text,pincode text,description text,specializations text[] NOT NULL DEFAULT '{}',facilities text[] NOT NULL DEFAULT '{}',logo text,verification_status text NOT NULL DEFAULT 'pending',created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),UNIQUE(owner_id),UNIQUE(registration_number))",
"CREATE TABLE IF NOT EXISTS doctor_hospital_applications(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),doctor_id uuid NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,hospital_id uuid NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,status text NOT NULL DEFAULT 'pending',created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz,UNIQUE(doctor_id,hospital_id))",
"CREATE TABLE IF NOT EXISTS appointments(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),patient_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,doctor_id uuid NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,hospital_id uuid NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,date date NOT NULL,slot text NOT NULL,reason text NOT NULL,temperature double precision,symptoms text[] NOT NULL DEFAULT '{}',status text NOT NULL DEFAULT 'booked',created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now())",
"ALTER TABLE appointments ADD COLUMN IF NOT EXISTS patient_age integer CHECK(patient_age BETWEEN 0 AND 120)",
"CREATE UNIQUE INDEX IF NOT EXISTS appointments_active_slot_uq ON appointments(hospital_id,doctor_id,date,slot) WHERE status IN ('booked','confirmed')",
"CREATE TABLE IF NOT EXISTS prescriptions(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),appointment_id uuid NOT NULL UNIQUE REFERENCES appointments(id) ON DELETE CASCADE,patient_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,doctor_id uuid NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,hospital_id uuid NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,diagnosis text NOT NULL,medicines jsonb NOT NULL DEFAULT '[]',instructions text NOT NULL,follow_up text,doctor_notes text,pdf_url text,text text,created_at timestamptz NOT NULL DEFAULT now())",
"CREATE TABLE IF NOT EXISTS prescription_context_chunks(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),prescription_id uuid NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,patient_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,doctor_id uuid NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,hospital_id uuid NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,appointment_id uuid NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,source text NOT NULL DEFAULT 'prescription',text text NOT NULL,tokens text[] NOT NULL DEFAULT '{}',created_at timestamptz NOT NULL DEFAULT now())"]

def _matches(doc,query):
 for key,expected in (query or {}).items():
  if key=="$or":
   if not any(_matches(doc,item) for item in expected): return False
   continue
  actual=doc.get(key)
  if isinstance(expected,dict):
   for op,value in expected.items():
    if op=="$options": continue
    if op=="$in" and actual not in value:return False
    if op=="$gte" and (actual is None or actual<value):return False
    if op=="$gt" and (actual is None or actual<=value):return False
    if op=="$lte" and (actual is None or actual>value):return False
    if op=="$lt" and (actual is None or actual>=value):return False
    if op=="$regex":
     flags=re.I if "i" in expected.get("$options","") else 0; values=actual if isinstance(actual,list) else [actual]
     if not any(re.search(str(value),str(item or ""),flags) for item in values):return False
  elif actual!=expected:return False
 return True

class Result:
 def __init__(self,inserted_id=None,matched_count=0,modified_count=0,deleted_count=0):self.inserted_id=inserted_id;self.matched_count=matched_count;self.modified_count=modified_count;self.deleted_count=deleted_count

class Cursor:
 def __init__(self,collection,query,projection=None):self.collection=collection;self.query=query or {};self.projection=projection;self.sorts=[];self.maximum=None;self.iterator=None
 def sort(self,key,direction=None):self.sorts=key if isinstance(key,list) else [(key,direction or 1)];return self
 def limit(self,value):self.maximum=value;return self
 async def items(self):
  items=[item for item in await self.collection.all() if _matches(item,self.query)]
  for key,direction in reversed(self.sorts):items.sort(key=lambda item:(item.get(key) is None,item.get(key)),reverse=direction<0)
  if self.maximum is not None:items=items[:self.maximum]
  if self.projection=={"_id":1}:items=[{"_id":item["_id"]} for item in items]
  return items
 async def to_list(self,length=None):items=await self.items();return items if length is None else items[:length]
 def __aiter__(self):self.iterator=None;return self
 async def __anext__(self):
  if self.iterator is None:self.iterator=iter(await self.items())
  try:return next(self.iterator)
  except StopIteration:raise StopAsyncIteration

class Collection:
 def __init__(self,database,name):self.database=database;self.name=name;self.table,self.fields=TABLES[name]
 def _column(self,key):
  spec=self.fields[key];return spec.split(":",1)[0] if ":" in spec else key
 def _type(self,key):return self.fields[key].split(":")[-1]
 def _encode(self,key,value):
  kind=self._type(key)
  if value is None:return None
  if kind=="json":return json.dumps(value)
  if kind=="uuid":return uuid.UUID(str(value))
  if kind=="date":return value if isinstance(value,date) else date.fromisoformat(str(value))
  if kind=="timestamptz":return value if isinstance(value,datetime) else datetime.fromisoformat(str(value).replace("Z","+00:00"))
  return value
 def _cast(self,key,index):return {"uuid":"::uuid","date":"::date","timestamptz":"::timestamptz","json":"::jsonb"}.get(self._type(key),"")
 def _decode(self,row):
  doc={"_id":str(row["id"])}
  for key in self.fields:
   value=row[self._column(key)]
   if isinstance(value,uuid.UUID):value=str(value)
   elif isinstance(value,date) and not isinstance(value,datetime):value=value.isoformat()
   elif self._type(key)=="json" and isinstance(value,str):value=json.loads(value)
   doc[key]=value
  return doc
 async def all(self):
  async with self.database.pool.acquire() as c:rows=await c.fetch(f"SELECT * FROM {self.table}")
  return [self._decode(row) for row in rows]
 def find(self,query=None,projection=None):return Cursor(self,query,projection)
 async def find_one(self,query,projection=None):
  items=await self.find(query,projection).limit(1).to_list(1);return items[0] if items else None
 async def insert_one(self,document):
  identifier=str(document.get("_id") or uuid.uuid4());keys=[key for key in document if key!="_id" and key in self.fields];columns=[self._column(key) for key in keys]
  placeholders=[f"${i+2}{self._cast(key,i+2)}" for i,key in enumerate(keys)];values=[self._encode(key,document[key]) for key in keys]
  sql=f"INSERT INTO {self.table}(id{',' if columns else ''}{','.join(columns)}) VALUES($1::uuid{',' if placeholders else ''}{','.join(placeholders)})"
  try:
   async with self.database.pool.acquire() as c:await c.execute(sql,identifier,*values)
  except asyncpg.UniqueViolationError as error:raise DuplicateKeyError(str(error)) from error
  return Result(inserted_id=identifier)
 async def insert_many(self,documents):return Result(inserted_id=[(await self.insert_one(doc)).inserted_id for doc in documents])
 async def update_one(self,query,update,upsert=False):
  current=await self.find_one(query)
  if current is None and not upsert:return Result()
  if current is None:
   data={k:v for k,v in query.items() if k in self.fields and not isinstance(v,dict)};data.update(update.get("$setOnInsert",{}));data.update(update.get("$set",{}));result=await self.insert_one(data);return Result(result.inserted_id,1,1)
  identifier=current["_id"];changes={k:v for k,v in update.get("$set",{}).items() if k in self.fields}
  if not changes:return Result(matched_count=1)
  keys=list(changes);assignments=[f"{self._column(key)}=${i+2}{self._cast(key,i+2)}" for i,key in enumerate(keys)];values=[self._encode(key,changes[key]) for key in keys]
  try:
   async with self.database.pool.acquire() as c:await c.execute(f"UPDATE {self.table} SET {','.join(assignments)} WHERE id=$1::uuid",identifier,*values)
  except asyncpg.UniqueViolationError as error:raise DuplicateKeyError(str(error)) from error
  return Result(matched_count=1,modified_count=1)
 async def delete_many(self,query):
  items=[item for item in await self.all() if _matches(item,query)]
  async with self.database.pool.acquire() as c:
   for item in items:await c.execute(f"DELETE FROM {self.table} WHERE id=$1::uuid",item["_id"])
  return Result(deleted_count=len(items))
 async def delete_one(self,query):
  item=await self.find_one(query)
  if not item:return Result()
  async with self.database.pool.acquire() as c:await c.execute(f"DELETE FROM {self.table} WHERE id=$1::uuid",item["_id"])
  return Result(deleted_count=1)
 async def count_documents(self,query):return len([item for item in await self.all() if _matches(item,query)])
 async def distinct(self,key,query=None):
  values=[]
  for item in await self.all():
   if _matches(item,query or {}) and item.get(key) not in values:values.append(item.get(key))
  return values
 async def create_index(self,*args,**kwargs):return None

class Database:
 def __init__(self):self.pool=None;self.collections={}
 def __getitem__(self,name):return self.collection(name)
 def __getattr__(self,name):
  if name.startswith("_"):raise AttributeError(name)
  return self.collection(name)
 def collection(self,name):
  if name not in self.collections:self.collections[name]=Collection(self,name)
  return self.collections[name]
 async def initialize(self):
  if self.pool is not None:return
  url=os.getenv("DATABASE_URL")
  if url:self.pool=await asyncpg.create_pool(url,ssl="require",min_size=1,max_size=5)
  else:
   project=os.getenv("SUPABASE_URL");password=os.getenv("SUPABASE_DB_PASSWORD")
   if not project or not password:raise RuntimeError("DATABASE_URL is required")
   ref=(urlparse(project).hostname or "").split(".")[0];self.pool=await asyncpg.create_pool(host=f"db.{ref}.supabase.co",user="postgres",password=password,database="postgres",ssl="require",min_size=1,max_size=5)
  async with self.pool.acquire() as c:
   for statement in DDL:await c.execute(statement)
   for _,(table,_) in TABLES.items():await c.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
   legacy=await c.fetchval("SELECT to_regclass('public.citycare_documents')")
   rows=await c.fetch("SELECT collection,id,data::text FROM citycare_documents ORDER BY CASE collection WHEN 'users' THEN 1 WHEN 'doctors' THEN 2 WHEN 'hospitals' THEN 3 WHEN 'applications' THEN 4 WHEN 'appointments' THEN 5 WHEN 'prescriptions' THEN 6 ELSE 7 END") if legacy else []
  for row in rows:
   if row["collection"] not in TABLES:continue
   doc={"_id":str(row["id"]),**json.loads(row["data"])}
   if not await self[row["collection"]].find_one({"_id":doc["_id"]}):await self[row["collection"]].insert_one(doc)
  if rows:
   async with self.pool.acquire() as c:
    if not await c.fetchval("SELECT to_regclass('public.citycare_documents_legacy_backup')"):await c.execute("ALTER TABLE citycare_documents RENAME TO citycare_documents_legacy_backup")

database=Database()
def get_database():return database
async def create_indexes():await database.initialize()
