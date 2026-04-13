import os
import io
import logging
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, desc, case, literal_column, text, Time, Date
from starlette.background import BackgroundTask
from typing import List, Optional
from datetime import date, datetime, time, timedelta

from database import get_db, AttendanceLog, EmployeeLocalRegistry, EmployeeMetadata, ShiftRule, EmployeeDailyShifts
from .service import process_summary_rows, sync_employees_full, sync_status, status_lock
from .export_service import export_status, export_lock, run_export_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-summary", tags=["Daily Summary"])

@router.get("/unique-shifts")
def get_unique_shifts(db: Session = Depends(get_db)):
    """
    Returns a list of all unique shift codes found in:
    - EmployeeDailyShifts
    - EmployeeLocalRegistry
    - EmployeeMetadata
    """
    from sqlalchemy import union_all

    # Use union to get unique values across 3 tables
    q1 = db.query(EmployeeDailyShifts.shift_code).distinct()
    q2 = db.query(EmployeeLocalRegistry.shift).distinct().filter(EmployeeLocalRegistry.shift != None)
    q3 = db.query(EmployeeMetadata.shift).distinct().filter(EmployeeMetadata.shift != None)
    
    # Use list comprehension and set for uniqueness
    results = [r[0] for r in q1.all()] + [r[0] for r in q2.all()] + [r[0] for r in q3.all()]
    unique_shifts = sorted(list(set(s.strip().upper() for s in results if s and s.strip())))
    
    return unique_shifts

