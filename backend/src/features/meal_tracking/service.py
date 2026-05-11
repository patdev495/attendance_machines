"""
Meal Tracking Service
Queries the external NY_VDS_DB database for meal registration data.
"""
import logging
from datetime import date, datetime
from sqlalchemy import text
from database import MealSessionLocal

logger = logging.getLogger(__name__)


def get_meal_info(emp_no: str, check_date: date = None) -> dict | None:
    """
    Look up meal registration for a single employee on a given date.
    Returns dict with meal info or None if not registered.
    """
    if check_date is None:
        check_date = date.today()
    
    mfg_day = check_date.strftime("%Y%m%d")
    
    db = MealSessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT EMP_NO, EMP_NAME, DEPARTMENT, AREA,
                       MEAL_CODE, MEAL_NAME_VI, MEAL_NAME_ZH
                FROM HR_MEAL_ORDER
                WHERE EMP_NO = :emp_no AND MFG_DAY = :mfg_day
            """),
            {"emp_no": emp_no, "mfg_day": mfg_day}
        ).fetchone()
        
        if result:
            meal_code = result[4]
            meal_vi = result[5]
            is_registered = True
            
            # Check MEAL_CODE or MEAL_NAME_VI for unregistered status
            if meal_code and (meal_code.strip().upper() == "NONE" or "không đăng ký" in meal_code.lower() or "không đăng kí" in meal_code.lower()):
                is_registered = False
            elif meal_vi and ("không đăng ký" in meal_vi.lower() or "không đăng kí" in meal_vi.lower()):
                is_registered = False

            emp_no = result[0].strip() if result[0] else ""
            emp_name = result[1]
            department = result[2]

            from database import SessionLocal, EmployeeLocalRegistry
            local_db = SessionLocal()
            try:
                emp = local_db.query(EmployeeLocalRegistry).filter(
                    (EmployeeLocalRegistry.employee_id == emp_no) | 
                    (EmployeeLocalRegistry.full_emp_id == emp_no)
                ).first()
                if emp:
                    if emp.emp_name: emp_name = emp.emp_name
                    if emp.department: department = emp.department
            except Exception as e:
                logger.error(f"Error fetching local info for {emp_no}: {e}")
            finally:
                local_db.close()

            return {
                "emp_no": result[0],
                "emp_name": emp_name,
                "department": department,
                "area": result[3],
                "meal_code": result[4],
                "meal_name_vi": meal_vi,
                "meal_name_zh": result[6],
                "mfg_day": mfg_day,
                "is_registered": is_registered
            }
        
        # Fallback: User not found in NY_VDS_DB. Check if they exist in local MIS DB.
        from database import SessionLocal, EmployeeLocalRegistry
        local_db = SessionLocal()
        try:
            emp = local_db.query(EmployeeLocalRegistry).filter(
                (EmployeeLocalRegistry.employee_id == emp_no) | 
                (EmployeeLocalRegistry.full_emp_id == emp_no)
            ).first()
            if emp:
                return {
                    "emp_no": emp_no,
                    "emp_name": emp.emp_name,
                    "department": emp.department,
                    "area": None,
                    "meal_code": "NONE",
                    "meal_name_vi": "Không đăng ký",
                    "meal_name_zh": None,
                    "mfg_day": mfg_day,
                    "is_registered": False
                }
        except Exception as e:
            logger.error(f"Error fetching fallback local info for {emp_no}: {e}")
        finally:
            local_db.close()
            
        return None
    except Exception as e:
        logger.error(f"Error querying meal info for {emp_no}: {e}")
        return None
    finally:
        db.close()


def get_meal_list(start_date: date, end_date: date, emp_no: str | list[str] = None) -> list:
    """
    Get meal registrations for a date range, optionally filtered by employee.
    If emp_no is a list, matches any of the given IDs.
    """
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    db = MealSessionLocal()
    try:
        query = """
            SELECT m.EMP_NO, m.EMP_NAME, m.DEPARTMENT, m.AREA,
                   m.MEAL_CODE, m.MEAL_NAME_VI, m.MEAL_NAME_ZH, m.MFG_DAY
            FROM HR_MEAL_ORDER m
            WHERE m.MFG_DAY >= :start_date AND m.MFG_DAY <= :end_date
        """
        params = {"start_date": start_str, "end_date": end_str}
        
        if emp_no:
            if isinstance(emp_no, list):
                # Use IN clause for multiple possible IDs
                placeholders = ", ".join(f":emp_no_{i}" for i in range(len(emp_no)))
                query += f" AND m.EMP_NO IN ({placeholders})"
                for i, e_no in enumerate(emp_no):
                    params[f"emp_no_{i}"] = e_no
            else:
                query += " AND m.EMP_NO = :emp_no"
                params["emp_no"] = emp_no
        
        query += " ORDER BY m.MFG_DAY DESC, m.EMP_NO"
        
        results = db.execute(text(query), params).fetchall()
        
        # Fetch local names/departments to override external ones
        local_info = {}
        if results:
            from database import SessionLocal, EmployeeLocalRegistry
            local_db = SessionLocal()
            try:
                emp_ids = list({r[0].strip() for r in results if r[0]})
                if emp_ids:
                    emps = local_db.query(EmployeeLocalRegistry).filter(
                        (EmployeeLocalRegistry.employee_id.in_(emp_ids)) | 
                        (EmployeeLocalRegistry.full_emp_id.in_(emp_ids))
                    ).all()
                    for emp in emps:
                        if emp.full_emp_id:
                            local_info[emp.full_emp_id.strip()] = {"name": emp.emp_name, "dept": emp.department}
                        if emp.employee_id:
                            local_info[emp.employee_id.strip()] = {"name": emp.emp_name, "dept": emp.department}
            except Exception as e:
                logger.error(f"Error fetching local names: {e}")
            finally:
                local_db.close()

        final_results = []
        for r in results:
            meal_code = r[4]
            meal_vi = r[5]
            is_reg = True
            
            if meal_code and (meal_code.strip().upper() == "NONE" or "không đăng ký" in meal_code.lower() or "không đăng kí" in meal_code.lower()):
                is_reg = False
            elif meal_vi and ("không đăng ký" in meal_vi.lower() or "không đăng kí" in meal_vi.lower()):
                is_reg = False
                
            emp_no = r[0].strip() if r[0] else ""
            local_data = local_info.get(emp_no)
            
            emp_name = local_data["name"] if local_data and local_data["name"] else r[1]
            dept = local_data["dept"] if local_data and local_data["dept"] else r[2]

            final_results.append({
                "emp_no": r[0],
                "emp_name": emp_name,
                "department": dept,
                "area": r[3],
                "meal_code": r[4],
                "meal_name_vi": meal_vi,
                "meal_name_zh": r[6],
                "mfg_day": r[7].strip() if r[7] else None,
                "is_registered": is_reg
            })
            
        return final_results
    except Exception as e:
        logger.error(f"Error querying meal list: {e}")
        return []
    finally:
        db.close()


def resolve_emp_no(machine_user_id: str) -> list[str]:
    """
    Look up possible EMP_NOs using the machine user ID.
    Returns a list of possible EMP_NOs (full_emp_id, employee_id).
    """
    from database import SessionLocal, EmployeeLocalRegistry
    from sqlalchemy import func
    
    db = SessionLocal()
    possible_ids = []
    try:
        user_id = machine_user_id.strip()
        variations = [user_id]
        if user_id.upper().startswith("NY"):
            variations.append(user_id[2:])
        else:
            variations.append(f"NY{user_id}")
            
        for vid in variations:
            emp = db.query(EmployeeLocalRegistry).filter(
                func.ltrim(func.rtrim(EmployeeLocalRegistry.employee_id)) == vid
            ).first()
            
            if emp:
                if emp.full_emp_id:
                    possible_ids.append(emp.full_emp_id.strip())
                possible_ids.append(emp.employee_id.strip())
                
            possible_ids.append(vid)
        
        # return unique IDs while preserving order
        return list(dict.fromkeys(possible_ids))
    finally:
        db.close()

def log_meal_swipe(machine_user_id: str, machine_ip: str, swipe_time: datetime, meal_info: dict | None):
    """
    Log a meal confirmation swipe to the MIS database table MealTrackingHistory.
    """
    from database import SessionLocal, MealTrackingHistory
    db = SessionLocal()
    try:
        emp_name = meal_info.get("emp_name") if meal_info else None
        department = meal_info.get("department") if meal_info else None
        meal_code = meal_info.get("meal_code") if meal_info else None
        meal_name = meal_info.get("meal_name_vi") if meal_info else None
        is_registered = meal_info.get("is_registered", False) if meal_info else False

        history = MealTrackingHistory(
            employee_id=machine_user_id,
            emp_name=emp_name,
            department=department,
            meal_code=meal_code,
            meal_name=meal_name,
            machine_ip=machine_ip,
            swipe_time=swipe_time,
            is_registered=is_registered
        )
        db.add(history)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log meal swipe: {e}")
        db.rollback()
    finally:
        db.close()

def was_meal_already_received(machine_user_id: str, check_date: date) -> bool:
    """
    Check if the user has already successfully swiped for a meal today
    by querying the external HR_MEAL_PICKUP_LOG table.
    """
    from database import MealSessionLocal
    from sqlalchemy import text
    
    db = MealSessionLocal()
    try:
        mfg_day = check_date.strftime("%Y%m%d")
        print(f">>> DEDUP CHECK: emp_no='{machine_user_id}', mfg_day='{mfg_day}'")
        # Check HR_MEAL_PICKUP_LOG for this user on this date
        result = db.execute(
            text("""
                SELECT COUNT(*) 
                FROM HR_MEAL_PICKUP_LOG 
                WHERE EMP_NO = :emp_no AND MFG_DAY = :mfg_day
            """),
            {"emp_no": machine_user_id, "mfg_day": mfg_day}
        ).scalar()
        
        print(f">>> DEDUP CHECK: COUNT result = {result}, returning {result > 0}")
        return result > 0
    except Exception as e:
        logger.error(f"Error checking duplicate meal in HR DB: {e}")
        return False
    finally:
        db.close()

def check_meal_by_machine_id(machine_user_id: str, check_date: date = None) -> dict | None:
    """
    Look up meal info using the machine user ID (which may differ from EMP_NO).
    First maps machine_user_id -> employee_id via EmployeeLocalRegistry,
    then queries meal DB.
    """
    if check_date is None:
        check_date = date.today()
        
    possible_ids = resolve_emp_no(machine_user_id)
    
    for emp_no in possible_ids:
        result = get_meal_info(emp_no, check_date)
        if result:
            return result
            
    return None

def try_log_meal_pickup(meal_info: dict, machine_ip: str) -> bool:
    """
    Atomically check-and-insert a meal pickup record.
    Uses INSERT ... WHERE NOT EXISTS to prevent race conditions.
    
    Returns:
        True if this was a NEW pickup (first swipe) - record was inserted.
        False if this was a DUPLICATE (already existed) - no insert happened.
    """
    if not meal_info or not meal_info.get('is_registered'):
        return False

    db = MealSessionLocal()
    try:
        emp_no = meal_info.get('emp_no')
        emp_name = meal_info.get('emp_name')
        department = meal_info.get('department')
        mfg_day = meal_info.get('mfg_day')
        area = meal_info.get('area') or "N/A"
        meal_code = meal_info.get('meal_code')
        meal_zh = meal_info.get('meal_name_zh')
        meal_vi = meal_info.get('meal_name_vi')
        pickup_time = datetime.now()
        
        from sqlalchemy.exc import IntegrityError
        # Atomic INSERT using DB's Unique Constraint (MFG_DAY, AREA, EMP_NO)
        db.execute(
            text("""
                INSERT INTO HR_MEAL_PICKUP_LOG 
                (MFG_DAY, AREA, EMP_NO, EMP_NAME, MEAL_CODE, MEAL_NAME_ZH, MEAL_NAME_VI, 
                 PICKUP_TIME, DEVICE_NAME, PICKUP_BY, DEPARTMENT)
                VALUES 
                (:mfg_day, :area, :emp_no, :emp_name, :meal_code, :meal_zh, :meal_vi, 
                 :pickup_time, :device_name, :pickup_by, :dept)
            """),
            {
                "mfg_day": mfg_day,
                "area": area,
                "emp_no": emp_no,
                "emp_name": emp_name,
                "meal_code": meal_code,
                "meal_zh": meal_zh,
                "meal_vi": meal_vi,
                "pickup_time": pickup_time,
                "device_name": machine_ip,
                "pickup_by": "System",
                "dept": department
            }
        )
        db.commit()
        
        was_new = True
        print(f">>> ATOMIC MEAL: emp_no='{emp_no}', mfg_day='{mfg_day}', was_new={was_new}")
        logger.info(f"Successfully logged external meal pickup for {emp_no} on {machine_ip}")
        return True
        
    except IntegrityError as ie:
        # Handle race condition: Check if the record was JUST inserted (within last 60s)
        # by another process/thread or a hardware retry.
        db.rollback()
        
        import time
        time.sleep(0.1) # Wait 100ms for parallel process to commit
        
        # Check the existing record's pickup time
        db_check = MealSessionLocal()
        try:
            mfg_day = meal_info.get('mfg_day')
            existing = db_check.execute(
                text("SELECT PICKUP_TIME FROM HR_MEAL_PICKUP_LOG WHERE EMP_NO = :emp_no AND MFG_DAY = :mfg_day"),
                {"emp_no": emp_no, "mfg_day": mfg_day}
            ).fetchone()
            
            if existing:
                pickup_time_db = existing[0]
                if isinstance(pickup_time_db, str):
                    pickup_time_db = datetime.fromisoformat(pickup_time_db)
                
                time_diff = (datetime.now() - pickup_time_db).total_seconds()
                # If it happened within the last 5 seconds, it's a race condition or hardware replay.
                # More than 5 seconds is treated as a genuine duplicate swipe.
                if abs(time_diff) < 5:
                    print(f">>> ATOMIC MEAL: emp_no='{emp_no}', mfg_day='{mfg_day}', was_new=True (Race condition success, diff={time_diff:.2f}s)")
                    return True
        except Exception as e2:
            logger.error(f"Error checking race condition: {e2}")
        finally:
            db_check.close()

        print(f">>> ATOMIC MEAL: emp_no='{emp_no}', mfg_day='{mfg_day}', was_new=False (IntegrityError: {ie})")
        logger.info(f"Duplicate meal pickup skipped for {meal_info.get('emp_no')} (already in HR DB)")
        return False
    except Exception as e:
        logger.error(f"Error in atomic meal pickup for {meal_info.get('emp_no')}: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_today_pickups() -> list:
    """
    Fetch all successful meal pickups for today from HR_MEAL_PICKUP_LOG.
    Ordered by most recent first.
    """
    today_str = datetime.now().strftime("%Y%m%d")
    db = MealSessionLocal()
    try:
        query = """
            SELECT EMP_NO, EMP_NAME, DEPARTMENT, MEAL_CODE, MEAL_NAME_VI, PICKUP_TIME, DEVICE_NAME
            FROM HR_MEAL_PICKUP_LOG
            WHERE MFG_DAY = :today
            ORDER BY PICKUP_TIME DESC
        """
        results = db.execute(text(query), {"today": today_str}).fetchall()
        pickups = []
        for r in results:
            pickups.append({
                "emp_no": r[0].strip() if r[0] else "",
                "emp_name": r[1],
                "department": r[2],
                "meal_code": r[3],
                "meal_name_vi": r[4],
                "attendance_time": r[5].isoformat() if isinstance(r[5], datetime) else r[5],
                "machine_ip": r[6]
            })
        return pickups
    except Exception as e:
        logger.error(f"Error fetching today pickups: {e}")
        return []
    finally:
        db.close()
