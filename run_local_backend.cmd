@echo off
set "JWT_SECRET=citycare-local-development-secret-2026-change-before-production"
cd /d "%~dp0"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "PYTHONPATH=%~dp0.runtime\python;%~dp0"
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 set "PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Python is unavailable. Install Python 3.12 and recreate .venv first.
  exit /b 1
)
call "%PYTHON_EXE%" -m uvicorn main:app --host 127.0.0.1 --port 8010
