from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from database import get_db, EmployeeLocalRegistry
from typing import List, Optional
import threading

from .schema import (
    EmployeeOut, 
    EmployeeListOut,
    EmployeeUpdate, 
    UpdateStatusOut, 
    DeleteHardwareOut, 
    UpdateHardwareOut,
    BiometricCoverageOut
)
from .service import update_registry, delete_user_from_hardware, update_employee_info
from features.machines.service import (
    get_biometric_coverage, 
    bulk_delete_ids_from_selected_machines,
    run_bulk_delete_on_machines,
    bulk_delete_status
)

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

from sqlalchemy import cast, Integer

@router.get("", response_model=EmployeeListOut)
def list_employees(
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None, 
    source_status: Optional[str] = None,
    order: str = 'asc',

    db: Session = Depends(get_db)
):
    query = db.query(EmployeeLocalRegistry)
    if search:
        search = search.strip()
        found_ids = db.query(EmployeeLocalRegistry.employee_id).filter(
            EmployeeLocalRegistry.employee_id.ilike(f"%{search}%") |
            EmployeeLocalRegistry.full_emp_id.ilike(f"%{search}%") |
            EmployeeLocalRegistry.emp_name.collate('Vietnamese_CI_AI').ilike(f"%{search}%")
        ).all()
        
        target_ids = {r[0] for r in found_ids} | {search}
        # Use ltrim/rtrim to be robust against machine-generated ID spaces
        query = query.filter(func.ltrim(func.rtrim(EmployeeLocalRegistry.employee_id)).in_(list(target_ids)))
        
    if source_status:
        query = query.filter(EmployeeLocalRegistry.source_status == source_status)


    # Apply sorting (Numeric sort for employee_id)
    if order.lower() == 'desc':
        query = query.order_by(func.cast(EmployeeLocalRegistry.employee_id, Integer).desc())
    else:
        query = query.order_by(func.cast(EmployeeLocalRegistry.employee_id, Integer).asc())


    total_count = query.count()
    total_pages = max(1, -(-total_count // page_size))  # ceiling division
    skip = (page - 1) * page_size
    items = query.offset(skip).limit(page_size).all()

    return EmployeeListOut(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

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

@router.post("/bulk-delete-hardware")
async def bulk_delete_hardware_endpoint(
    bg_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    machine_ips: str = Form(...)  # Comma separated
):
    # 1. Parse IDs from file
    content = await file.read()
    text = content.decode('utf-8')
    # Filter out empty lines and strip whitespace
    employee_ids = [line.strip() for line in text.splitlines() if line.strip()]
    
    if not employee_ids:
        raise HTTPException(status_code=400, detail="No valid Employee IDs found in file")
        
    # 2. Parse IPs
    ips = [ip.strip() for ip in machine_ips.split(",") if ip.strip()]
    if not ips:
        raise HTTPException(status_code=400, detail="No target machines selected")
        
    # 3. Perform bulk deletion (Background)
    if bulk_delete_status["is_running"]:
        raise HTTPException(status_code=400, detail="Another bulk operation is in progress")
        
    bg_tasks.add_task(run_bulk_delete_on_machines, employee_ids, ips)
    return {"status": "Started", "count": len(employee_ids), "total_machines": len(ips)}
