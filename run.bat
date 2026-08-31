@echo off
echo ===================================================
echo Starting VeriSight Phase 1 System
echo ===================================================

echo [1/3] Activating Virtual Environment...
if exist ".venv\Scripts\python.exe" (
    echo Virtual environment found.
) else (
    echo Error: Virtual environment not found in .venv\
    pause
    exit /b 1
)

echo.
echo [2/3] Checking and initializing database tables...
".venv\Scripts\python.exe" backend\scripts\setup_db.py
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Database setup encountered an error. 
    echo Please check your Supabase credentials in the .env file.
    echo The server will still attempt to start, but validation may fail.
    echo.
) else (
    echo Database verified successfully.
)

echo.
echo [3/3] Starting the FastAPI Backend Server...
cd backend
"..\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload

pause
