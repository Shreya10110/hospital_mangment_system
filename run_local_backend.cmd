@echo off
set "MONGO_URL=mongodb://127.0.0.1:27017"
set "JWT_SECRET=citycare-local-development-secret-2026-change-before-production"
cd /d "%~dp0"
call ".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8010
