from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db, EmployeeLocalRegistry
from typing import List, Optional
import threading

from .schema import (
    EmployeeOut, 
    EmployeeUpdate, 
    UpdateStatusOut, 
    DeleteHardwareOut, 
    UpdateHardwareOut,
    BiometricCoverageOut
)
from .service import update_registry, delete_user_from_hardware, update_employee_info
from sync_service import get_biometric_coverage

router = APIRouter(prefix="/api/employees", tags=["Employees"])

# Global state for registry update
registry_update_state = {
    "is_running": False,
    "status": "Idle",
    "progress": 0
}

def run_update_registry(db: Session):
    global registry_update_state
    registry_update_state["is_running"] = True
    registry_update_state["status"] = "Updating from Excel, Machines, and Logs..."
    try:
        update_registry(db)
        registry_update_state["status"] = "Success"
        registry_update_state["progress"] = 100
    except Exception as e:
        registry_update_state["status"] = f"Error: {e}"
    finally:
        registry_update_state["is_running"] = False

@router.get("", response_model=List[EmployeeOut])
def list_employees(
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None, 
    source_status: Optional[str] = None,
    shift: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(EmployeeLocalRegistry)
    
    if search:
        query = query.filter(EmployeeLocalRegistry.employee_id.ilike(f"%{search}%") | EmployeeLocalRegistry.emp_name.ilike(f"%{search}%"))
        
    if source_status:
        query = query.filter(EmployeeLocalRegistry.source_status == source_status)
        
    if shift:
        if shift == "__none__":
            query = query.filter(
                (EmployeeLocalRegistry.shift == None) | (EmployeeLocalRegistry.shift == "-")
            )
        else:
            query = query.filter(EmployeeLocalRegistry.shift == shift)
        
    return query.order_by(EmployeeLocalRegistry.employee_id).offset(skip).limit(limit).all()

@router.post("/update-registry", response_model=UpdateStatusOut)
def trigger_update_registry(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if registry_update_state["is_running"]:
        return UpdateStatusOut(**registry_update_state)
    
    background_tasks.add_task(run_update_registry, db)
    return UpdateStatusOut(is_running=True, status="Started", progress=0)

@router.get("/update-status", response_model=UpdateStatusOut)
def get_update_status():
    return UpdateStatusOut(**registry_update_state)

@router.delete("/{employee_id}", response_model=DeleteHardwareOut)
def delete_employee_from_hardware(employee_id: str):
    results = delete_user_from_hardware(employee_id)
    return DeleteHardwareOut(results=results)

@router.put("/{employee_id}", response_model=UpdateHardwareOut)
def update_employee(employee_id: str, payload: EmployeeUpdate, db: Session = Depends(get_db)):
    # Basic update logic inside the service
    # If emp_name is updated, it pushes to hardware
    results = {}
    if payload.emp_name:
        results = update_employee_info(employee_id, payload.emp_name, db)
    
    # Also update other fields locally
    registry_entry = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == employee_id).first()
    if not registry_entry:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    if payload.department is not None:
        registry_entry.department = payload.department
    if payload.group_name is not None:
        registry_entry.group_name = payload.group_name
    if payload.shift is not None:
        registry_entry.shift = payload.shift
        
    db.commit()
    
    return UpdateHardwareOut(results=results)

@router.get("/{employee_id}/biometric-coverage", response_model=List[BiometricCoverageOut])
def get_biometric_coverage_endpoint(employee_id: str):
    results = get_biometric_coverage(employee_id)
    return results
