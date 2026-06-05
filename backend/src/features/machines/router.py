from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, cast, Dict, Any
from datetime import datetime
from database import get_db, EmployeeMetadata
from config import DEMO_MODE

if not DEMO_MODE:
    from . import service
    from .service import (
        get_machine_list, get_devices_capacity_info, get_users_from_machine,
        add_user_to_machine, delete_user_from_machine, bulk_delete_users_from_machine,
        update_user_name_all_machines, download_fingerprints_from_machine,
        bulk_download_fingerprints_from_machine, get_biometric_coverage,
        delete_status, delete_user_from_all_machines,
        bulk_delete_status, bulk_delete_users_from_all_machines,
        sync_time_on_machine, bulk_sync_time_all_machines,
        global_sync_status, global_sync_all_fingerprints,
        clear_all_fingerprints_on_machine, clear_fp_status,
        enroll_user_remote, update_machine_tags, get_all_machine_configs,
        push_status, push_fingerprints_to_machines,
        bulk_push_status, bulk_push_fingerprints_to_machines,
        sync_employee_status, sync_employee_to_machines
    )
else:
    # In DEMO_MODE, hardware service is not available
    from shared.hardware import get_machine_list, get_all_machine_configs, update_machine_tags
    import threading
    sync_employee_status: Dict[str, Any] = {
        "is_running": False,
        "employee_id": "",
        "total_machines": 0,
        "processed_count": 0,
        "current_ip": "",
        "results": {}
    }
    sync_employee_status_lock = threading.Lock()

if not DEMO_MODE:
    from .biometric_service import BiometricExportService
from pydantic import BaseModel

class NameUpdate(BaseModel):
    employee_id: str
    new_name: str

class MachineEmployeeCreate(BaseModel):
    employee_id: str
    name: str = ""
    role: str = "employee"          # "employee" | "admin" | "super_admin"
    photo_base64: str = ""          # Optional for employee; REQUIRED for admin/super_admin
    password: str = "123456"        # Manager password (must be unique on device)
    authority: int = 2              # 0 = Super Admin, 2 = Ordinary Admin (manager only)

class MachineEmployeeUpdate(BaseModel):
    name: str = ""
    role: str = "employee"          # "employee" | "admin" | "super_admin"
    photo_base64: str = ""          # Optional; existing machine photo is preserved when omitted
    password: str = ""              # Optional; existing manager password is preserved when omitted

class FingerprintSyncRequest(BaseModel):
    ip: str
    employee_id: str

class BulkDeleteRequest(BaseModel):
    employee_ids: List[str]

class BulkPushRequest(BaseModel):
    employee_ids: List[str]
    target_ips: List[str]

class BulkPushPreviewRequest(BaseModel):
    employee_ids: List[str]

class PushFingerprintsRequest(BaseModel):
    employee_id: str
    target_ips: List[str]

class PrivilegeUpdateRequest(BaseModel):
    privilege: int

class EnrollmentRequest(BaseModel):
    employee_id: str
    finger_index: int = 0

router = APIRouter(prefix="/api/machines", tags=["Machines"])


def _hanvon_not_supported(feature: str):
    raise HTTPException(
        status_code=410,
        detail=f"{feature} is a legacy ZKTeco operation and is not supported after switching machines to Hanvon.",
    )

@router.get("")
def get_machines():
    """List all configured machine IPs."""
    return get_machine_list()

@router.get("/configs")
def get_machines_full_configs():
    """List all machines with their live/canteen tags."""
    return get_all_machine_configs()

@router.get("/capacity")
def get_machines_capacity():
    """Get health and capacity info for all machines."""
    if DEMO_MODE:
        # Return simulated capacity data for demo machines
        configs = get_all_machine_configs()
        return [{
            "ip": c["ip"], 
            "status": "Online",
            "users": 200, "users_cap": 3000, 
            "fingers": 400, "fingers_cap": 3000, 
            "records": 5000, "records_cap": 100000,
            "admins": 2, "admins_cap": 10
        } for c in configs]
    return get_devices_capacity_info()

@router.get("/live-status")
def get_live_machines_status():
    """Get the current connection status of all live monitor threads."""
    if DEMO_MODE:
        from .demo_simulator import demo_simulator
        return demo_simulator.get_status()
    from .live_monitor import live_monitor
    return live_monitor.get_status()

