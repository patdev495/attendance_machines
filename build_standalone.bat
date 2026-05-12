@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   TIME ATTENDANCE SYSTEM - STANDALONE BUILD SCRIPT
echo ============================================================
echo.

:: Step 1: Build Frontend
echo [1/4] Building Frontend...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)
echo Running frontend build...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERROR: Frontend build failed!
    pause
    exit /b %ERRORLEVEL%
)
cd ..

:: Step 2: Verify Static Files
echo [2/4] Verifying Static Assets...
if not exist backend\static\index.html (
    echo ERROR: Frontend build did not produce backend\static\index.html!
    pause
    exit /b 1
)
echo Frontend assets verified in backend\static\

:: Step 3: Build Backend EXE
echo [3/4] Building Standalone EXE using PyInstaller...
uv run pyinstaller TimeAttendance.spec --clean -y
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed!
    pause
    exit /b %ERRORLEVEL%
)

:: Step 4: Finalize Distribution Folder
echo [4/4] Finalizing Distribution...
set DIST_PATH=dist\TimeAttendance

echo Copying configuration and data files...
if not exist %DIST_PATH%\machines.txt copy machines.txt %DIST_PATH%\
if not exist %DIST_PATH%\employee_work_shift.xlsx copy employee_work_shift.xlsx %DIST_PATH%\
if not exist %DIST_PATH%\backend mkdir %DIST_PATH%\backend
if not exist %DIST_PATH%\backend\.env copy backend\.env %DIST_PATH%\backend\.env

echo Ensuring required data files exist...
if not exist %DIST_PATH%\audio mkdir %DIST_PATH%\audio

echo.
echo ============================================================
echo   BUILD COMPLETE!
echo   Location: %DIST_PATH%
echo   Run %DIST_PATH%\TimeAttendance.exe to start.
echo ============================================================
echo.
pause
