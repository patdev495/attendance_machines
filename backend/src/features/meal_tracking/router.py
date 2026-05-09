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
from .service import get_meal_info, get_meal_list, check_meal_by_machine_id, resolve_emp_no, log_meal_swipe
from shared.hardware import get_canteen_machine_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meal", tags=["Meal Tracking"])

class ManualSwipeRequest(BaseModel):
    emp_id: str
    machine_ip: str = "Manual Override"

@router.post("/manual_swipe")
def manual_swipe(req: ManualSwipeRequest):
    """
    Manually register a meal swipe (e.g. fingerprint scanner failed).
    Logs the swipe to the database and returns the meal info.
    """
    now = datetime.now()
    meal_info = check_meal_by_machine_id(req.emp_id, now.date())
    
    # Log it to the database
    log_meal_swipe(req.emp_id, req.machine_ip, now, meal_info)
    
    if meal_info:
        return {"found": True, **meal_info}
        
    return {
        "found": False,
        "emp_no": req.emp_id,
        "is_registered": False,
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
