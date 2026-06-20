from typing import Optional
from sqlalchemy.orm import Session
from database import EmployeeLocalRegistry, EmployeeMetadata, AttendanceLog, SessionLocal
from config import DEMO_MODE
from shared.hardware import get_machine_list

if not DEMO_MODE:
    from features.machines.service import delete_user_from_machine
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import logging
import io
import openpyxl
from openpyxl.cell import MergedCell
from sqlalchemy import func
from .registry_service import filter_registry_by_employee_search, reconcile_employee_local_registry

logger = logging.getLogger(__name__)

def update_registry(db: Session):
    try:
        reconcile_employee_local_registry(db)
    except Exception as e:
        logger.error(f"Error updating registry: {e}")
        db.rollback()
        raise

def delete_user_from_hardware(employee_id: str):
    """
    Deletes user ONLY from hardware, does not delete from DB.
    Uses ThreadPoolExecutor for parallel processing.
    """
    ips = get_machine_list()
    results = {}

    with ThreadPoolExecutor(max_workers=max(1, len(ips))) as executor:
        future_to_ip = {executor.submit(delete_user_from_machine, ip, employee_id): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                results[ip] = result
            except Exception as e:
                results[ip] = f"Error: {str(e)}"
    return results

def update_employee_info(employee_id: str, db_name: str, db: Session):
    """
    Updates user info in EmployeeLocalRegistry and EmployeeMetadata.
    """
    # 1. Update EmployeeLocalRegistry
    registry_entry = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == employee_id).first()
    if registry_entry:
        registry_entry.emp_name = db_name  # type: ignore[assignment]

    # 2. Update EmployeeMetadata
    meta_entry = db.query(EmployeeMetadata).filter(EmployeeMetadata.employee_id == employee_id).first()
    if meta_entry:
        meta_entry.emp_name = db_name  # type: ignore[assignment]

    db.commit()

    return {"status": "success", "message": "Updated in DB"}

def export_employees_to_excel(db: Session, search: Optional[str] = None, source_status: Optional[str] = None):
    query = db.query(EmployeeLocalRegistry)

    query = filter_registry_by_employee_search(query, db, search)

    if source_status:
        query = query.filter(EmployeeLocalRegistry.source_status == source_status)

    # Hanvon IDs can exceed SQL Server INT range, so do not cast employee_id.
    query = query.order_by(EmployeeLocalRegistry.employee_id.asc())
    employees = query.all()

    # Lấy thông tin chấm công gần nhất cho mỗi nhân viên
    latest_logs = db.query(
        AttendanceLog.employee_id,
        func.max(AttendanceLog.attendance_time).label('last_time')
    ).group_by(AttendanceLog.employee_id).all()
    latest_log_dict = {log.employee_id: log.last_time for log in latest_logs}

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Employees"

    headers = [
        "Mã NV (Máy CC)", "Mã NV (Đầy đủ)", "Họ và Tên", "Phòng Ban",
        "Nhóm / Chuyền", "Ngày vào làm", "Ca làm việc", "Nguồn dữ liệu", "Lần chấm công gần nhất"
    ]
    ws.append(headers)

    for emp in employees:
        last_time = latest_log_dict.get(emp.employee_id)
        ws.append([
            emp.employee_id,
            emp.full_emp_id or "",
            emp.emp_name or "",
            emp.department or "",
            emp.group_name or "",
            (emp.start_date if emp.start_date and emp.start_date.year > 1970 else ""),
            emp.shift or "",
            emp.source_status or "",
            last_time if last_time else ""
        ])

        # Định dạng lại cột Ngày (cột 6) và cột Thời gian (cột 9) theo chuẩn Date/Time của Excel
        current_row = ws.max_row
        if emp.start_date:
            ws.cell(row=current_row, column=6).number_format = 'yyyy-mm-dd'
        if last_time:
            ws.cell(row=current_row, column=9).number_format = 'yyyy-mm-dd hh:mm:ss'

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        first_cell = col[0]
        if isinstance(first_cell, MergedCell):
            continue
        col_letter = first_cell.column_letter
        for cell in col:
            if isinstance(cell, MergedCell):
                continue
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[col_letter].width = adjusted_width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# --- Bulk Push Hardware Features ---
import threading
from features.hanvon.client import HanvonClient
from config import config

bulk_push_status = {
    "is_running": False,
    "employee_ids": [],
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {},
    "missing_employees": []
}

bulk_push_lock = threading.Lock()

