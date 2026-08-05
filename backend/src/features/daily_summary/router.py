import os
import io
import logging
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from starlette.background import BackgroundTask
from typing import Optional
from datetime import date, datetime

from database import get_db, AttendanceLog, EmployeeLocalRegistry, EmployeeMetadata, ShiftDefinition
from features.employees.registry_service import find_employee_ids_for_search, normalize_employee_id, employee_search_filter
from utils.date_utils import parse_date_robust

from .service import process_summary_rows, sync_employees_full, sync_status, status_lock
from .export_service import export_status, export_lock, run_export_task
from .report_query import (
    build_daily_summary_query,
    build_log_work_date_subquery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-summary", tags=["Daily Summary"])

@router.get("/unique-shifts")
def get_unique_shifts(db: Session = Depends(get_db)):
    # Only pull from the official definitions table
    q = db.query(ShiftDefinition.shift_code).distinct()

    results = [r[0] for r in q.all()]
    unique_shifts = sorted(list(set(s.strip().upper() for s in results if s and s.strip())))

    # Always include NA at the beginning
    return ["NA"] + unique_shifts



@router.get("")
def get_daily_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    machine_ip: Optional[str] = Query(None),
    shift: Optional[str] = Query(None),
    min_hours: Optional[float] = Query(None),
    max_hours: Optional[float] = Query(None),
    only_missing: Optional[bool] = Query(False),
    late_arrival: Optional[bool] = Query(False),
    early_departure: Optional[bool] = Query(False),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    try:
        parsed_start = parse_date_robust(start_date)
        parsed_end = parse_date_robust(end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    parts = build_daily_summary_query(db, parsed_start, parsed_end)
    query = parts.query
    union_keys = parts.union_keys
    agg_logs_sub = parts.agg_logs_sub
    roster_sub = parts.roster_sub

    # 5. Filters
    if employee_id:
        query = query.filter(employee_search_filter(db, employee_id, union_keys.c.employee_id))

    if machine_ip: query = query.filter(agg_logs_sub.c.machine_ip == machine_ip)

    if department:
        query = query.filter(func.coalesce(EmployeeLocalRegistry.department, EmployeeMetadata.department) == department)

    if status and status != 'All':
        # Match against our dynamic status logic
        dynamic_status = func.coalesce(EmployeeLocalRegistry.source_status, "machine_only")
        query = query.filter(dynamic_status == status)

    if shift:
        valid_shift_ids = db.query(ShiftDefinition.shift_code)
        effective_shift = func.coalesce(roster_sub.c.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift)
        mapped_shift = case(
            (effective_shift.in_(valid_shift_ids), effective_shift),
            else_="NA"
        )
        query = query.filter(mapped_shift == shift)

    query = query.order_by(desc(union_keys.c.work_date), union_keys.c.employee_id)

    rules_pool = db.query(ShiftDefinition).all()


    if min_hours or max_hours or only_missing or late_arrival or early_departure:
        # Complex calculation filters require fetching results to compute metrics
        # But we still only fetch what is needed. For now, fetch ALL then filter.
        # POTENTIAL FUTURE OPTIMIZATION: Push metrics into SQL.
        all_results = query.all()
        processed_items = process_summary_rows(all_results, rules_pool=rules_pool, db=db)

        filtered_items = []
        for item in processed_items:
            if only_missing and not (item['tap_count'] < 2 or item['note']): continue
            wh = item['work_hours'] or 0.0
            if min_hours and wh < min_hours: continue
            if max_hours and wh > max_hours: continue
            if late_arrival and not (item.get('minutes_late') and item.get('minutes_late') > 0): continue
            if early_departure and not (item.get('minutes_early_leave') and item.get('minutes_early_leave') > 0): continue
            filtered_items.append(item)

        total = len(filtered_items)
        start_idx = (page - 1) * size
        summary_items = filtered_items[start_idx:start_idx + size]
    else:
        # Standard case: Use database-level pagination
        total = query.count()
        results = query.offset((page - 1) * size).limit(size).all()
        summary_items = process_summary_rows(results, rules_pool=rules_pool, db=db)


    return {
        "items": summary_items,
        "total_count": total,
        "total_pages": (total + size - 1) // size,
        "page": page,
        "size": size
    }

@router.get("/detail")
def get_daily_detail(
    employee_id: str = Query(...),
    work_date: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        parsed_work_date = parse_date_robust(work_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    base_calc_sub = build_log_work_date_subquery(
        db,
        start_date=parsed_work_date,
        end_date=parsed_work_date,
        date_padding_days=1,
    )

    logs = db.query(AttendanceLog) \
             .join(base_calc_sub, AttendanceLog.id == base_calc_sub.c.id) \
             .filter(employee_search_filter(db, employee_id, base_calc_sub.c.employee_id)) \
             .filter(base_calc_sub.c.work_date == parsed_work_date) \
             .order_by(AttendanceLog.attendance_time) \
             .all()
    return logs

@router.post("/export")
def start_export(
    background_tasks: BackgroundTasks,
    start_date: str = Query(...),
    end_date: str = Query(...),
    view_mode: str = Query(..., description="'time', 'hours', or 'both'")
):
    try:
        parsed_start = parse_date_robust(start_date)
        parsed_end = parse_date_robust(end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if parsed_start is None or parsed_end is None:
        raise HTTPException(status_code=400, detail="Start date and end date are required.")

    with export_lock:
        if export_status["is_running"]:
            return {"message": "Export already running", "status": export_status}
    background_tasks.add_task(run_export_task, parsed_start, parsed_end, view_mode)
    return {"message": "Export started"}

@router.get("/export/status")
def get_export_status():
    with export_lock:
        return export_status

@router.get("/export/download")
def download_export():
    with export_lock:
        if not export_status["filename"] or not os.path.exists(export_status["filename"]):
            raise HTTPException(status_code=404, detail="File not ready")
        filepath = export_status["filename"]
        export_status["filename"] = None

    download_name = f"Attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {
        "Content-Disposition": f'inline; filename="{download_name}"',
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
        background=BackgroundTask(lambda: os.remove(filepath))
    )

@router.post("/export/cancel")
def cancel_export():
    with export_lock:
        if export_status["is_running"]:
            export_status["cancel_requested"] = True
            return {"message": "Cancel requested"}
        return {"message": "Export not running"}

@router.post("/sync-excel")
async def sync_excel(background_tasks: BackgroundTasks, file: Optional[UploadFile] = File(None)):
    content = None
    if file:
        file_content = await file.read()
        content = io.BytesIO(file_content)
    background_tasks.add_task(sync_employees_full, content)
    return {"status": "Started"}

@router.get("/sync-excel/status")
def get_sync_excel_status():
    with status_lock:
        return sync_status
