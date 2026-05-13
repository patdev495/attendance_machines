import logging
import pandas as pd
import threading
import io
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
                "hours_t": window.get('leave_hours_t', 0.0),
                "hours_c": window.get('leave_hours_c', 0.0),
                "hours_k": window.get('leave_hours_k', 0.0),
                "workday_base": window.get('workday_base', 8.0),
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
                "hours_p": window.get('leave_hours_p', 0.0),
                "hours_r": window.get('leave_hours_r', 0.0),
                "hours_o": window.get('leave_hours_o', 0.0),
                "hours_t": window.get('leave_hours_t', 0.0),
                "hours_c": window.get('leave_hours_c', 0.0),
                "hours_k": window.get('leave_hours_k', 0.0),
                "workday_base": window.get('workday_base', 8.0),
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
        
        # compute_day_stats now returns 14 values
        res_work, hours_standard, hours_ot, minutes_late, minutes_early_lv, hours_p, hours_r, hours_o, hours_t, hours_c, hours_k, night_subsidy, std_hours_shift, workday_base = compute_day_stats(
            first, last, w_date, department, calculation_shift, rules_pool=rules_pool
        )
        
        if not (count > 1 and first != last and not is_double_checkin):
            note = determine_missing_tap(first, w_date, calculation_shift, department, rules_pool)
            # Single tap: suppress the metric we cannot know and set the missing tap to None for UI
            if note == "Missing Check-out":
                minutes_early_lv = 0   # don't know when they left
                last = None            # Hide the duplicate time on UI
            elif note == "Missing Check-in":
                minutes_late = 0       # don't know when they arrived
                first = None           # Hide the duplicate time on UI

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
            "hours_t": hours_t,
            "hours_c": hours_c,
            "hours_k": hours_k,
            "shift": shift_code_display,
            "status": (row.status if hasattr(row, "status") and row.status else "Active"),
            "note": note,
            "minutes_late": minutes_late,
            "minutes_early_leave": minutes_early_lv,
            "daily_shift_code": shift_code_display,
            "night_subsidy": night_subsidy,
            "standard_hours_shift": std_hours_shift,
            "workday_base": workday_base,
        })

    return summary_items

def sync_employees_full(file_bytes: Optional[io.BytesIO] = None):
    """
    Upgraded Sync:
    1. Sync Excel to EmployeeMetadata (if file provided).
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
            "current_step": "Initializing sync...", "error": None,
            "excel_count": 0, "machine_only_count": 0
        })

    db = SessionLocal()
    try:
        if file_bytes is not None:
            # 1. Process Excel
            with status_lock:
                sync_status["current_step"] = "Reading Excel..."

            df = pd.read_excel(file_bytes)
            df.columns = df.columns.str.strip()
            
            emp_col = 'FULL_EMP_ID' if 'FULL_EMP_ID' in df.columns else 'EMP_ID'
            if emp_col not in df.columns:
                raise ValueError("Excel file missing required column: EMP_ID or FULL_EMP_ID")

            total_rows = len(df)
            with status_lock:
                sync_status["total"] = total_rows
                sync_status["current_step"] = f"Processing {total_rows} Excel records..."

            existing_meta = {e.employee_id: e for e in db.query(EmployeeMetadata).all()}
            
            excel_synced_ids = set()
            
            # Case-insensitive column matching
            cols_upper = {str(c).strip().upper(): c for c in df.columns}
            logger.info(f"Excel Columns detected: {list(cols_upper.keys())}")
            
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
                
                if 'EMP_NAME' in cols_upper and pd.notna(row[cols_upper['EMP_NAME']]): 
                    meta.emp_name = str(row[cols_upper['EMP_NAME']])
                if 'DEPARTMENT' in cols_upper and pd.notna(row[cols_upper['DEPARTMENT']]): 
                    meta.department = str(row[cols_upper['DEPARTMENT']])
                if 'GROUP' in cols_upper and pd.notna(row[cols_upper['GROUP']]): 
                    meta.group = str(row[cols_upper['GROUP']])
                
                # Phase 13: Robust hired date mapping
                start_date_aliases = ['START_DATE', 'NGÀY VÀO LÀM', 'NGAY VAO LAM', 'NGÀY VÀO', 'HIRED DATE', 'DATE HIRED', 'START DATE']
                hired_date_val = None
                
                found_alias = None
                for alias in start_date_aliases:
                    if alias.upper() in cols_upper:
                        hired_date_val = row[cols_upper[alias.upper()]]
                        found_alias = alias
                        break
                
                if hired_date_val is not None and pd.notna(hired_date_val):
                    if idx < 5:
                        logger.info(f"Row {idx} [{emp_id}] - Raw hired_date_val: {hired_date_val} (Type: {type(hired_date_val)})")
                    try:
                        # Handle Excel numeric dates (e.g. 44409)
                        if isinstance(hired_date_val, (int, float)) and not isinstance(hired_date_val, bool):
                            dt = pd.to_datetime(hired_date_val, unit='D', origin='1899-12-30')
                        else:
                            dt = pd.to_datetime(hired_date_val)
                            
                        if dt.year > 1900: # Use 1900 as more realistic bound for birth/hire dates
                            meta.start_date = dt.date()
                        else:
                            meta.start_date = None
                            if idx < 5: logger.info(f"Row {idx} skipped: year too low ({dt.year})")
                    except Exception as e:
                        meta.start_date = None
                        if idx < 5: logger.error(f"Row {idx} error: {e}")
                else:
                    meta.start_date = None

                # Force updated_at refresh to show sync happened
                from sqlalchemy import func
                meta.updated_at = func.now()

                if idx % 100 == 0:
                    logger.info(f"Syncing Excel row {idx}/{total_rows} (Last Match: {found_alias or 'None'})")

                with status_lock:
                    sync_status["progress"] = int((len(excel_synced_ids) / total_rows) * 40)

            # Xóa metadata của những nhân viên không còn trong file Excel
            for e_id, meta in existing_meta.items():
                if e_id not in excel_synced_ids:
                    db.delete(meta)
                    
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
        else:
            logger.info("No Excel file provided — skipping Excel processing and daily shift sync")

        # 2. Call centralized update_registry
        with status_lock:
            sync_status["current_step"] = "Scanning machines and logs to sync registry..."
            sync_status["progress"] = 60
            
        from features.employees.service import update_registry
        update_registry(db)
        
        excel_count = db.query(EmployeeLocalRegistry).filter_by(source_status='excel_synced').count()
        machine_only_count = db.query(EmployeeLocalRegistry).filter_by(source_status='machine_only').count()
        
        with status_lock:
            sync_status.update({
                "progress": 100, 
                "is_running": False, 
                "excel_count": excel_count,
                "machine_only_count": machine_only_count,
                "current_step": "Sync complete."
            })

    except Exception as e:
        logger.error(f"Sync error: {e}")
        with status_lock:
            sync_status.update({"is_running": False, "error": str(e)})
    finally:
        db.close()
