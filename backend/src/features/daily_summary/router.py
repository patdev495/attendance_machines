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

from database import get_db, AttendanceLog, EmployeeLocalRegistry, EmployeeMetadata, ShiftDefinition, EmployeeDailyShifts

from .service import process_summary_rows, sync_employees_full, sync_status, status_lock
from .export_service import export_status, export_lock, run_export_task

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
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
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
    # Phase 13: Use 09:00 AM anchor for work_date calculation
    # All logs from 09:00 today to 08:59 tomorrow belong to today's shift
    # This correctly handles Workshop 1 night shifts ending at 08:00 AM
    # Phase 15: Shift-Aware Subquery
    # We join with DailyShifts for Today and Yesterday to determine the anchor correctly
    today_shift = aliased(EmployeeDailyShifts)
    yest_shift = aliased(EmployeeDailyShifts)

    # Optimization: Filter raw logs by date range early (+/- 1 day to catch overnight shifts)
    from datetime import timedelta
    log_filter = []
    if start_date: log_filter.append(AttendanceLog.attendance_date >= (start_date - timedelta(days=1)))
    if end_date: log_filter.append(AttendanceLog.attendance_date <= (end_date + timedelta(days=1)))

    base_calc_sub = db.query(
        AttendanceLog.id,
        AttendanceLog.attendance_time,
        AttendanceLog.employee_id,
        AttendanceLog.machine_ip,
        # Logic: Determine work_date by checking if this tap is a completion of yesterday's Night Shift
        # or a start of today's shift. Priority: DailyShift > Employee Default.
        case(
            # Priority 1: If Today is a Night Shift (D), taps before 12:00 (Noon) MUST belong to Yesterday
            (
                (func.coalesce(today_shift.shift_code, "").like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(12, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            # Priority 2: If Today is a Night Shift (D), taps after 18:00 MUST belong to Today
            (
                (func.coalesce(today_shift.shift_code, "").like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) >= time(18, 0)),
                func.cast(AttendanceLog.attendance_time, Date)
            ),
            # Priority 3: If Yesterday was a Night Shift (D) and it's early morning, belong to Yesterday
            (
                (func.coalesce(yest_shift.shift_code, "").like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(10, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            # Default fallback: 3-hour anchor (standard for Day shifts)
            else_=func.cast(func.dateadd(text("hour"), text("-3"), AttendanceLog.attendance_time), Date)
        ).label("work_date")
    ).filter(*log_filter).outerjoin(
        today_shift,
        (AttendanceLog.employee_id == today_shift.employee_id) & 
        (func.cast(AttendanceLog.attendance_time, Date) == today_shift.work_date)
    ).outerjoin(
        yest_shift,
        (AttendanceLog.employee_id == yest_shift.employee_id) & 
        (func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date) == yest_shift.work_date)
    ).subquery()
    
    # 1. Base Aggregated Logs Subquery (Keys + Metrics)
    agg_logs_sub = db.query(
        base_calc_sub.c.employee_id,
        base_calc_sub.c.work_date,
        func.min(base_calc_sub.c.attendance_time).label("first_tap"),
        func.max(base_calc_sub.c.attendance_time).label("last_tap"),
        func.count(base_calc_sub.c.id).label("tap_count"),
        func.max(base_calc_sub.c.machine_ip).label("machine_ip")
    ).group_by(base_calc_sub.c.employee_id, base_calc_sub.c.work_date).subquery()

    # 2. Roster Subquery (Excel schedule)
    roster_sub_query = db.query(
        EmployeeDailyShifts.employee_id,
        EmployeeDailyShifts.work_date,
        EmployeeDailyShifts.shift_code
    )
    if start_date: roster_sub_query = roster_sub_query.filter(EmployeeDailyShifts.work_date >= start_date)
    if end_date: roster_sub_query = roster_sub_query.filter(EmployeeDailyShifts.work_date <= end_date)
    roster_sub = roster_sub_query.subquery()

    # 3. Union Keys (Set of Employee + Date to report on)
    # Use explicit labels to ensure column names are consistent across UNION
    roster_keys = db.query(
        roster_sub.c.employee_id.label('employee_id'), 
        roster_sub.c.work_date.label('work_date')
    )
    log_keys = db.query(
        agg_logs_sub.c.employee_id.label('employee_id'), 
        agg_logs_sub.c.work_date.label('work_date')
    )
    # Match range for logs as well
    if start_date: log_keys = log_keys.filter(agg_logs_sub.c.work_date >= start_date)
    if end_date: log_keys = log_keys.filter(agg_logs_sub.c.work_date <= end_date)
    
    union_query = roster_keys.union(log_keys)
    union_keys = union_query.subquery('union_keys')

    # 4. Main Query: Join Union Keys with Metrics and Metadata
    query = db.query(
        union_keys.c.employee_id,
        union_keys.c.work_date,
        agg_logs_sub.c.first_tap,
        agg_logs_sub.c.last_tap,
        func.coalesce(agg_logs_sub.c.tap_count, 0).label("tap_count"),
        func.coalesce(roster_sub.c.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).label("shift"),
        func.coalesce(EmployeeLocalRegistry.emp_name, EmployeeMetadata.emp_name).label("emp_name"),
        func.coalesce(EmployeeLocalRegistry.full_emp_id, EmployeeMetadata.full_emp_id).label("full_emp_id"),
        func.coalesce(EmployeeLocalRegistry.department, EmployeeMetadata.department).label("department"),
        # Status 'excel_synced' if present in roster for this day, else 'machine_only'
        func.coalesce(EmployeeLocalRegistry.source_status, "machine_only").label("status"),
        roster_sub.c.shift_code.label("daily_shift_code")
    ).outerjoin(
        agg_logs_sub, 
        (union_keys.c.employee_id == agg_logs_sub.c.employee_id) & 
        (union_keys.c.work_date == agg_logs_sub.c.work_date)
    ).outerjoin(
        roster_sub,
        (union_keys.c.employee_id == roster_sub.c.employee_id) & 
        (union_keys.c.work_date == roster_sub.c.work_date)
    ).outerjoin(
        EmployeeLocalRegistry, 
        union_keys.c.employee_id == EmployeeLocalRegistry.employee_id
    ).outerjoin(
        EmployeeMetadata, 
        union_keys.c.employee_id == EmployeeMetadata.employee_id
    )

    # 5. Filters
    if employee_id:
        employee_id = employee_id.strip()
        id_match_q = db.query(EmployeeLocalRegistry.employee_id).filter(
            EmployeeLocalRegistry.employee_id.ilike(f"%{employee_id}%") |
            EmployeeLocalRegistry.full_emp_id.ilike(f"%{employee_id}%") |
            EmployeeLocalRegistry.emp_name.collate('Vietnamese_CI_AI').ilike(f"%{employee_id}%")
        )
        id_match_meta_q = db.query(EmployeeMetadata.employee_id).filter(
            EmployeeMetadata.employee_id.ilike(f"%{employee_id}%") |
            EmployeeMetadata.full_emp_id.ilike(f"%{employee_id}%") |
            EmployeeMetadata.emp_name.collate('Vietnamese_CI_AI').ilike(f"%{employee_id}%")
        )
        
        query = query.filter(
            (union_keys.c.employee_id.in_(id_match_q)) | 
            (union_keys.c.employee_id.in_(id_match_meta_q)) |
            (union_keys.c.employee_id.like(f"%{employee_id}%"))
        )

    if machine_ip: query = query.filter(agg_logs_sub.c.machine_ip == machine_ip)
    
    if department: 
        query = query.filter(func.coalesce(EmployeeLocalRegistry.department, EmployeeMetadata.department) == department)
    
    if status and status != 'All': 
        # Match against our dynamic status logic
        dynamic_status = func.coalesce(EmployeeLocalRegistry.source_status, "machine_only")
        query = query.filter(dynamic_status == status)

    if shift:
        valid_shift_ids = db.query(ShiftDefinition.shift_code).subquery()
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
        processed_items = process_summary_rows(all_results, rules_pool=rules_pool)
        
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
                (func.coalesce(today_shift.shift_code, "").like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(12, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            (
                (func.coalesce(today_shift.shift_code, "").like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) >= time(18, 0)),
                func.cast(AttendanceLog.attendance_time, Date)
            ),
            (
                (func.coalesce(yest_shift.shift_code, "").like("%D%")) &
                (func.cast(AttendanceLog.attendance_time, Time) < time(10, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            ),
            else_=func.cast(func.dateadd(text("hour"), text("-3"), AttendanceLog.attendance_time), Date)
        ).label("work_date")
    ).outerjoin(today_shift, (AttendanceLog.employee_id == today_shift.employee_id) & (func.cast(AttendanceLog.attendance_time, Date) == today_shift.work_date)) \
     .outerjoin(yest_shift, (AttendanceLog.employee_id == yest_shift.employee_id) & (func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date) == yest_shift.work_date)) \
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
