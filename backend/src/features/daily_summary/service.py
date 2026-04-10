import logging
import pandas as pd
import threading
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import exists

from database import SessionLocal, ShiftRule, EmployeeMetadata, EmployeeLocalRegistry
from utils.stats_utils import compute_day_stats
from features.logs.service import get_machine_list, get_users_from_machine

logger = logging.getLogger(__name__)

# Sync Status Tracking
sync_status = {
    "is_running": False,
    "progress": 0,
    "total": 0,
    "current_step": "",
    "error": None,
    "excel_count": 0,
    "machine_only_count": 0
}
status_lock = threading.Lock()

def process_summary_rows(results: List[Any], rules_pool: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    """
    Ported from AttendanceService. Transform raw grouped SQLAlchemy rows into a list of summary dictionaries.
    """
    if rules_pool is None:
        db = SessionLocal()
        try:
            rules_pool = db.query(ShiftRule).all()
        finally:
            db.close()

    summary_items = []
    for row in results:
        first      = row.first_tap
        last       = row.last_tap
        count      = row.tap_count
        w_date     = row.work_date
        row_shift  = row.shift
        department = getattr(row, "department", None)

        work_hours       = 0.0
        minutes_late     = None
        minutes_early_lv = None
        note = ""

        # Logic: If all taps are before shift start (8:00 for N, 20:00 for D),
        # AND they are on the same calendar day, treat as Missing Out.
        boundary_hour = 20 if row_shift == 'D' else 8
        is_double_checkin = (count > 1 and first != last and 
                             last.date() == first.date() and 
                             last.hour < boundary_hour)
        
        is_valid_day = (count > 1 and first != last and not is_double_checkin)

        if is_valid_day:
            work_hours, _, _, minutes_late, minutes_early_lv = compute_day_stats(
                first, last, w_date, department, row_shift, rules_pool=rules_pool
            )
        else:
            note = "Missing Check-in/out"

        summary_items.append({
            "employee_id": row.employee_id,
            "attendance_date": w_date,
            "first_tap": first,
            "last_tap": last,
            "tap_count": count,
            "work_hours": work_hours,
            "shift": row_shift or "N/A",
            "status": (row.status if hasattr(row, "status") and row.status else "Active"),
            "note": note,
            "minutes_late": minutes_late,
            "minutes_early_leave": minutes_early_lv,
        })
    return summary_items

def sync_employees_full(file_bytes: bytes):
    """
    Upgraded Sync:
    1. Sync Excel to EmployeeMetadata.
    2. Upsert Excel users into EmployeeLocalRegistry (source_status=excel_synced).
    3. Scan all machines for users.
    4. Upsert machine-only users into EmployeeLocalRegistry (source_status=machine_only) if not already synced from Excel.
    """
    global sync_status
    
    with status_lock:
        if sync_status["is_running"]:
            return
        sync_status.update({
            "is_running": True, "progress": 0, "total": 0, 
            "current_step": "Reading Excel...", "error": None,
            "excel_count": 0, "machine_only_count": 0
        })

    db = SessionLocal()
    try:
        # 1. Process Excel
        df = pd.read_excel(file_bytes)
        df.columns = df.columns.str.strip()
        
        if 'EMP_ID' not in df.columns:
            raise ValueError("Excel file missing required column: EMP_ID")

        total_rows = len(df)
        with status_lock:
            sync_status["total"] = total_rows
            sync_status["current_step"] = f"Processing {total_rows} Excel records..."

        existing_meta = {e.employee_id: e for e in db.query(EmployeeMetadata).all()}
        existing_registry = {r.employee_id: r for r in db.query(EmployeeLocalRegistry).all()}
        
        excel_synced_ids = set()
        
        for idx, row in df.iterrows():
            emp_id = str(row['EMP_ID'])
            excel_synced_ids.add(emp_id)
            
            # Update EmployeeMetadata
            meta = existing_meta.get(emp_id)
            if not meta:
                meta = EmployeeMetadata(employee_id=emp_id)
                db.add(meta)
                existing_meta[emp_id] = meta
            
            if 'SHIFT' in row and pd.notna(row['SHIFT']):
                val = str(row['SHIFT']).strip().upper()
                meta.shift = val
                meta.status = 'TV' if val == 'TV' else 'Active'
            
            if 'EMP_NAME' in df.columns and pd.notna(row['EMP_NAME']): meta.emp_name = str(row['EMP_NAME'])
            if 'DEPARTMENT' in df.columns and pd.notna(row['DEPARTMENT']): meta.department = str(row['DEPARTMENT'])
            if 'GROUP' in df.columns and pd.notna(row['GROUP']): meta.group = str(row['GROUP'])
            if 'START_DATE' in df.columns and pd.notna(row['START_DATE']):
                meta.start_date = pd.to_datetime(row['START_DATE']).date()

            # Upsert into EmployeeLocalRegistry
            reg = existing_registry.get(emp_id)
            if not reg:
                reg = EmployeeLocalRegistry(employee_id=emp_id)
                db.add(reg)
                existing_registry[emp_id] = reg
            
            reg.emp_name = meta.emp_name
            reg.department = meta.department
            reg.group_name = meta.group
            reg.shift = meta.shift
            reg.source_status = 'excel_synced'
            
            with status_lock:
                sync_status["excel_count"] += 1
                sync_status["progress"] = int((sync_status["excel_count"] / total_rows) * 50)

        db.commit()

        # 2. Process Machine Users
        with status_lock:
            sync_status["current_step"] = "Scanning machines for additional users..."
            sync_status["progress"] = 60

        machine_ips = get_machine_list()
        machine_users_found = {} # emp_id -> name
        
        for ip in machine_ips:
            users, msg = get_users_from_machine(ip)
            if msg == "Success":
                for u in users:
                    u_id = str(u['user_id'])
                    if u_id not in machine_users_found:
                        machine_users_found[u_id] = u['name']

        # 3. Merge Machine-only users
        for u_id, u_name in machine_users_found.items():
            if u_id in excel_synced_ids:
                continue # Already handled via Excel
            
            reg = existing_registry.get(u_id)
            if not reg:
                reg = EmployeeLocalRegistry(employee_id=u_id, emp_name=u_name, source_status='machine_only')
                db.add(reg)
                existing_registry[u_id] = reg
                with status_lock: sync_status["machine_only_count"] += 1
            elif reg.source_status == 'log_only': # Upgrade from log_only to machine_only
                reg.source_status = 'machine_only'
                if not reg.emp_name: reg.emp_name = u_name
                with status_lock: sync_status["machine_only_count"] += 1

        db.commit()
        
        with status_lock:
            sync_status.update({
                "progress": 100, 
                "is_running": False, 
                "current_step": "Sync complete."
            })

    except Exception as e:
        logger.error(f"Sync error: {e}")
        with status_lock:
            sync_status.update({"is_running": False, "error": str(e)})
    finally:
        db.close()
