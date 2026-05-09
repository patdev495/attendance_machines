@echo off
echo ===================================================
echo   TIME ATTENDANCE MACHINE - DEV ENVIRONMENT
echo ===================================================

:: Start Backend in a new window
echo [1/2] Starting FastAPI Backend...
start "Backend" cmd /k "uv run -m uvicorn main:app --reload --app-dir backend/src --port 8000"

:: Start Frontend in a new window
echo [2/2] Starting Vue Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both services are starting up!
echo - Backend will run on: http://localhost:8000
echo - Frontend will run on its default Vite port (usually http://localhost:5173)
echo.
echo Press any key to close this launcher window (the services will keep running in their own windows).
pause > nul
