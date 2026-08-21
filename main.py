import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load local configuration before any module reads database or token settings.
# Production environments can provide the same variables directly.
load_dotenv()

from core.database.database import create_indexes
from core.apis.routes import router

local_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
configured_origins = [origin.strip().rstrip("/") for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
allowed_origins = list(dict.fromkeys(local_origins + configured_origins))

@asynccontextmanager
async def lifespan(app):
    await create_indexes(); yield
app=FastAPI(title="CityCare API",version="1.0.0",lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"(?i)^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|shreya|.*\.onrender\.com)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.exception_handler(Exception)
async def armour(request:Request,exc:Exception):
    logging.exception("Unhandled request failure")
    return JSONResponse(status_code=500,content={"detail":"Something went wrong. Please try again."})
@app.get("/health")
async def health(): return {"status":"ok"}
app.include_router(router)
