import argparse
import os
import uvicorn
from fastapi import FastAPI, Depends, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text, Date, case
from typing import List, Optional
from datetime import date, datetime, time, timedelta
from db import get_db, AttendanceLog, EmployeeMetadata
from sync import sync_all_machines, get_machine_list, sync_status, sync_employees_from_excel, delete_user_from_all_machines

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
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(AttendanceLog).outerjoin(EmployeeMetadata, AttendanceLog.employee_id == EmployeeMetadata.employee_id)
    
    if employee_id:
        query = query.filter(AttendanceLog.employee_id == employee_id)
    if machine_ip:
        query = query.filter(AttendanceLog.machine_ip == machine_ip)
    if start_date:
        query = query.filter(AttendanceLog.attendance_date >= start_date)
    if end_date:
        query = query.filter(AttendanceLog.attendance_date <= end_date)
    if status:
        query = query.filter(EmployeeMetadata.status == status)
        
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

@app.get("/api/attendance/summary")
def get_attendance_summary(
    employee_id: Optional[str] = Query(None),
    machine_ip: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    min_hours: Optional[float] = Query(None),
    max_hours: Optional[float] = Query(None),
    only_missing: bool = Query(False),
    shift: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1),
    db: Session = Depends(get_db)
):
    # Shift-specific Date Logic:
    # Night Shift (D): We offset by 10 hours so an 08:00 AM tap is counted as 'Yesterday'.
    # Day Shift (N): We offset by 4 hours for a normal morning boundary.
    # Step 1: Base subquery with join and date calculation
    # We use -10 for Night (D) and -4 for Day (N/All)
    base_calc_sub = db.query(
        AttendanceLog.id,
        AttendanceLog.attendance_time,
        AttendanceLog.employee_id,
        AttendanceLog.machine_ip, # Included for potential further filtering
        EmployeeMetadata.shift,
        EmployeeMetadata.status,
        case(
            (EmployeeMetadata.shift == text("'D'"), func.cast(func.dateadd(text("hour"), text("-10"), AttendanceLog.attendance_time), Date)),
            else_=func.cast(func.dateadd(text("hour"), text("-4"), AttendanceLog.attendance_time), Date)
        ).label("work_date")
    ).outerjoin(EmployeeMetadata, AttendanceLog.employee_id == EmployeeMetadata.employee_id).subquery()
    
    # Step 2: Aggregated query on top of the subquery
    query = db.query(
        base_calc_sub.c.employee_id,
        base_calc_sub.c.work_date,
        func.min(base_calc_sub.c.attendance_time).label("first_tap"),
        func.max(base_calc_sub.c.attendance_time).label("last_tap"),
        func.count(base_calc_sub.c.id).label("tap_count"),
        base_calc_sub.c.shift,
        base_calc_sub.c.status
    )
    
    if employee_id:
        query = query.filter(base_calc_sub.c.employee_id == employee_id)
    if machine_ip:
        query = query.filter(base_calc_sub.c.machine_ip == machine_ip)
    if start_date:
        query = query.filter(base_calc_sub.c.work_date >= start_date)
    if end_date:
        query = query.filter(base_calc_sub.c.work_date <= end_date)
    if shift:
        query = query.filter(base_calc_sub.c.shift == shift)
    if status:
        query = query.filter(base_calc_sub.c.status == status)
        
    query = query.group_by(
        base_calc_sub.c.employee_id, 
        base_calc_sub.c.work_date, 
        base_calc_sub.c.shift, 
        base_calc_sub.c.status
    )
    
    # Advanced Filtering using HAVING
    if only_missing:
        query = query.having(func.count(base_calc_sub.c.id) == 1)
    else:
        # If filtering by hours, the record must have at least 2 taps (In and Out)
        if min_hours is not None:
            # We calculate seconds difference and divide by 3600 for precision
            # Note: Cast to float for division
            query = query.having(
                (func.datediff(text("second"), func.min(base_calc_sub.c.attendance_time), func.max(base_calc_sub.c.attendance_time)) / 3600.0) >= min_hours
            )
        if max_hours is not None:
            query = query.having(
                (func.datediff(text("second"), func.min(base_calc_sub.c.attendance_time), func.max(base_calc_sub.c.attendance_time)) / 3600.0) <= max_hours
            )
    
    # Use a subquery to correctly count grouped rows
    total_count = db.query(func.count()).select_from(query.subquery()).scalar()
    total_pages = (total_count + size - 1) // size
    
    # Order by work_date desc, then employee
    results = query.order_by(desc(base_calc_sub.c.work_date), base_calc_sub.c.employee_id) \
                   .offset((page - 1) * size) \
                   .limit(size) \
                   .all()
    
    summary_items = []
    for row in results:
        first = row.first_tap
        last = row.last_tap
        count = row.tap_count
        w_date = row.work_date
        shift = row.shift # 'N'=Day, 'D'=Night
        
        work_hours = 0.0
        note = ""
        
        if count > 1 and first != last:
            # Determine official shift start for clipping
            # Official start times: Day (N) = 08:00, Night (D) = 20:00
            if shift == 'D': # D = Night
                official_start = datetime.combine(w_date, time(20, 0))
            else: # N = Day or N/A
                official_start = datetime.combine(w_date, time(8, 0))
            
            # Clip start time: Early check-ins don't count
            effective_in = max(first, official_start)
            
            diff = last - effective_in
            total_secs = diff.total_seconds()
            
            # Subtract 1 hour for break (3600 seconds)
            # Only if duration is positive
            if total_secs > 3600:
                work_hours = round((total_secs - 3600) / 3600, 2)
            else:
                work_hours = round(max(0, total_secs) / 3600, 2)
        else:
            note = "Missing Check-in/out (Only 1 tap)"
            
        summary_items.append({
            "employee_id": row.employee_id,
            "attendance_date": w_date,
            "first_tap": first,
            "last_tap": last,
            "tap_count": count,
            "work_hours": work_hours,
            "shift": row.shift or "N/A",
            "status": row.status or "Active",
            "note": note
        })
        
    return {
        "items": summary_items,
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

@app.get("/api/devices/capacity")
def get_devices_capacity():
    from sync import get_devices_capacity_info
    return get_devices_capacity_info()

@app.get("/api/sync-status")
def get_sync_status():
    return sync_status

@app.post("/api/employees/sync")
def sync_employees():
    count, msg = sync_employees_from_excel()
    if msg != "Success":
        raise HTTPException(status_code=500, detail=msg)
    return {"message": f"Successfully synced {count} employees from Excel."}

@app.delete("/api/employees/{employee_id}/machine-data")
def delete_employee_from_machines(employee_id: str):
    # This is the remote deletion from ZKTeco hardware
    results = delete_user_from_all_machines(employee_id)
    return {"results": results}

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Time Attendance System API.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)
