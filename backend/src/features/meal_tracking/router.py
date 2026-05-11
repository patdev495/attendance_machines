"""
Meal Tracking API Router
Provides endpoints for meal registration lookup and kiosk WebSocket support.
"""
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from typing import Optional
from datetime import date as date_type
import logging

from pydantic import BaseModel
from datetime import datetime
from .service import (
    get_meal_info, 
    get_meal_list, 
    check_meal_by_machine_id, 
    resolve_emp_no, 
    log_meal_swipe,
    try_log_meal_pickup,
    get_today_pickups
)
from shared.hardware import get_canteen_machine_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meal", tags=["Meal Tracking"])

@router.get("/today_pickups")
def today_pickups():
    """Get all successful pickups for today from HR_MEAL_PICKUP_LOG"""
    return {"items": get_today_pickups()}

class ManualSwipeRequest(BaseModel):
    emp_id: str
    machine_ip: str = "Manual Override"

@router.post("/manual_swipe")
def manual_swipe(req: ManualSwipeRequest):
    """
    Manually register a meal swipe (e.g. fingerprint scanner failed).
    Logs the swipe to the local database and optionally to the external HR database.
    """
    now = datetime.now()
    today = now.date()
    
    # 1. Look up meal registration first to resolve the "canonical" EMP_NO
    meal_info = check_meal_by_machine_id(req.emp_id, today)
    
    # 2. Use the resolved emp_no for internal logging/duplicate check if found, 
    #    otherwise fallback to the raw input ID.
    target_emp_id = meal_info.get("emp_no") if meal_info else req.emp_id
    
    # 3. Atomic check-and-insert to HR_MEAL_PICKUP_LOG
    if meal_info and meal_info.get('is_registered'):
        was_new = try_log_meal_pickup(meal_info, req.machine_ip)
        is_duplicate = not was_new
    else:
        is_duplicate = False
    
    # 4. Always log to local MIS history for auditing (using resolved ID)
    log_meal_swipe(target_emp_id, req.machine_ip, now, meal_info)
    
    if meal_info:
        return {
            "found": True, 
            "is_duplicate": is_duplicate,
            **meal_info
        }
        
    return {
        "found": False,
        "emp_no": req.emp_id,
        "is_registered": False,
        "is_duplicate": is_duplicate,
        "message": "Không tìm thấy đăng ký suất ăn"
    }


@router.get("/check/{emp_id}")
def check_meal(emp_id: str, check_date: Optional[date_type] = Query(None)):
    """
    Check meal registration for an employee.
    Tries both direct EMP_NO match and machine-ID-to-employee mapping.
    """
    result = check_meal_by_machine_id(emp_id, check_date)
    if result:
        return {"found": True, **result}
    
    return {
        "found": False,
        "emp_no": emp_id,
        "is_registered": False,
        "message": "Không tìm thấy đăng ký suất ăn"
    }


@router.get("/list")
def list_meals(
    start_date: date_type = Query(...),
    end_date: date_type = Query(...),
    emp_no: Optional[str] = Query(None)
):
    """
    List meal registrations for a date range, optionally filtered by employee.
    """
    target_ids = None
    if emp_no:
        target_ids = resolve_emp_no(emp_no)
        
    items = get_meal_list(start_date, end_date, target_ids)
    return {
        "items": items,
        "total_count": len(items)
    }


@router.get("/canteen-machines")
def get_canteen_machines():
    """
    Returns list of machine IPs tagged as canteen in machines.txt.
    Used by the kiosk UI to know which machines to listen for.
    """
    return {"machines": get_canteen_machine_list()}

@router.get("/today_stats")
def get_today_meal_stats():
    """
    Returns today's meal statistics: registered vs picked up for each meal type.
    """
    from database import MealSessionLocal
    from sqlalchemy import text
    from datetime import date
    
    today = date.today().strftime("%Y%m%d")
    db = MealSessionLocal()
    try:
        registered_query = text("""
            SELECT MEAL_CODE, COUNT(*) as cnt
            FROM HR_MEAL_ORDER
            WHERE MFG_DAY = :mfg_day
            GROUP BY MEAL_CODE
        """)
        registered_rows = db.execute(registered_query, {"mfg_day": today}).fetchall()
        
        picked_up_query = text("""
            SELECT MEAL_CODE, COUNT(*) as cnt
            FROM HR_MEAL_PICKUP_LOG
            WHERE MFG_DAY = :mfg_day
            GROUP BY MEAL_CODE
        """)
        picked_up_rows = db.execute(picked_up_query, {"mfg_day": today}).fetchall()
        
        stats = {
            "RICE": {"registered": 0, "picked_up": 0},
            "NOODLE": {"registered": 0, "picked_up": 0},
            "BREAD": {"registered": 0, "picked_up": 0},
        }
        
        for r in registered_rows:
            if r.MEAL_CODE in stats:
                stats[r.MEAL_CODE]["registered"] = r.cnt
                
        for r in picked_up_rows:
            if r.MEAL_CODE in stats:
                stats[r.MEAL_CODE]["picked_up"] = r.cnt
                
        return stats
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()
