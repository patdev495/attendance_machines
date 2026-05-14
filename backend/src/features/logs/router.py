from fastapi import APIRouter, Depends, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
import logging
from sqlalchemy.orm import Session
from shared.socket_manager import manager
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import date as date_type

from database import get_db, AttendanceLog
from .service import sync_all_machines, sync_status, status_lock
from compat import safe_ilike

logger = logging.getLogger(__name__)

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
    from database import EmployeeLocalRegistry, EmployeeMetadata
    query = db.query(
        AttendanceLog.id,
        AttendanceLog.employee_id,
        AttendanceLog.attendance_time,
        AttendanceLog.machine_ip,
        func.coalesce(EmployeeLocalRegistry.emp_name, EmployeeMetadata.emp_name).label("emp_name")
    ).outerjoin(EmployeeLocalRegistry, func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(EmployeeLocalRegistry.employee_id))) \
     .outerjoin(EmployeeMetadata, func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(EmployeeMetadata.employee_id)))
    
    if employee_id:
        employee_id = employee_id.strip()
        # Step 1: Find matching IDs from registry/metadata (fast, small tables)
        match_ids = db.query(EmployeeLocalRegistry.employee_id).filter(
            EmployeeLocalRegistry.employee_id.ilike(f"%{employee_id}%") |
            safe_ilike(EmployeeLocalRegistry.emp_name, f"%{employee_id}%")
        ).all()
        match_ids_meta = db.query(EmployeeMetadata.employee_id).filter(
            EmployeeMetadata.employee_id.ilike(f"%{employee_id}%") |
            safe_ilike(EmployeeMetadata.emp_name, f"%{employee_id}%")
        ).all()
        
        found_ids = {r[0] for r in match_ids} | {r[0] for r in match_ids_meta} | {employee_id}
        
        # Step 2: Filter large AttendanceLog table using indexed IN clause (very fast)
        # Use ltrim/rtrim to be robust against machine-generated ID spaces
        query = query.filter(func.ltrim(func.rtrim(AttendanceLog.employee_id)).in_(list(found_ids)))
    if machine_ip:
        query = query.filter(AttendanceLog.machine_ip == machine_ip)
    
    if start_date:
        query = query.filter(AttendanceLog.attendance_date >= start_date)
    if end_date:
        query = query.filter(AttendanceLog.attendance_date <= end_date)
        
    total = query.count()
    results = query.order_by(desc(AttendanceLog.attendance_time)) \
                   .offset((page - 1) * size) \
                   .limit(size) \
                   .all()
                   
    return {
        "items": [r._asdict() for r in results],
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

@router.websocket("/live/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("Incoming WebSocket connection request...")
    await manager.connect(websocket)
    try:
        logger.info("WebSocket connected and stored.")
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            logger.debug(f"Received WS data: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected gracefully.")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
