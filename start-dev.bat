@echo off
rem TripCanvas dev launcher (starts backend + frontend)
start "TripCanvas Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe run.py"
start "TripCanvas Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo Started. Backend: http://127.0.0.1:8001/docs  Frontend: http://127.0.0.1:5173/