@router.get("")
def get_daily_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    employee_id: Optional[str] = Query(None),
    machine_ip: Optional[str] = Query(None),
    shift: Optional[str] = Query(None),
    min_hours: Optional[float] = Query(None),
    max_hours: Optional[float] = Query(None),
    only_missing: Optional[bool] = Query(False),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Phase 13: Use 09:00 AM anchor for work_date calculation
    # All logs from 09:00 today to 08:59 tomorrow belong to today's shift
    # This correctly handles Workshop 1 night shifts ending at 08:00 AM
    # Phase 15: Shift-Aware Subquery
    # We join with DailyShifts for Today and Yesterday to determine the anchor correctly
    today_shift = aliased(EmployeeDailyShifts)
    yest_shift = aliased(EmployeeDailyShifts)

    base_calc_sub = db.query(
        AttendanceLog.id,
        AttendanceLog.attendance_time,
        AttendanceLog.employee_id,
        AttendanceLog.machine_ip,
        EmployeeLocalRegistry.emp_name.label("reg_name"),
        func.nullif(EmployeeLocalRegistry.shift, "").label("reg_shift"),
        EmployeeLocalRegistry.department,
        EmployeeLocalRegistry.source_status,
        EmployeeLocalRegistry.full_emp_id,
        EmployeeMetadata.emp_name.label("meta_name"),
        func.nullif(EmployeeMetadata.shift, "").label("meta_shift"),
        EmployeeMetadata.department.label("meta_dept"),
        EmployeeMetadata.status.label("meta_status"),
        # Logic: Determine work_date by checking if this tap is a completion of yesterday's Night Shift
        # or a start of today's shift.
        case(
            # Priority 1: If Today is a Night Shift (D), taps before 12:00 (Noon) MUST belong to Yesterday
            (
                (func.coalesce(today_shift.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(12, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            # Priority 2: If Today is a Night Shift (D), taps after 18:00 MUST belong to Today
            (
                (func.coalesce(today_shift.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) >= time(18, 0)),
                func.cast(AttendanceLog.attendance_time, Date)
            ),
            # Priority 3: If Yesterday was a Night Shift (D) and it's early morning, belong to Yesterday
            (
                (func.coalesce(yest_shift.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(10, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            # Default fallback: 3-hour anchor (standard for Day shifts)
            else_=func.cast(func.dateadd(text("hour"), text("-3"), AttendanceLog.attendance_time), Date)
        ).label("work_date")
    ).outerjoin(
        EmployeeLocalRegistry, 
        func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(EmployeeLocalRegistry.employee_id))
    ).outerjoin(
        EmployeeMetadata, 
        func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(EmployeeMetadata.employee_id))
    ).outerjoin(
        today_shift,
        (func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(today_shift.employee_id))) &
        (func.cast(AttendanceLog.attendance_time, Date) == today_shift.work_date)
    ).outerjoin(
        yest_shift,
        (func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(yest_shift.employee_id))) &
        (func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date) == yest_shift.work_date)
    ).subquery()
    
    # Phase 13: Join with EmployeeDailyShifts to get the daily shift code
    query = db.query(
        base_calc_sub.c.employee_id,
        base_calc_sub.c.full_emp_id, # Display full ID
        func.coalesce(base_calc_sub.c.reg_name, base_calc_sub.c.meta_name).label("emp_name"),
        base_calc_sub.c.work_date,
        func.min(base_calc_sub.c.attendance_time).label("first_tap"),
        func.max(base_calc_sub.c.attendance_time).label("last_tap"),
        func.count(base_calc_sub.c.id).label("tap_count"),
        # Use daily shift code first, then fallback to employee-level shift
        func.coalesce(
            func.max(EmployeeDailyShifts.shift_code),
            func.coalesce(base_calc_sub.c.reg_shift, base_calc_sub.c.meta_shift)
        ).label("shift"),
        func.coalesce(base_calc_sub.c.department, base_calc_sub.c.meta_dept).label("department"),
        func.coalesce(base_calc_sub.c.source_status, base_calc_sub.c.meta_status).label("status"),
        func.max(EmployeeDailyShifts.shift_code).label("daily_shift_code")
    ).outerjoin(
        EmployeeDailyShifts,
        (func.ltrim(func.rtrim(base_calc_sub.c.employee_id)) == func.ltrim(func.rtrim(EmployeeDailyShifts.employee_id))) &
        (base_calc_sub.c.work_date == EmployeeDailyShifts.work_date)
    )
    
    if start_date: query = query.filter(base_calc_sub.c.work_date >= start_date)
    if end_date: query = query.filter(base_calc_sub.c.work_date <= end_date)
    if employee_id:
        employee_id = employee_id.strip()
        match_ids = db.query(EmployeeLocalRegistry.employee_id).filter(
            EmployeeLocalRegistry.employee_id.ilike(f"%{employee_id}%") |
            EmployeeLocalRegistry.full_emp_id.ilike(f"%{employee_id}%") |
            EmployeeLocalRegistry.emp_name.collate('Vietnamese_CI_AI').ilike(f"%{employee_id}%")
        ).all()
        match_ids_meta = db.query(EmployeeMetadata.employee_id).filter(
            EmployeeMetadata.employee_id.ilike(f"%{employee_id}%") |
            EmployeeMetadata.full_emp_id.ilike(f"%{employee_id}%") |
            EmployeeMetadata.emp_name.collate('Vietnamese_CI_AI').ilike(f"%{employee_id}%")
        ).all()
        
        found_ids = {r[0] for r in match_ids} | {r[0] for r in match_ids_meta} | {employee_id}
        query = query.filter(func.ltrim(func.rtrim(base_calc_sub.c.employee_id)).in_(list(found_ids)))
    if machine_ip: query = query.filter(base_calc_sub.c.machine_ip == machine_ip)
    # Filter by shift: use daily code if available
    final_shift = func.coalesce(
        func.max(EmployeeDailyShifts.shift_code),
        func.coalesce(base_calc_sub.c.reg_shift, base_calc_sub.c.meta_shift)
    )
    if shift == "NA":
        query = query.having(final_shift == None)
    elif shift:
        query = query.having(final_shift == shift)
    if department: query = query.filter(base_calc_sub.c.department == department)
    final_status = func.coalesce(base_calc_sub.c.source_status, base_calc_sub.c.meta_status)
    if status and status != 'All': 
        query = query.filter(final_status == status)

    query = query.group_by(
        base_calc_sub.c.employee_id, 
        base_calc_sub.c.reg_name,
        base_calc_sub.c.meta_name,
        base_calc_sub.c.work_date, 
        base_calc_sub.c.reg_shift, 
        base_calc_sub.c.meta_shift,
        base_calc_sub.c.department, 
        base_calc_sub.c.meta_dept,
        base_calc_sub.c.source_status,
        base_calc_sub.c.meta_status,
        base_calc_sub.c.full_emp_id
    ).order_by(desc(base_calc_sub.c.work_date), base_calc_sub.c.employee_id)

    rules_pool = db.query(ShiftRule).all()

    if min_hours or max_hours or only_missing:
        all_results = query.all()
        processed_items = process_summary_rows(all_results, rules_pool=rules_pool)
        
        filtered_items = []
        for item in processed_items:
            if only_missing and not (item['tap_count'] < 2 or item['note']): continue
            wh = item['work_hours'] or 0.0
            if min_hours and wh < min_hours: continue
            if max_hours and wh > max_hours: continue
            filtered_items.append(item)
            
        total = len(filtered_items)
        start_idx = (page - 1) * size
        summary_items = filtered_items[start_idx:start_idx + size]
    else:
        # Use query.all() then slice to be 100% safe on MSSQL complex group by
        all_results = query.all()
        total = len(all_results)
        results = all_results[(page - 1) * size : page * size]
        summary_items = process_summary_rows(results, rules_pool=rules_pool)
         
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
    work_date: date = Query(...),
    db: Session = Depends(get_db)
):
    today_shift = aliased(EmployeeDailyShifts)
    yest_shift = aliased(EmployeeDailyShifts)

    base_calc_sub = db.query(
        AttendanceLog.id,
        AttendanceLog.attendance_time,
        AttendanceLog.employee_id,
        case(
            (
                (func.coalesce(today_shift.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(12, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            (
                (func.coalesce(today_shift.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) >= time(18, 0)),
                func.cast(AttendanceLog.attendance_time, Date)
            ),
            (
                (func.coalesce(yest_shift.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(10, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            else_=func.cast(func.dateadd(text("hour"), text("-3"), AttendanceLog.attendance_time), Date)
        ).label("work_date")
    ).outerjoin(EmployeeLocalRegistry, func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(EmployeeLocalRegistry.employee_id))) \
     .outerjoin(EmployeeMetadata, func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(EmployeeMetadata.employee_id))) \
     .outerjoin(today_shift, (func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(today_shift.employee_id))) & (func.cast(AttendanceLog.attendance_time, Date) == today_shift.work_date)) \
     .outerjoin(yest_shift, (func.ltrim(func.rtrim(AttendanceLog.employee_id)) == func.ltrim(func.rtrim(yest_shift.employee_id))) & (func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date) == yest_shift.work_date)) \
     .subquery()

    logs = db.query(AttendanceLog) \
             .join(base_calc_sub, AttendanceLog.id == base_calc_sub.c.id) \
             .filter(func.ltrim(func.rtrim(base_calc_sub.c.employee_id)) == employee_id.strip()) \
             .filter(base_calc_sub.c.work_date == work_date) \
             .order_by(AttendanceLog.attendance_time) \
             .all()
    return logs

@router.post("/export")
def start_export(
    background_tasks: BackgroundTasks,
    start_date: date = Query(...),
    end_date: date = Query(...),
    view_mode: str = Query(..., description="'time', 'hours', or 'both'")
):
    with export_lock:
        if export_status["is_running"]:
            return {"message": "Export already running", "status": export_status}
    background_tasks.add_task(run_export_task, start_date, end_date, view_mode)
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
async def sync_excel(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    content = await file.read()
    background_tasks.add_task(sync_employees_full, io.BytesIO(content))
    return {"status": "Started"}

@router.get("/sync-excel/status")
def get_sync_excel_status():
    with status_lock:
        return sync_status
