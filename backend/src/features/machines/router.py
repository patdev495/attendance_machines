from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db, EmployeeMetadata
from .service import (
    get_machine_list, get_devices_capacity_info, get_users_from_machine,
    delete_user_from_machine, bulk_delete_users_from_machine,
    update_user_name_all_machines, download_fingerprints_from_machine,
    bulk_download_fingerprints_from_machine, get_biometric_coverage,
    delete_status, delete_user_from_all_machines,
    bulk_delete_status, bulk_delete_users_from_all_machines
)
from .biometric_service import BiometricExportService
from pydantic import BaseModel

class NameUpdate(BaseModel):
    employee_id: str
    new_name: str

class FingerprintSyncRequest(BaseModel):
    ip: str
    employee_id: str

class BulkDeleteRequest(BaseModel):
    employee_ids: List[str]

class PushFingerprintsRequest(BaseModel):
    employee_id: str
    target_ips: List[str]

router = APIRouter(prefix="/api/machines", tags=["Machines"])

@router.get("")
def get_machines():
    """List all configured machine IPs."""
    return get_machine_list()

@router.get("/capacity")
def get_machines_capacity():
    """Get health and capacity info for all machines."""
    return get_devices_capacity_info()

@router.get("/{ip}/employees")
def get_machine_employees(ip: str, db: Session = Depends(get_db)):
    """List employees currently on a specific machine, enriched with DB names."""
    users, status = get_users_from_machine(ip)
    if status != "Success" and not users:
        raise HTTPException(status_code=500, detail=status)
    
    # Enrich with Consolidated Registry metadata (Phase 4 table)
    from database import EmployeeLocalRegistry
    registry_map = {r.employee_id: r for r in db.query(EmployeeLocalRegistry).all()}
    enriched = []
    for u in users:
        emp_id = str(u['user_id'])
        reg = registry_map.get(emp_id)
        
        # Consistent status logic: map shift to display status if available
        # This will be used by the frontend to render badges
        enriched.append({
            **u,
            "db_name": reg.emp_name if reg else None,
            "status": reg.shift if reg and reg.shift else "Unknown",
            "department": reg.department if reg else None,
            "group_name": reg.group_name if reg else None,
            "shift": reg.shift if reg else None,
            "source_status": reg.source_status if reg else "machine_only"
        })
    return {"items": enriched, "total": len(enriched), "status": status}

@router.delete("/{ip}/employees/{employee_id}")
def delete_machine_employee(ip: str, employee_id: str):
    """Delete a single employee from a machine."""
    return delete_user_from_machine(ip, employee_id)

@router.post("/{ip}/employees/bulk-delete")
def bulk_delete_machine_employees(ip: str, req: BulkDeleteRequest):
    """Delete multiple employees from a machine."""
    count, status = bulk_delete_users_from_machine(ip, req.employee_ids)
    if status != "Success":
        raise HTTPException(status_code=500, detail=status)
    return {"count": count, "status": status}

@router.post("/update-name")
def update_machine_name(data: NameUpdate):
    """Global name update across all machines and DB."""
    return update_user_name_all_machines(data.employee_id, data.new_name)

@router.post("/sync-fingerprints")
def sync_fingerprints(data: FingerprintSyncRequest):
    """Pull fingerprints for a single user from a machine to DB."""
    count, status = download_fingerprints_from_machine(data.ip, data.employee_id)
    return {"count": count, "status": status}

@router.post("/{ip}/sync-all-fingerprints")
def sync_all_machine_fingerprints(ip: str):
    """Pull all fingerprints from a machine to DB."""
    count, status = bulk_download_fingerprints_from_machine(ip)
    if status != "Success":
        raise HTTPException(status_code=500, detail=status)
    return {"count": count, "status": status}

@router.get("/export-fingerprints")
def export_machine_fingerprints(ip: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Export DB fingerprints to Excel."""
    output = BiometricExportService.generate_excel_from_db(db, ip=ip)
    label = f"Device_{ip}" if ip else "All"
    filename = f"Fingerprints_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Status polling for background tasks
@router.get("/delete-status/{employee_id}")
def get_global_delete_status(employee_id: str):
    """Check status of global machine deletion."""
    if delete_status.get("employee_id") == employee_id:
        return delete_status
    return {"status": "Not running or different employee"}

@router.post("/bulk-delete-global")
def trigger_bulk_global_delete(req: BulkDeleteRequest, background_tasks: BackgroundTasks):
    """Start background global deletion for multiple employees."""
    if bulk_delete_status["is_running"]:
        raise HTTPException(status_code=400, detail="Another bulk operation is in progress")
    
    background_tasks.add_task(bulk_delete_users_from_all_machines, req.employee_ids)
    return {"status": "Started", "count": len(req.employee_ids)}

@router.get("/bulk-delete-status")
def get_bulk_global_delete_status():
    """Poll status of the bulk global deletion."""
    return bulk_delete_status

@router.post("/push-fingerprints")
def trigger_push_fingerprints(data: PushFingerprintsRequest, background_tasks: BackgroundTasks):
    """Start background global fingerprint pushing."""
    from .service import push_status, push_fingerprints_to_machines
    if push_status["is_running"]:
        raise HTTPException(status_code=400, detail="Another push operation is in progress")
    
    background_tasks.add_task(push_fingerprints_to_machines, data.employee_id, data.target_ips)
    return {"status": "Started", "count": len(data.target_ips)}

@router.get("/push-status")
def get_push_status():
    """Poll status of the fingerprint push operation."""
    from .service import push_status
    return push_status
