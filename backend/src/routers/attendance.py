from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional
from datetime import date

from ..database import get_db, AttendanceLog, EmployeeMetadata
from ..services.attendance_service import AttendanceService

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

@router.get("")
def get_attendance(
    employee_id: Optional[str] = Query(None),
    machine_ip: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
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
        "min": result.min_dt.date() if result.min_dt else None,
        "max": result.max_dt.date() if result.max_dt else None
    }

@router.get("/summary")
def get_attendance_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    employee_id: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query("Active"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    from sqlalchemy import Date, case, text
    
    # ─── AGGREGATED QUERY ──────────────────────────────────────────
    base_calc_sub = db.query(
        AttendanceLog.id,
        AttendanceLog.attendance_time,
        AttendanceLog.employee_id,
        EmployeeMetadata.shift,
        EmployeeMetadata.department,
        EmployeeMetadata.status,
        case(
            (EmployeeMetadata.shift == text("'D'"), func.cast(func.dateadd(text("hour"), text("-10"), AttendanceLog.attendance_time), Date)),
            else_=func.cast(func.dateadd(text("hour"), text("-4"), AttendanceLog.attendance_time), Date)
        ).label("work_date")
    ).outerjoin(EmployeeMetadata, AttendanceLog.employee_id == EmployeeMetadata.employee_id).subquery()
    
    query = db.query(
        base_calc_sub.c.employee_id,
        base_calc_sub.c.work_date,
        func.min(base_calc_sub.c.attendance_time).label("first_tap"),
        func.max(base_calc_sub.c.attendance_time).label("last_tap"),
        func.count(base_calc_sub.c.id).label("tap_count"),
        base_calc_sub.c.shift,
        base_calc_sub.c.department,
        base_calc_sub.c.status
    )
    
    query = query.filter(base_calc_sub.c.work_date >= start_date)
    query = query.filter(base_calc_sub.c.work_date <= end_date)
    
    if employee_id:
        query = query.filter(base_calc_sub.c.employee_id == employee_id)
    if department:
        query = query.filter(base_calc_sub.c.department == department)
    if status and status != 'All':
        query = query.filter(base_calc_sub.c.status == status)

    total = query.group_by(base_calc_sub.c.employee_id, base_calc_sub.c.work_date, base_calc_sub.c.shift, base_calc_sub.c.department, base_calc_sub.c.status).count()
    
    results = query.group_by(base_calc_sub.c.employee_id, base_calc_sub.c.work_date, base_calc_sub.c.shift, base_calc_sub.c.department, base_calc_sub.c.status) \
                   .order_by(desc(base_calc_sub.c.work_date), base_calc_sub.c.employee_id) \
                   .offset((page - 1) * size) \
                   .limit(size) \
                   .all()
    
    summary_items = AttendanceService.process_summary_rows(results)
        
    return {
        "items": summary_items,
        "total": total,
        "page": page,
        "size": size
    }

@router.get("/detail")
def get_attendance_detail(
    employee_id: str = Query(...),
    work_date: date = Query(...),
    db: Session = Depends(get_db)
):
    from sqlalchemy import Date, case, text
    # ─── AGGREGATED QUERY FOR DETAIL ──────────────────────────────
    base_calc_sub = db.query(
        AttendanceLog.attendance_time,
        AttendanceLog.employee_id,
        case(
            (EmployeeMetadata.shift == text("'D'"), func.cast(func.dateadd(text("hour"), text("-10"), AttendanceLog.attendance_time), Date)),
            else_=func.cast(func.dateadd(text("hour"), text("-4"), AttendanceLog.attendance_time), Date)
        ).label("work_date")
    ).outerjoin(EmployeeMetadata, AttendanceLog.employee_id == EmployeeMetadata.employee_id).subquery()

    logs = db.query(AttendanceLog) \
             .join(base_calc_sub, AttendanceLog.id == base_calc_sub.c.id) \
             .filter(base_calc_sub.c.employee_id == employee_id) \
             .filter(base_calc_sub.c.work_date == work_date) \
             .order_by(AttendanceLog.attendance_time) \
             .all()
    return logs
