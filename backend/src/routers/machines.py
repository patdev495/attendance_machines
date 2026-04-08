from fastapi import APIRouter, Query, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db, EmployeeMetadata
from ..sync_service import (
    sync_all_machines, get_machine_list, sync_status, 
    sync_employees_from_excel, delete_user_from_all_machines, 
    get_users_from_machine, delete_user_from_machine, bulk_delete_users_from_machine,
    excel_sync_status, delete_status, get_devices_capacity_info,
    update_user_name_all_machines, download_fingerprints_from_machine,
    bulk_download_fingerprints_from_machine, get_biometric_coverage
)
from ..services.biometric_export import BiometricExportService
from pydantic import BaseModel

class NameUpdate(BaseModel):
    employee_id: str
    new_name: str

class FingerprintSyncRequest(BaseModel):
    ip: str
    employee_id: str

class BulkDeleteRequest(BaseModel):
    employee_ids: List[str]

router = APIRouter(prefix="/api", tags=["Machines"])

@router.post("/devices/update_name")
def update_employee_name(data: NameUpdate):
    return update_user_name_all_machines(data.employee_id, data.new_name)

@router.post("/devices/sync_fingerprints")
def sync_fingerprints(data: FingerprintSyncRequest):
    count, status = download_fingerprints_from_machine(data.ip, data.employee_id)
    return {"count": count, "status": status}

@router.get("/machines")
def get_machines():
    return get_machine_list()

@router.post("/sync")
def start_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_all_machines)
    return {"status": "Started"}

@router.get("/sync/status")
def get_sync_status():
    return sync_status

@router.post("/sync/excel")
async def upload_excel(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    content = await file.read()
    import io
    background_tasks.add_task(sync_employees_from_excel, file_bytes=io.BytesIO(content))
    return {"status": "Started"}

@router.get("/sync/excel/status")
def get_excel_sync_status():
    return excel_sync_status

@router.get("/devices/{ip}/employees")
def get_device_employees(ip: str, page: int = 1, size: int = 5000, db: Session = Depends(get_db)):
    users, status = get_users_from_machine(ip)
    if status != "Success" and not users:
        raise HTTPException(status_code=500, detail=status)
    
    # Merge with DB metadata
    # 1. Get all metadata
    metadata_map = {m.employee_id: m for m in db.query(EmployeeMetadata).all()}
    
    # 2. Enrich user objects
    enriched_users = []
    for u in users:
        meta = metadata_map.get(str(u['user_id']))
        enriched_users.append({
            **u,
            "db_name": meta.emp_name if meta else None,
            "status": meta.status if meta else "Unknown",
            "department": meta.department if meta else None,
            "shift": meta.shift if meta else None
        })
    
    return {
        "items": enriched_users,
        "status": status,
        "total": len(enriched_users)
    }

@router.get("/devices/capacity")
def get_devices_capacity():
    return get_devices_capacity_info()

@router.delete("/devices/{ip}/employees/{employee_id}")
def delete_single_device_employee(ip: str, employee_id: str):
    return delete_user_from_machine(ip, employee_id)

@router.post("/devices/{ip}/employees/bulk_delete")
def bulk_delete_device_employees(ip: str, req: BulkDeleteRequest):
    count, status = bulk_delete_users_from_machine(ip, req.employee_ids)
    print(f"Bulk Delete Request for {ip}, received payload: {req.employee_ids}, count: {count}")
    if status != "Success":
        raise HTTPException(status_code=500, detail=status)
    return {"count": count, "status": status}

@router.delete("/devices/delete_global/{employee_id}")
def delete_global_employee(employee_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(delete_user_from_all_machines, employee_id)
    return {"status": "Started"}

@router.get("/devices/delete_status/{employee_id}")
def get_delete_status(employee_id: str):
    # This assumes delete_status uses employee_id as key
    if employee_id in delete_status:
        return delete_status[employee_id]
    return {"status": "Not found"}

@router.get("/devices/employees/all")
def get_all_device_employees():
    # Helper to see who is actually on the machines
    machines = get_machine_list()
    all_users = []
    for m in machines:
        users = get_users_from_machine(m['ip'])
        if isinstance(users, list):
            for u in users:
                u['machine_name'] = m['name']
                u['machine_ip'] = m['ip']
                all_users.append(u)
    return all_users

@router.post("/devices/{ip}/sync_all_fingerprints")
def sync_all_fingerprints(ip: str):
    count, status = bulk_download_fingerprints_from_machine(ip)
    if status != "Success":
        raise HTTPException(status_code=500, detail=status)
    return {"count": count, "status": status}

@router.get("/employees/{employee_id}/biometric_coverage")
def get_employee_biometric_coverage(employee_id: str):
    return get_biometric_coverage(employee_id)

@router.get("/devices/export-fingerprints")
def export_fingerprints(ip: Optional[str] = Query(None), db: Session = Depends(get_db)):
    output = BiometricExportService.generate_excel_from_db(db, ip=ip)
    label = f"Device_{ip}" if ip else "All"
    filename = f"Fingerprints_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
