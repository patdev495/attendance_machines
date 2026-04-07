from fastapi import APIRouter, Query, UploadFile, File
from typing import List, Optional
from ..sync_service import (
    sync_all_machines, get_machine_list, sync_status, 
    sync_employees_from_excel, delete_user_from_all_machines, 
    get_users_from_machine, delete_user_from_machine,
    excel_sync_status, delete_status, get_devices_capacity_info
)

router = APIRouter(prefix="/api", tags=["Machines"])

@router.get("/machines")
def get_machines():
    return get_machine_list()

@router.post("/sync/all")
def start_sync():
    return sync_all_machines()

@router.get("/sync/status")
def get_sync_status():
    return sync_status

@router.post("/sync/excel")
def upload_excel(file: UploadFile = File(...)):
    return sync_employees_from_excel(file)

@router.get("/sync/excel/status")
def get_excel_sync_status():
    return excel_sync_status

@router.get("/devices/capacity")
def get_devices_capacity():
    return get_devices_capacity_info()

@router.delete("/devices/delete_employee/{employee_id}")
def delete_device_employee(employee_id: str):
    return delete_user_from_all_machines(employee_id)

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