@router.get("/{ip}/employees")
def get_machine_employees(ip: str, db: Session = Depends(get_db)):
    """List employees currently on a specific machine, enriched with DB names."""
    from database import EmployeeLocalRegistry
    
    if DEMO_MODE:
        # In demo mode, return all employees as if they're on every machine
        registry = db.query(EmployeeLocalRegistry).all()
        enriched = []
        for reg in registry:
            emp_id = cast(str, reg.employee_id)
            enriched.append({
                "uid": int(emp_id) if emp_id.isdigit() else 0,
                "user_id": emp_id,
                "name": reg.emp_name or "",
                "privilege": reg.privilege or 0,
                "password": "",
                "group_id": "",
                "card": 0,
                "db_name": reg.emp_name,
                "status": reg.shift if reg.shift else "Unknown",
                "department": reg.department,
                "group_name": reg.group_name,
                "shift": reg.shift,
                "source_status": reg.source_status or "excel_synced",
                "role": "Admin" if reg.privilege == 3 else "User"
            })
        return {"items": enriched, "total": len(enriched), "status": "Success (Demo)"}
    
    users, status = get_users_from_machine(ip)
    if status != "Success" and not users:
        raise HTTPException(status_code=500, detail=status)
    
    # Enrich with Consolidated Registry metadata (Phase 4 table)
    registry_map = {str(r.employee_id): r for r in db.query(EmployeeLocalRegistry).all()}
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

@router.post("/{ip}/employees")
def add_machine_employee(ip: str, req: MachineEmployeeCreate):
    """Add or update an employee or manager on a specific Hanvon machine.

    Role → Hanvon API mapping (per HANVON_PROTOCOL.md §9):
    - "employee"   → SetEmployee (userType="1"), photo optional
    - "admin"      → SetManager (authority=2 = Ordinary Admin), photo REQUIRED
    - "super_admin" → SetManager (authority=0 = Super Admin), photo REQUIRED
    """
    employee_id = req.employee_id.strip()
    if not employee_id:
        raise HTTPException(status_code=422, detail="employee_id is required")

    valid_roles = {"employee", "admin", "super_admin"}
    if req.role not in valid_roles:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{req.role}'. Must be one of: {', '.join(sorted(valid_roles))}",
        )

    # Managers require a real photo per device protocol §8.3
    if req.role in ("admin", "super_admin") and not req.photo_base64.strip():
        raise HTTPException(
            status_code=422,
            detail="A real JPEG photo (base64) is required to register a manager on a Hanvon device.",
        )

    status = add_user_to_machine(
        ip=ip,
        employee_id=employee_id,
        name=req.name,
        role=req.role,
        photo_base64=req.photo_base64,
        password=req.password,
        authority=req.authority,
    )
    if status != "Success":
        raise HTTPException(status_code=500, detail=status)
    return {"status": status, "employee_id": employee_id}

@router.put("/{ip}/employees/{employee_id}")
def update_machine_employee(ip: str, employee_id: str, req: MachineEmployeeUpdate):
    """Update one employee/manager identity on a specific Hanvon machine."""
    employee_id = employee_id.strip()
    if not employee_id:
        raise HTTPException(status_code=422, detail="employee_id is required")

    valid_roles = {"employee", "admin", "super_admin"}
    if req.role not in valid_roles:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{req.role}'. Must be one of: {', '.join(sorted(valid_roles))}",
        )

    if DEMO_MODE:
        return {"status": "Success (Demo)", "employee_id": employee_id}

    status = service.update_user_on_machine(
        ip=ip,
        employee_id=employee_id,
        name=req.name,
        role=req.role,
        photo_base64=req.photo_base64,
        password=req.password,
    )
    if status != "Success":
        raise HTTPException(status_code=500, detail=status)
    return {"status": status, "employee_id": employee_id}

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
    _hanvon_not_supported("Machine-side name update")

@router.post("/sync-fingerprints")
def sync_fingerprints(data: FingerprintSyncRequest):
    """Pull fingerprints for a single user from a machine to DB."""
    _hanvon_not_supported("Fingerprint sync")

@router.post("/{ip}/sync-all-fingerprints")
def sync_all_machine_fingerprints(ip: str):
    """Pull all fingerprints from a machine to DB."""
    _hanvon_not_supported("Fingerprint sync")

