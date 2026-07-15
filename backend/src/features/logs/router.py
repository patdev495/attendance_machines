from fastapi import APIRouter, Depends, Query, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
import logging
from sqlalchemy.orm import Session
from shared.socket_manager import manager
from sqlalchemy import func, desc
from typing import Optional
from datetime import date as date_type

from database import get_db, AttendanceLog
from .service import sync_all_machines, sync_status, status_lock
from features.employees.registry_service import employee_name_map, find_employee_ids_for_search, normalize_employee_id, employee_search_filter
from utils.date_utils import parse_date_robust

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["Logs"])

@router.get("")
def get_logs(
    employee_id: Optional[str] = Query(None),
    machine_ip: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    try:
        parsed_start = parse_date_robust(start_date)
        parsed_end = parse_date_robust(end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    query = db.query(AttendanceLog)

    if employee_id:
        query = query.filter(employee_search_filter(db, employee_id, AttendanceLog.employee_id))
    if machine_ip:
        query = query.filter(AttendanceLog.machine_ip == machine_ip)

    if parsed_start:
        query = query.filter(AttendanceLog.attendance_date >= parsed_start)
    if parsed_end:
        query = query.filter(AttendanceLog.attendance_date <= parsed_end)

    total = query.count()
    logs = query.order_by(desc(AttendanceLog.attendance_time)) \
                .offset((page - 1) * size) \
                .limit(size) \
                .all()
    names = employee_name_map(db, (normalize_employee_id(log.employee_id) for log in logs))

    items = []
    for log in logs:
        emp_id = normalize_employee_id(log.employee_id)
        items.append({
            "id": log.id,
            "employee_id": log.employee_id,
            "attendance_time": log.attendance_time,
            "machine_ip": log.machine_ip,
            "emp_name": names.get(emp_id),
        })

    return {
        "items": items,
        "total_count": total,
        "total_pages": (total + size - 1) // size
    }

@router.get("/date-range")
def get_date_range(db: Session = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    from datetime import datetime as datetime_class, date as date_class
    result = db.query(
        sqlfunc.min(AttendanceLog.attendance_time).label("min_dt"),
        sqlfunc.max(AttendanceLog.attendance_time).label("max_dt")
    ).first()
    if not result:
        return {"min_date": None, "max_date": None}

    def safe_date(val):
        if not val:
            return None
        if isinstance(val, datetime_class):
            return val.date()
        if isinstance(val, date_class):
            return val
        if isinstance(val, str):
            try:
                return parse_date_robust(val)
            except Exception:
                return val[:10]
        if hasattr(val, "date") and callable(val.date):
            return val.date()
        return None

    return {
        "min_date": safe_date(result.min_dt),
        "max_date": safe_date(result.max_dt)
    }

@router.post("/sync")
def start_sync(
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    try:
        parsed_start = parse_date_robust(start_date)
        parsed_end = parse_date_robust(end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from shared.hardware import get_all_machine_configs
    # Set running state BEFORE background task starts to avoid race condition
    # where the first poll sees is_running=False and thinks sync is complete
    with status_lock:
        if sync_status["is_running"]:
            return {"message": "Sync already running"}
        machine_configs = get_all_machine_configs()
        sync_status["is_running"] = True
        sync_status["total_machines"] = len(machine_configs)
        sync_status["current_machine_index"] = 0
        sync_status["current_machine_ip"] = ""
        sync_status["total_added"] = 0
        sync_status["fail_count"] = 0
    background_tasks.add_task(sync_all_machines, parsed_start, parsed_end)
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
