import os
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from datetime import date, datetime
from services.export_service import export_status, export_lock, run_export_task

router = APIRouter(prefix="/api/export-attendance", tags=["Export"])

@router.post("/start")
def start_export(
    background_tasks: BackgroundTasks,
    start_date: date = Query(...),
    end_date: date = Query(...),
    view_mode: str = Query(..., description="'time', 'hours', or 'both'")
):
    with export_lock:
        if export_status["is_running"]:
            return {"message": "An export is already running", "status": export_status}
    
    background_tasks.add_task(run_export_task, start_date, end_date, view_mode)
    return {"message": "Export started"}

@router.get("/status")
def get_export_status():
    with export_lock:
        return export_status

@router.post("/cancel")
def cancel_export():
    with export_lock:
        export_status["cancel_requested"] = True
    return {"message": "Cancellation requested"}

@router.get("/download")
def download_export():
    with export_lock:
        if not export_status["filename"] or not os.path.exists(export_status["filename"]):
            raise HTTPException(status_code=404, detail="File not ready or expired")
        
        filepath = export_status["filename"]
        # Reset status for next use
        export_status["filename"] = None 
        
    return FileResponse(
        filepath, 
        filename=f"Attendance_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        background=BackgroundTask(lambda: os.remove(filepath))
    )
