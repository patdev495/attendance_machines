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
        is_registered = bool(meal_info)

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
