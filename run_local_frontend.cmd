@echo off
set "VITE_API_URL=http://127.0.0.1:8010"
cd /d "%~dp0frontend"
call npm.cmd run dev -- --host 0.0.0.0 --port 5173
