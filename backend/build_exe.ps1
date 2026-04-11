# Packaging script for Time Attendance System
# Run this from the project root

$projectName = "TimeAttendance"
$mainScript = "backend/src/main.py"
$distFolder = "dist"
$buildFolder = "build"

# Hidden imports for WebSockets and Uvicorn
$hiddenImports = @(
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "websockets.legacy.client"
)

# Construct hidden import arguments
$hiddenImportArgs = $hiddenImports | ForEach-Object { "--hidden-import=$_" }

Write-Host "Cleaning old builds..." -ForegroundColor Cyan
if (Test-Path $distFolder) { Remove-Item -Recurse -Force $distFolder }
if (Test-Path $buildFolder) { Remove-Item -Recurse -Force $buildFolder }

Write-Host "Starting PyInstaller packaging..." -ForegroundColor Green

# Running PyInstaller
# --onedir: creates a folder (more stable than --onefile for complex apps)
# --add-data: bundles the static frontend files
# --paths: includes the src directory in python path
uv run pyinstaller --onedir `
    --name $projectName `
    --paths "backend/src" `
    --add-data "backend/static;backend/static" `
    $hiddenImportArgs `
    $mainScript

Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "Output located in: $distFolder\$projectName" -ForegroundColor Cyan
Write-Host "Don't forget to copy machines.txt and employee_work_shift.xlsx to the output folder!" -ForegroundColor Yellow