def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def run_bulk_push_on_machines(employee_ids: list, target_ips: list):
    global bulk_push_status
    with bulk_push_lock:
        if bulk_push_status["is_running"]:
            return
        bulk_push_status.update({
            "is_running": True,
            "employee_ids": employee_ids,
            "total_machines": len(target_ips),
            "processed_count": 0,
            "current_ip": "Initializing...",
            "results": {},
            "missing_employees": []
        })

    db = SessionLocal()
    existing_map = {}
    missing_employees = []
    
    try:
        for emp_id in employee_ids:
            emp = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == emp_id).first()
            if emp:
                role = "employee"
                if emp.privilege in (3, 14):
                    role = "admin"
                existing_map[emp_id] = {
                    "name": emp.emp_name or emp_id,
                    "role": role,
                    "db_privilege": emp.privilege
                }
            else:
                missing_employees.append(emp_id)
    except Exception as e:
        logger.error(f"Error querying registry DB in bulk push: {e}")
    finally:
        db.close()

    with bulk_push_lock:
        bulk_push_status["missing_employees"] = missing_employees

    face_source_map = {}
    
    if not DEMO_MODE:
        # Check all machines to map registered faces
        all_machines = get_machine_list()
        
        def get_face_coverage(ip):
            try:
                with HanvonClient(
                    ip,
                    port=config.HANVON_PORT,
                    secret_key=config.HANVON_SECRET_KEY,
                    timeout=5,
                ) as client:
                    ids, face_ids = client.get_employee_ids()
                    return ip, ids, face_ids
            except Exception as e:
                logger.warning(f"Error checking machine {ip} for face coverage map: {e}")
                return ip, [], set()

        with ThreadPoolExecutor(max_workers=max(1, len(all_machines))) as executor:
            futures = [executor.submit(get_face_coverage, ip) for ip in all_machines]
            for future in concurrent.futures.as_completed(futures):
                ip, ids, face_ids = future.result()
                for emp_id in existing_map:
                    if emp_id in ids:
                        has_face = emp_id in face_ids
                        if emp_id not in face_source_map or (has_face and not face_source_map[emp_id]["has_face"]):
                            face_source_map[emp_id] = {"ip": ip, "has_face": has_face}
                            
    employee_details = {}
    
    for emp_id in employee_ids:
        if emp_id in existing_map:
            name = existing_map[emp_id]["name"]
            role = existing_map[emp_id]["role"]
        else:
            name = emp_id
            role = "employee"
            
        employee_details[emp_id] = {
            "employee_id": emp_id,
            "name": name,
            "role": role,
            "photo_base64": "",
            "face_data": [],
            "password": "123456",
            "authority": 2
        }

    if not DEMO_MODE:
        source_groups = {}
        for emp_id, source in face_source_map.items():
            if source["has_face"]:
                source_groups.setdefault(source["ip"], []).append(emp_id)
                
        for sip, ids_to_fetch in source_groups.items():
            try:
                with HanvonClient(
                    sip,
                    port=config.HANVON_PORT,
                    secret_key=config.HANVON_SECRET_KEY,
                    timeout=10,
                ) as client:
                    for emp_id in ids_to_fetch:
                        try:
                            if existing_map[emp_id]["role"] == "admin":
                                try:
                                    mgr = client.get_manager(emp_id)
                                    employee_details[emp_id]["photo_base64"] = mgr.get("capturejpg") or ""
                                    employee_details[emp_id]["password"] = mgr.get("password") or "123456"
                                    employee_details[emp_id]["authority"] = _to_int(mgr.get("authority"), 2)
                                except Exception:
                                    emp_detail = client.get_employee(emp_id)
                                    employee_details[emp_id]["photo_base64"] = emp_detail.get("capturejpg") or ""
                                    employee_details[emp_id]["face_data"] = emp_detail.get("face_data") or []
                            else:
                                emp_detail = client.get_employee(emp_id)
                                employee_details[emp_id]["photo_base64"] = emp_detail.get("capturejpg") or ""
                                employee_details[emp_id]["face_data"] = emp_detail.get("face_data") or []
                        except Exception as e:
                            logger.warning(f"Error fetching biometric detail for {emp_id} from {sip}: {e}")
            except Exception as e:
                logger.warning(f"Failed to connect to source machine {sip} to fetch biometrics: {e}")

    def push_to_machine(ip):
        with bulk_push_lock:
            bulk_push_status["current_ip"] = ip
            
        success_count = 0
        details = {}
        
        if DEMO_MODE:
            import time
            time.sleep(1.5)
            for emp_id in employee_ids:
                details[emp_id] = "Success"
                success_count += 1
            return success_count, "Success", details
            
        try:
            with HanvonClient(
                ip,
                port=config.HANVON_PORT,
                secret_key=config.HANVON_SECRET_KEY,
                timeout=15,
            ) as client:
                for emp_id in employee_ids:
                    u = employee_details[emp_id]
                    try:
                        if u["role"] in ("admin", "super_admin"):
                            if not u["photo_base64"]:
                                logger.warning(f"No photo found for admin {emp_id}, falling back to standard employee registration.")
                                client.set_employee(
                                    employee_id=emp_id,
                                    name=u["name"],
                                    photo_base64=""
                                )
                                details[emp_id] = "Pushed as normal employee (photo missing for manager)"
                            else:
                                client.set_manager(
                                    manager_id=emp_id,
                                    photo_base64=u["photo_base64"],
                                    password=u["password"],
                                    authority=u["authority"]
                                )
                                details[emp_id] = "Success (Manager)"
                        else:
                            client.set_employee(
                                employee_id=emp_id,
                                name=u["name"],
                                photo_base64=u["photo_base64"],
                                face_data=u["face_data"]
                            )
                            details[emp_id] = "Success"
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to push user {emp_id} to machine {ip}: {e}")
                        details[emp_id] = str(e)
            
            failed = [emp_id for emp_id, st in details.items() if st != "Success" and "Success" not in st]
            status = "Success" if not failed else f"Partial failure: {len(failed)} errors"
            return success_count, status, details
        except Exception as e:
            logger.error(f"Error during bulk push to machine {ip}: {e}")
            for emp_id in employee_ids:
                details[emp_id] = f"Connection error: {str(e)}"
            return 0, f"Connection error: {str(e)}", details

    results = {}
    with ThreadPoolExecutor(max_workers=max(1, len(target_ips))) as executor:
        future_to_ip = {executor.submit(push_to_machine, ip): ip for ip in target_ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                success_count, status, details = future.result()
                results[ip] = {"pushed": success_count, "status": status, "details": details}
            except Exception as e:
                results[ip] = {"pushed": 0, "status": f"Error: {str(e)}", "details": {}}
                
            with bulk_push_lock:
                bulk_push_status["processed_count"] += 1
                bulk_push_status["results"][ip] = results[ip]

    with bulk_push_lock:
        bulk_push_status["current_ip"] = "Done"
        bulk_push_status["is_running"] = False

