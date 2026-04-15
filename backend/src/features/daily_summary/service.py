import logging
import pandas as pd
import threading
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import exists, text

from database import SessionLocal, EmployeeMetadata, EmployeeLocalRegistry, EmployeeDailyShifts, ShiftDefinition

from utils.stats_utils import compute_day_stats, determine_missing_tap, parse_shift_window

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
    Transform raw grouped SQLAlchemy rows into a list of summary dictionaries.
    Supports dynamic daily shift codes (Phase 13).
    """
    from utils.stats_utils import FULL_DAY_LEAVE_CODES

    if rules_pool is None:
        db = SessionLocal()
        try:
            rules_pool = db.query(ShiftDefinition).all()
        finally:
            db.close()


    summary_items = []
    for row in results:
        first      = getattr(row, "first_tap", None)
        last       = getattr(row, "last_tap", None)
        count      = getattr(row, "tap_count", 0)
        w_date     = getattr(row, "work_date", None)
        # Use the combined calculation shift from the row object
        row_shift  = getattr(row, "shift", None)
        department = getattr(row, "department", None)
        daily_code = getattr(row, "daily_shift_code", None)
        
        effective_shift_raw = daily_code or row_shift
        
        # Phase 13: Check if the shift code is defined in the ShiftDefinitions table
        # Only pull from rules_pool if we have one.
        valid_codes = {r.shift_code for r in rules_pool} if rules_pool else set()
        
        # Display "-" if no shift, but internally calculate as "N"
        if not effective_shift_raw or effective_shift_raw.strip().upper() not in valid_codes:
            shift_code_display = "NA"
            calculation_shift = "N" # Fallback for calculation
        else:
            shift_code_display = effective_shift_raw.strip().upper()
            calculation_shift = shift_code_display


        work_hours       = 0.0
        minutes_late     = 0
        minutes_early_lv = 0
        note = ""

        # Check if this is a full-day leave code (Even if they quet)
        is_leave_code = calculation_shift.strip().upper() in FULL_DAY_LEAVE_CODES
        
        # 1. Handle Absent / No Taps
        if not first or not last or count == 0:
            window = parse_shift_window(calculation_shift, department, rules_pool=rules_pool)
            summary_items.append({
                "employee_id": row.employee_id,
                "full_emp_id": getattr(row, "full_emp_id", None),
                "emp_name": getattr(row, "emp_name", None),
                "attendance_date": w_date,
                "first_tap": None,
                "last_tap": None,
                "tap_count": 0,
                "work_hours": 0.0,
                "hours_standard": 0.0,
                "hours_ot": 0.0,
                "hours_p": window.get('leave_hours_p', 0.0),
                "hours_r": window.get('leave_hours_r', 0.0),
                "hours_o": window.get('leave_hours_o', 0.0),
                "shift": shift_code_display,
                "status": (row.status if hasattr(row, "status") and row.status else "Active"),
                "note": (calculation_shift.strip().upper() if window['is_leave'] else "Vắng"),
                "minutes_late": 0,
                "minutes_early_leave": 0,
                "daily_shift_code": shift_code_display,
            })
            continue

        # 2. Handle known leave code with some quets (optional, usually they don't quet if leave)
        if is_leave_code:
            # For now, follow the same logic as before for full-day leave
            window = parse_shift_window(calculation_shift, department, rules_pool=rules_pool)
            summary_items.append({
                "employee_id": row.employee_id,
                "emp_name": getattr(row, "emp_name", None),
                "attendance_date": w_date,
                "first_tap": first,
                "last_tap": last,
                "tap_count": count,
                "work_hours": 0.0,
                "hours_standard": 0.0,
                "hours_ot": 0.0,
                "shift": shift_code_display,
                "status": (row.status if hasattr(row, "status") and row.status else "Active"),
                "note": calculation_shift.strip().upper(),
                "minutes_late": 0,
                "minutes_early_leave": 0,
                "daily_shift_code": shift_code_display,
            })
            continue

        # Logic: If all taps are before shift start, treat as Missing Out.
        boundary_hour = 20 if calculation_shift.upper() == 'D' else 8
        is_double_checkin = (count > 1 and first != last and 
                             last.date() == first.date() and 
                             last.hour < boundary_hour)
        
        # compute_day_stats now returns 8 values
        work_hours, hours_standard, hours_ot, minutes_late, minutes_early_lv, hours_p, hours_r, hours_o = compute_day_stats(
            first, last, w_date, department, calculation_shift, rules_pool=rules_pool
        )
        
        if not (count > 1 and first != last and not is_double_checkin):
            note = determine_missing_tap(first, w_date, calculation_shift, department, rules_pool)
            # Single tap: suppress the metric we cannot know
            if note == "Missing Check-out":
                minutes_early_lv = 0   # don't know when they left
            elif note == "Missing Check-in":
                minutes_late = 0       # don't know when they arrived

        emp_name = getattr(row, "emp_name", None)
        if not emp_name:
            logger.debug(f"Missing name for employee_id: {row.employee_id}")

        summary_items.append({
            "employee_id": row.employee_id,
            "full_emp_id": getattr(row, "full_emp_id", None),
            "emp_name": emp_name,
            "attendance_date": w_date,
            "first_tap": first,
            "last_tap": last,
            "tap_count": count,
            "work_hours": hours_standard,
            "hours_standard": hours_standard,
            "hours_ot": hours_ot,

            "hours_p": hours_p,
            "hours_r": hours_r,
            "hours_o": hours_o,
            "shift": shift_code_display,
            "status": (row.status if hasattr(row, "status") and row.status else "Active"),
            "note": note,
            "minutes_late": minutes_late,
            "minutes_early_leave": minutes_early_lv,
            "daily_shift_code": shift_code_display,
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
        
        emp_col = 'FULL_EMP_ID' if 'FULL_EMP_ID' in df.columns else 'EMP_ID'
        if emp_col not in df.columns:
            raise ValueError("Excel file missing required column: EMP_ID or FULL_EMP_ID")

        total_rows = len(df)
        with status_lock:
            sync_status["total"] = total_rows
            sync_status["current_step"] = f"Processing {total_rows} Excel records..."

        # --- CLEAN SYNC PRE-PHASE: Mark all current excel_synced as stale ---
        db.execute(text("UPDATE EmployeeLocalRegistry SET source_status = 'stale' WHERE source_status = 'excel_synced'"))
        db.commit()

        existing_meta = {e.employee_id: e for e in db.query(EmployeeMetadata).all()}
        existing_registry = {r.employee_id: r for r in db.query(EmployeeLocalRegistry).all()}
        
        excel_synced_ids = set()
        
        for idx, row in df.iterrows():
            # ID mappings based on user's final logic: EMP_ID is the PK, FULL_EMP_ID is display
            emp_id_raw = str(row.get('EMP_ID', '')).strip()
            full_id_raw = str(row.get('FULL_EMP_ID', '')).strip()
            
            # Clean .0 from Excel numbers
            if emp_id_raw.endswith('.0'): emp_id_raw = emp_id_raw[:-2]
            if full_id_raw.endswith('.0'): full_id_raw = full_id_raw[:-2]

            # PK is ALWAYS EMP_ID
            emp_id = emp_id_raw
            if not emp_id or emp_id.lower() == 'nan':
                continue
            
            f_id = full_id_raw if (full_id_raw and full_id_raw.lower() != 'nan') else None
            
            excel_synced_ids.add(emp_id)
            
            # Update EmployeeMetadata
            meta = existing_meta.get(emp_id)
            if not meta:
                meta = EmployeeMetadata(employee_id=emp_id)
                db.add(meta)
                existing_meta[emp_id] = meta
            
            meta.full_emp_id = f_id
            
            if 'SHIFT' in row and pd.notna(row['SHIFT']):
                val = str(row['SHIFT']).strip().upper()
                meta.shift = val
                meta.status = 'TV' if val == 'TV' else 'Active'
            
            if 'EMP_NAME' in df.columns and pd.notna(row['EMP_NAME']): meta.emp_name = str(row['EMP_NAME'])
            if 'DEPARTMENT' in df.columns and pd.notna(row['DEPARTMENT']): meta.department = str(row['DEPARTMENT'])
            if 'GROUP' in df.columns and pd.notna(row['GROUP']): meta.group = str(row['GROUP'])
            # Phase 13: Robust hired date mapping
            start_date_aliases = ['START_DATE', 'NGÀY VÀO LÀM', 'NGAY VAO LAM', 'HIRED DATE', 'DATE HIRED']
            hired_date_val = None
            for alias in start_date_aliases:
                if alias in df.columns:
                    hired_date_val = row[alias]
                    break
            
            if hired_date_val and pd.notna(hired_date_val):
                try:
                    meta.start_date = pd.to_datetime(hired_date_val).date()
                except:
                    pass

            # Upsert into EmployeeLocalRegistry
            reg = existing_registry.get(emp_id)
            if not reg:
                reg = EmployeeLocalRegistry(employee_id=emp_id)
                db.add(reg)
                existing_registry[emp_id] = reg
            
            reg.emp_name = meta.emp_name
            reg.department = meta.department
            reg.group_name = meta.group
            reg.start_date = meta.start_date
            reg.shift = meta.shift
            reg.full_emp_id = f_id
            reg.source_status = 'excel_synced'
            
            with status_lock:
                sync_status["excel_count"] += 1
                sync_status["progress"] = int((sync_status["excel_count"] / total_rows) * 40)

        db.commit()

        # ── Phase 13: Parse daily shift columns (e.g. "1/4", "2/4", "15/4") ──
        with status_lock:
            sync_status["current_step"] = "Parsing daily shift assignments..."
            sync_status["progress"] = 45

        import re
        from datetime import date as date_type

        date_columns = {}  # col_name -> (day, month)
        for col in df.columns:
            col_str = str(col).strip()
            # Match patterns like "1/4", "01/04", "15/4"
            m = re.match(r'^(\d{1,2})/(\d{1,2})$', col_str)
            if m:
                day_val, month_val = int(m.group(1)), int(m.group(2))
                if 1 <= day_val <= 31 and 1 <= month_val <= 12:
                    date_columns[col] = (day_val, month_val)

        if date_columns:
            logger.info(f"Found {len(date_columns)} date columns for daily shifts")
            # Determine the year from the data (use current year as default)
            from datetime import datetime as dt_class
            current_year = dt_class.now().year

            # Load existing daily shifts for bulk upsert
            existing_shifts = {}
            for shift in db.query(EmployeeDailyShifts).all():
                key = (shift.employee_id, shift.work_date)
                existing_shifts[key] = shift

            daily_shift_count = 0
            for idx, row in df.iterrows():
                emp_id = str(row.get('EMP_ID', '')).strip()
                if emp_id.endswith('.0'): emp_id = emp_id[:-2]
                if not emp_id or emp_id.lower() == 'nan':
                    continue
                
                for col_name, (day_val, month_val) in date_columns.items():
                    cell_val = row.get(col_name)
                    # If cell is empty, interpret as 'NA' shift so it appears in reports
                    if pd.isna(cell_val) or str(cell_val).strip() == '':
                        shift_code = 'NA'
                    else:
                        shift_code = str(cell_val).strip().upper()
                    try:
                        w_date = date_type(current_year, month_val, day_val)
                    except ValueError:
                        continue  # Skip invalid dates like Feb 30

                    # Upsert: check if record exists in memory
                    key = (emp_id, w_date)
                    existing = existing_shifts.get(key)
                    if existing:
                        existing.shift_code = shift_code
                    else:
                        new_shift = EmployeeDailyShifts(
                            employee_id=emp_id, work_date=w_date, shift_code=shift_code
                        )
                        db.add(new_shift)
                        existing_shifts[key] = new_shift
                        
                    daily_shift_count += 1

            db.commit()
            logger.info(f"Upserted {daily_shift_count} daily shift assignments")
        else:
            logger.info("No date columns found in Excel — skipping daily shift sync")

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
            elif reg.source_status == 'log_only' or reg.source_status == 'stale': 
                # Upgrade to machine_only if they are found on machine
                reg.source_status = 'machine_only'
                if not reg.emp_name: reg.emp_name = u_name
                with status_lock: sync_status["machine_only_count"] += 1

        # --- CLEAN SYNC POST-PHASE: Demote remaining stale records to log_only ---
        db.execute(text("UPDATE EmployeeLocalRegistry SET source_status = 'log_only' WHERE source_status = 'stale'"))
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
