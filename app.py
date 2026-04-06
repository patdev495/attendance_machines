import argparse
import os
import uvicorn
from fastapi import FastAPI, Depends, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import date
from db import get_db, AttendanceLog
from sync import sync_all_machines, get_machine_list, sync_status

app = FastAPI(title="Time Attendance System")

# CORS middleware to allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/machines")
def get_machines():
    return get_machine_list()

@app.get("/api/attendance")
def get_attendance(
    employee_id: Optional[str] = Query(None),
    machine_ip: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceLog)
    
    if employee_id:
        query = query.filter(AttendanceLog.employee_id == employee_id)
    if machine_ip:
        query = query.filter(AttendanceLog.machine_ip == machine_ip)
    if start_date:
        query = query.filter(AttendanceLog.attendance_date >= start_date)
    if end_date:
        query = query.filter(AttendanceLog.attendance_date <= end_date)
        
    total_count = query.count()
    total_pages = (total_count + size - 1) // size
    
    results = query.order_by(desc(AttendanceLog.attendance_time)) \
                   .offset((page - 1) * size) \
                   .limit(size) \
                   .all()
    
    return {
        "items": results,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "size": size
    }

@app.post("/api/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    if sync_status["is_running"]:
        return {"message": "Sync is already in progress.", "is_running": True}
    
    background_tasks.add_task(sync_all_machines)
    return {"message": "Sync started in background.", "is_running": True}

@app.get("/api/sync-status")
def get_sync_status():
    return sync_status

# Serving Static Files (Frontend)
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Time Attendance System API.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)