@router.get("/export-fingerprints")
def export_machine_fingerprints(ip: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Export DB fingerprints to Excel."""
    _hanvon_not_supported("Fingerprint export")

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
    _hanvon_not_supported("Fingerprint push")

@router.get("/push-status")
def get_push_status():
    """Poll status of the fingerprint push operation."""
    return push_status

@router.post("/bulk-push-fingerprints")
def trigger_bulk_push_fingerprints(data: BulkPushRequest, background_tasks: BackgroundTasks):
    """Start background bulk fingerprint pushing."""
    _hanvon_not_supported("Fingerprint push")

@router.get("/bulk-push-status")
def get_bulk_push_status():
    """Poll status of the bulk fingerprint push operation."""
    return bulk_push_status

@router.post("/bulk-push-preview")
def preview_bulk_push_endpoint(data: BulkPushPreviewRequest):
    """Preview the data before pushing."""
    _hanvon_not_supported("Fingerprint push preview")

@router.post("/sync-all-fingerprints-global")
def trigger_global_sync_all_fingerprints(background_tasks: BackgroundTasks):
    """Start background process to sync all fingerprints from all machines to DB."""
    _hanvon_not_supported("Fingerprint sync")

@router.get("/sync-all-fingerprints-global/status")
def get_global_sync_status():
    """Get status of the global sync operation."""
    return global_sync_status

@router.post("/{ip}/clear-fingerprints")
def clear_machine_fingerprints(ip: str, background_tasks: BackgroundTasks):
    """Clear all user data and fingerprints on a specific machine, keeping logs."""
    _hanvon_not_supported("Fingerprint clear")

@router.get("/clear-fingerprints-status")
def get_clear_fingerprints_status():
    """Get status of the clear fingerprints operation."""
    return clear_fp_status

@router.post("/sync-time-all")
def sync_all_machines_time():
    """Sync time for all connected machines."""
    _hanvon_not_supported("Time sync")

@router.post("/{ip}/users/{employee_id}/privilege")
def update_user_privilege_endpoint(ip: str, employee_id: str, req: PrivilegeUpdateRequest):
    """Sets a user's privilege on a specific machine and updates local DB."""
    _hanvon_not_supported("Machine-side privilege update")

@router.post("/{ip}/enroll")
async def enroll_machine_user(ip: str, request: EnrollmentRequest, background_tasks: BackgroundTasks):
    """
    Kích hoạt chế độ đăng ký vân tay từ xa (chạy ngầm).
    """
    _hanvon_not_supported("Remote fingerprint enrollment")

@router.get("/{ip}/enroll/status")
async def get_enroll_status(ip: str):
    """
    Lấy trạng thái tiến trình đăng ký vân tay.
    """
    _hanvon_not_supported("Remote fingerprint enrollment")

@router.post("/{ip}/enroll/cancel")
async def cancel_enroll(ip: str):
    """
    Hủy bỏ tiến trình đăng ký vân tay trên máy.
    """
    _hanvon_not_supported("Remote fingerprint enrollment")

class MachineConfigUpdate(BaseModel):
    is_live: bool
    is_canteen: bool

@router.post("/{ip}/config")
def update_machine_cfg(ip: str, req: MachineConfigUpdate):
    """Update machine configuration (live/canteen tags)."""
    success, msg = update_machine_tags(ip, req.is_live, req.is_canteen)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "success"}

@router.post("/{ip}/reconnect")
def reconnect_machine_endpoint(ip: str):
    """Force reconnect a machine's live monitoring thread."""
    if DEMO_MODE:
        return {"status": "success", "message": "Demo mode: simulated reconnect"}
    from .live_monitor import live_monitor
    success, msg = live_monitor.reconnect_machine(ip)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "success", "message": msg}


class SyncEmployeeRequest(BaseModel):
    source_ip: str
    employee_id: str
    employee_name: str
    target_ips: List[str]

@router.post("/sync-employee")
def sync_employee_endpoint(req: SyncEmployeeRequest, background_tasks: BackgroundTasks):
    """
    Kích hoạt tiến trình đồng bộ nhân viên sang các máy khác (chạy ngầm).
    """
    if DEMO_MODE:
        import time
        with sync_employee_status_lock:
            if sync_employee_status["is_running"]:
                raise HTTPException(status_code=400, detail="Sync already running")
            sync_employee_status.update({
                "is_running": True,
                "employee_id": req.employee_id,
                "total_machines": len(req.target_ips),
                "processed_count": 0,
                "current_ip": "",
                "results": {}
            })
        def run_demo():
            for ip in req.target_ips:
                with sync_employee_status_lock:
                    sync_employee_status["current_ip"] = ip
                time.sleep(1.0)
                with sync_employee_status_lock:
                    sync_employee_status["results"][ip] = "Success"
                    sync_employee_status["processed_count"] = int(sync_employee_status["processed_count"]) + 1
            with sync_employee_status_lock:
                sync_employee_status["is_running"] = False
        
        background_tasks.add_task(run_demo)
        return {"status": "Success"}

    background_tasks.add_task(
        sync_employee_to_machines,
        req.source_ip,
        req.employee_id,
        req.employee_name,
        req.target_ips
    )
    return {"status": "Success"}

@router.get("/sync-employee/status")
def get_sync_employee_status_endpoint():
    """
    Lấy trạng thái của tiến trình đồng bộ nhân viên.
    """
    if DEMO_MODE:
        return sync_employee_status
    return sync_employee_status


