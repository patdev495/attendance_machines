from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import date as date_type

from database import get_db, AttendanceLog
from .service import sync_all_machines, sync_status, status_lock

router = APIRouter(prefix="/api/logs", tags=["Logs"])

@router.get("")
def get_logs(
    employee_id: Optional[str] = Query(None),
    machine_ip: Optional[str] = Query(None),
    start_date: Optional[date_type] = Query(None),
    end_date: Optional[date_type] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceLog)
    
    if employee_id:
        query = query.filter(AttendanceLog.employee_id == employee_id)
    if machine_ip:
        query = query.filter(AttendanceLog.machine_ip == machine_ip)
    
    from sqlalchemy import Date
    if start_date:
        query = query.filter(func.cast(AttendanceLog.attendance_time, Date) >= start_date)
    if end_date:
        query = query.filter(func.cast(AttendanceLog.attendance_time, Date) <= end_date)
        
    total = query.count()
    results = query.order_by(desc(AttendanceLog.attendance_time)) \
                   .offset((page - 1) * size) \
                   .limit(size) \
                   .all()
                   
    return {
        "items": results,
        "total_count": total,
        "total_pages": (total + size - 1) // size
    }

@router.get("/date-range")
def get_date_range(db: Session = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    result = db.query(
        sqlfunc.min(AttendanceLog.attendance_time).label("min_dt"),
        sqlfunc.max(AttendanceLog.attendance_time).label("max_dt")
    ).first()
    return {
        "min_date": result.min_dt.date() if result.min_dt else None,
        "max_date": result.max_dt.date() if result.max_dt else None
    }

@router.post("/sync")
def start_sync(background_tasks: BackgroundTasks):
    from shared.hardware import get_machine_list
    # Set running state BEFORE background task starts to avoid race condition
    # where the first poll sees is_running=False and thinks sync is complete
    with status_lock:
        if sync_status["is_running"]:
            return {"message": "Sync already running"}
        machine_ips = get_machine_list()
        sync_status["is_running"] = True
        sync_status["total_machines"] = len(machine_ips)
        sync_status["current_machine_index"] = 0
        sync_status["current_machine_ip"] = ""
        sync_status["total_added"] = 0
        sync_status["fail_count"] = 0
    background_tasks.add_task(sync_all_machines)
    return {"message": "Sync started"}

@router.get("/sync/status")
def get_sync_status():
    return sync_status
