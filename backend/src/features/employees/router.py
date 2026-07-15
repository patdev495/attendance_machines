from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db, EmployeeLocalRegistry
from typing import List, Optional
import threading
import logging
import base64
from config import config, DEMO_MODE

logger = logging.getLogger(__name__)

from .schema import (
    EmployeeOut, 
    EmployeeListOut,
    EmployeeUpdate, 
    UpdateStatusOut, 
    DeleteHardwareOut, 
    UpdateHardwareOut,
    BiometricCoverageOut,
    CardPrintRequest,
    CardPrintBtxmlOut
)
from .service import (
    update_registry, 
    delete_user_from_hardware, 
    update_employee_info, 
    export_employees_to_excel,
    run_bulk_push_on_machines,
    bulk_push_status
)
from .registry_service import filter_registry_by_employee_search
from features.machines.service import (
    get_biometric_coverage, 
    run_bulk_delete_on_machines,
    bulk_delete_status,
    get_user_photo_from_machine
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
    query = filter_registry_by_employee_search(query, db, search)
        
    if source_status:
        query = query.filter(EmployeeLocalRegistry.source_status == source_status)

    # Hanvon IDs can exceed SQL Server INT range, so do not cast employee_id.
    if order.lower() == 'desc':
        query = query.order_by(EmployeeLocalRegistry.employee_id.desc())
    else:
        query = query.order_by(EmployeeLocalRegistry.employee_id.asc())


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

@router.get("/export")
def export_employees(
    search: Optional[str] = None, 
    source_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from datetime import datetime
    output = export_employees_to_excel(db, search, source_status)
    filename = f"Employees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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
        registry_entry.department = payload.department  # type: ignore[assignment]
    if payload.group_name is not None:
        registry_entry.group_name = payload.group_name  # type: ignore[assignment]
    if payload.shift is not None:
        registry_entry.shift = payload.shift  # type: ignore[assignment]

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
    machine_ips: str = Form(...)
):
    # 1. Parse IDs from file
    content = await file.read()
    text = content.decode('utf-8')
    # Filter out empty lines and strip whitespace
    employee_ids = [line.strip() for line in text.splitlines() if line.strip()]
    
    if not employee_ids:
        raise HTTPException(status_code=400, detail="No valid Employee IDs found in file")
        
    ips = [ip.strip() for ip in machine_ips.split(",") if ip.strip()]
    if not ips:
        raise HTTPException(status_code=400, detail="No target machines selected")

    if bulk_delete_status["is_running"]:
        raise HTTPException(status_code=400, detail="Another bulk operation is in progress")
        
    bg_tasks.add_task(run_bulk_delete_on_machines, employee_ids, ips)
    return {"status": "Started", "count": len(employee_ids), "total_machines": len(ips)}

@router.post("/bulk-push-hardware")
async def bulk_push_hardware_endpoint(
    bg_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    machine_ips: str = Form(...)
):
    # 1. Parse IDs from file
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
        
    # Filter out empty lines and strip whitespace
    employee_ids = [line.strip() for line in text.splitlines() if line.strip()]
    
    if not employee_ids:
        raise HTTPException(status_code=400, detail="No valid Employee IDs found in file")
        
    ips = [ip.strip() for ip in machine_ips.split(",") if ip.strip()]
    if not ips:
        raise HTTPException(status_code=400, detail="No target machines selected")

    if bulk_push_status["is_running"]:
        raise HTTPException(status_code=400, detail="Another bulk push operation is in progress")
        
    bg_tasks.add_task(run_bulk_push_on_machines, employee_ids, ips)
    return {"status": "Started", "count": len(employee_ids), "total_machines": len(ips)}

@router.get("/bulk-push-status")
def get_bulk_push_status_endpoint():
    return bulk_push_status


def get_or_cache_employee_photo(employee_id: str, request: Request, db: Session) -> str:
    """
    Gets the cached employee photo URL. If not cached, fetches from machines on-demand and caches it.
    Returns the public HTTP URL of the image, or "" if not found.
    """
    avatar_dir = config.STATIC_DIR / "assets" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    
    avatar_file = avatar_dir / f"{employee_id}.jpg"
    
    if avatar_file.exists():
        return f"{request.base_url}assets/avatars/{employee_id}.jpg"
        
    if DEMO_MODE:
        # Mock successful photo retrieval in demo mode
        mock_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x0c\x01\x01\x11\x00?\x00\x37\x00\xff\xd9'
        with open(avatar_file, "wb") as f:
            f.write(mock_jpg)
        return f"{request.base_url}assets/avatars/{employee_id}.jpg"

    coverage = get_biometric_coverage(employee_id)
    for machine in coverage:
        if machine.get("registered") and machine.get("has_face") and machine.get("status") == "Online":
            ip = machine["ip"]
            photo_base64, status = get_user_photo_from_machine(ip, employee_id)
            if status == "Success" and photo_base64:
                try:
                    img_data = base64.b64decode(photo_base64)
                    with open(avatar_file, "wb") as f:
                        f.write(img_data)
                    return f"{request.base_url}assets/avatars/{employee_id}.jpg"
                except Exception as e:
                    logger.error(f"Failed to decode and save photo for {employee_id}: {e}")
                    
    return ""


@router.post("/card-print-btxml", response_model=CardPrintBtxmlOut)
def generate_card_print_btxml(
    payload: CardPrintRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    employee_ids = payload.employee_ids
    print("PAYLOAD IDs:", employee_ids)
    all_db = db.query(EmployeeLocalRegistry).all()
    print("ALL REGISTRY IN DB:", [(e.employee_id, e.emp_name) for e in all_db])
    if not employee_ids:
        raise HTTPException(status_code=400, detail="No employee IDs provided")
    if len(employee_ids) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 employee IDs allowed")
        
    # Fetch employees
    employees = db.query(EmployeeLocalRegistry).filter(
        EmployeeLocalRegistry.employee_id.in_(employee_ids)
    ).all()
    print("MATCHED EMPLOYEES:", [e.employee_id for e in employees])

    
    # Map employees by ID to preserve the order in payload
    emp_map = {emp.employee_id: emp for emp in employees}
    
    # Generate 6 slots of data
    xml_substrings = []
    for i in range(6):
        idx = i + 1
        if i < len(employee_ids):
            emp_id = employee_ids[i]
            emp = emp_map.get(emp_id)
            if emp:
                emp_name = emp.emp_name or ""
                dept = emp.department or ""
                group = emp.group_name or ""
                # Get or cache photo URL
                photo_url = get_or_cache_employee_photo(emp_id, request, db)
            else:
                emp_name = ""
                dept = ""
                group = ""
                photo_url = ""
                emp_id = ""
        else:
            emp_id = ""
            emp_name = ""
            dept = ""
            group = ""
            photo_url = ""
            
        xml_substrings.append(f'      <NamedSubString Name="id{idx}"><Value>{emp_id}</Value></NamedSubString>')
        xml_substrings.append(f'      <NamedSubString Name="name{idx}"><Value>{emp_name}</Value></NamedSubString>')
        xml_substrings.append(f'      <NamedSubString Name="dept{idx}"><Value>{dept}</Value></NamedSubString>')
        xml_substrings.append(f'      <NamedSubString Name="group{idx}"><Value>{group}</Value></NamedSubString>')
        xml_substrings.append(f'      <NamedSubString Name="image{idx}"><Value>{photo_url}</Value></NamedSubString>')
        
    substrings_str = "\n".join(xml_substrings)
    
    btxml = f"""<XMLScript Version="2.0">
  <Command Name="PrintCards">
    <Print>
      <Format>C:\\templates\\employee_card.btw</Format>
      <Printer>Default</Printer>
{substrings_str}
    </Print>
  </Command>
</XMLScript>"""
    
    return CardPrintBtxmlOut(btxml=btxml)


