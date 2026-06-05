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
    query = db.query(AttendanceLog)

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

        query = query.filter(
            (AttendanceLog.employee_id.in_(list(found_ids))) |
            (AttendanceLog.employee_id.ilike(f"%{employee_id}%"))
        )
    if machine_ip:
        query = query.filter(AttendanceLog.machine_ip == machine_ip)

    if start_date:
        query = query.filter(AttendanceLog.attendance_date >= start_date)
    if end_date:
        query = query.filter(AttendanceLog.attendance_date <= end_date)

    total = query.count()
    logs = query.order_by(desc(AttendanceLog.attendance_time)) \
                .offset((page - 1) * size) \
                .limit(size) \
                .all()
    employee_ids = {str(log.employee_id).strip() for log in logs if log.employee_id}
    registry_map = {}
    metadata_map = {}

    if employee_ids:
        registry_rows = db.query(
            EmployeeLocalRegistry.employee_id,
            EmployeeLocalRegistry.emp_name,
        ).filter(EmployeeLocalRegistry.employee_id.in_(list(employee_ids))).all()
        registry_map = {str(r.employee_id).strip(): r.emp_name for r in registry_rows}

        missing_ids = employee_ids - set(registry_map.keys())
        if missing_ids:
            metadata_rows = db.query(
                EmployeeMetadata.employee_id,
                EmployeeMetadata.emp_name,
            ).filter(EmployeeMetadata.employee_id.in_(list(missing_ids))).all()
            metadata_map = {str(r.employee_id).strip(): r.emp_name for r in metadata_rows}

    items = []
    for log in logs:
        emp_id = str(log.employee_id).strip()
        items.append({
            "id": log.id,
            "employee_id": log.employee_id,
            "attendance_time": log.attendance_time,
            "machine_ip": log.machine_ip,
            "emp_name": registry_map.get(emp_id) or metadata_map.get(emp_id),
        })

    return {
        "items": items,
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
def start_sync(
    background_tasks: BackgroundTasks,
    start_date: Optional[date_type] = Query(None),
    end_date: Optional[date_type] = Query(None),
):
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
    background_tasks.add_task(sync_all_machines, start_date, end_date)
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
