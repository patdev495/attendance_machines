from config import config, DEMO_MODE

from database import SessionLocal, EmployeeMetadata
from features.hanvon.client import HanvonClient
from shared.hardware import get_machine_list, update_machine_tags, get_all_machine_configs, delete_machine_config
import logging
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _unsupported_hanvon_operation(operation: str):
    message = f"{operation} is not supported for Hanvon devices"
    logger.warning(message)
    return message


# State for machine operations (deletion, etc.)
delete_status = {
    "is_running": False,
    "employee_id": None,
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {}
}

status_lock = threading.Lock()

def get_devices_capacity_info():
    """Checks Hanvon capacity for all configured machines."""
    machines = get_all_machine_configs()
    results = []
    for machine in machines:
        ip = machine["ip"] if isinstance(machine, dict) else str(machine)
        try:
            with HanvonClient(
                ip,
                port=config.HANVON_PORT,
                secret_key=config.HANVON_SECRET_KEY,
                timeout=5,
            ) as client:
                info = client.get_device_info()

            users = _to_int(info.get("real_faceregist"))
            users_cap = _to_int(info.get("max_faceregist"))
            records = _to_int(info.get("real_facerecord"))
            records_cap = _to_int(info.get("max_facerecord"))
            admins = _to_int(info.get("managernum"))
            admins_cap = _to_int(info.get("max_managernum"), 10)
            results.append({
                "ip": ip,
                "status": "Online",
                "protocol": "hanvon",
                "model": info.get("model") or info.get("type") or "",
                "sn": info.get("sn") or "",
                "firmware": info.get("edition") or "",
                "device_time": info.get("time") or "",
                "users": users,
                "users_cap": users_cap,
                "fingers": users,
                "fingers_cap": users_cap,
                "records": records,
                "records_cap": records_cap,
                "admins": admins,
                "admins_cap": admins_cap,
            })
        except Exception as e:
            results.append({
                "ip": ip,
                "status": "Offline",
                "protocol": "hanvon",
                "users": 0,
                "users_cap": 0,
                "fingers": 0,
                "fingers_cap": 0,
                "records": 0,
                "records_cap": 0,
                "admins": 0,
                "admins_cap": 0,
                "error": str(e),
            })
    return results

def get_users_from_machine(ip: str):
    """Fetches all Hanvon employee IDs and manager IDs from a specific machine."""
    try:
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=15,
        ) as client:
            employee_ids, face_ids = client.get_employee_ids()
            try:
                manager_ids = client.get_manager_ids()
            except Exception as e:
                logger.warning(f"Error fetching manager IDs from machine {ip}: {e}")
                manager_ids = []

            user_list = []
            uid_counter = 1

            # Map normal employees
            for employee_id in employee_ids:
                user_list.append({
                    "uid": uid_counter,
                    "user_id": employee_id,
                    "name": "",
                    "privilege": 0,
                    "password": "",
                    "group_id": "",
                    "card": 0,
                    "has_face": employee_id in face_ids,
                    "role": "User",
                })
                uid_counter += 1

            # Map managers/admins
            for manager_id in manager_ids:
                authority = 2  # default ordinary admin
                has_face = False
                try:
                    manager_detail = client.get_manager(manager_id)
                    authority = _to_int(manager_detail.get("authority"), 2)
                    has_face = bool(str(manager_detail.get("capturejpg") or "").strip())
                except Exception as e:
                    logger.warning(f"Error fetching manager detail for {manager_id} from {ip}: {e}")

                role_name = "Super Admin" if authority == 0 else "Admin"

                # Avoid duplicate entries if any ID is present in both
                existing = next((u for u in user_list if u["user_id"] == manager_id), None)
                if existing:
                    existing["role"] = role_name
                    existing["privilege"] = 3
                    existing["has_face"] = existing["has_face"] or has_face
                else:
                    user_list.append({
                        "uid": uid_counter,
                        "user_id": manager_id,
                        "name": "",
                        "privilege": 3,
                        "password": "",
                        "group_id": "",
                        "card": 0,
                        "has_face": has_face,
                        "role": role_name,
                    })
                    uid_counter += 1

        return user_list, "Success"
    except Exception as e:
        logger.error(f"Error fetching users from machine {ip}: {e}")
        return [], str(e)

def add_user_to_machine(
    ip: str,
    employee_id: str,
    name: str = "",
    role: str = "employee",
    photo_base64: str = "",
    password: str = "123456",
    authority: int = 2,
):
    """Add or update an employee or manager on a specific Hanvon machine.

    Role routing (per Hanvon protocol §9):
    - "employee"  → SetEmployee (userType="1"), photo optional
    - "admin"     → SetManager  (authority=2 = Ordinary Admin), photo REQUIRED
    - "super_admin" → SetManager (authority=0 = Super Admin), photo REQUIRED
    """
    try:
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=10,
        ) as client:
            if role in ("admin", "super_admin"):
                authority_val = 0 if role == "super_admin" else 2
                client.set_manager(
                    manager_id=employee_id,
                    photo_base64=photo_base64,
                    password=password,
                    authority=authority_val,
                )
            else:
                client.set_employee(employee_id, name, photo_base64=photo_base64)
        return "Success"
    except Exception as e:
        logger.error(f"Error adding user {employee_id} ({role}) to machine {ip}: {e}")
        return str(e)


def update_user_on_machine(
    ip: str,
    employee_id: str,
    name: str = "",
    role: str = "employee",
    photo_base64: str = "",
    password: str = "",
):
    """Update one Hanvon employee/manager while preserving existing biometric data."""
    try:
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=10,
        ) as client:
            employee_ids, _face_ids = client.get_employee_ids()
            manager_ids = client.get_manager_ids()
            is_employee = employee_id in employee_ids
            is_manager = employee_id in manager_ids

            employee_detail: dict[str, Any] = {}
            manager_detail: dict[str, Any] = {}

            if is_employee:
                try:
                    employee_detail = client.get_employee(employee_id)
                except Exception as e:
                    logger.warning(f"Failed to fetch employee detail for {employee_id} from {ip}: {e}")

            if is_manager:
                try:
                    manager_detail = client.get_manager(employee_id)
                except Exception as e:
                    logger.warning(f"Failed to fetch manager detail for {employee_id} from {ip}: {e}")

            if role in ("admin", "super_admin"):
                manager_photo = (
                    photo_base64.strip()
                    or str(manager_detail.get("capturejpg") or "").strip()
                    or str(employee_detail.get("capturejpg") or "").strip()
                )
                if not manager_photo:
                    return "A real JPEG photo is required to update/register a Hanvon manager."

                client.set_manager(
                    manager_id=employee_id,
                    photo_base64=manager_photo,
                    password=(password or manager_detail.get("password") or "123456"),
                    authority=0 if role == "super_admin" else 2,
                )
                return "Success"

            if not is_employee and not is_manager:
                return f"User {employee_id} not found on machine {ip}"

            client.set_employee(
                employee_id=employee_id,
                name=(name or employee_detail.get("name") or ""),
                photo_base64=(photo_base64 or employee_detail.get("capturejpg") or ""),
                face_data=employee_detail.get("face_data") or None,
            )
            return "Success"
    except Exception as e:
        logger.error(f"Error updating user {employee_id} ({role}) on machine {ip}: {e}")
        return str(e)


def get_user_photo_from_machine(ip: str, employee_id: str) -> tuple[str, str]:
    """Fetch the current Hanvon capture photo for one employee/manager."""
    employee_id = employee_id.strip()
    if not employee_id:
        return "", "employee_id is required"

    try:
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=10,
        ) as client:
            employee_ids, _face_ids = client.get_employee_ids()
            manager_ids = client.get_manager_ids()
            is_employee = employee_id in employee_ids
            is_manager = employee_id in manager_ids

            if not is_employee and not is_manager:
                return "", f"User {employee_id} not found on machine {ip}"

            if is_manager:
                try:
                    manager_detail = client.get_manager(employee_id)
                    manager_photo = str(manager_detail.get("capturejpg") or "").strip()
                    if manager_photo:
                        return manager_photo, "Success"
                except Exception as e:
                    logger.warning(f"Failed to fetch manager photo for {employee_id} from {ip}: {e}")

            if is_employee:
                try:
                    employee_detail = client.get_employee(employee_id)
                    return str(employee_detail.get("capturejpg") or "").strip(), "Success"
                except Exception as e:
                    logger.warning(f"Failed to fetch employee photo for {employee_id} from {ip}: {e}")
                    return "", str(e)

            return "", "Success"
    except Exception as e:
        logger.error(f"Error fetching user photo {employee_id} from machine {ip}: {e}")
        return "", str(e)



def delete_user_from_machine(ip: str, employee_id: str):
    """Delete a Hanvon employee and/or manager identity from a specific machine."""
    try:
        actions = []
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=10,
        ) as client:
            employee_ids, _face_ids = client.get_employee_ids()
            manager_ids = client.get_manager_ids()

            if employee_id in employee_ids:
                try:
                    client.delete_employee(employee_id)
                    actions.append("employee deleted")
                except Exception as e:
                    actions.append(f"employee delete failed: {e}")

            if employee_id in manager_ids:
                try:
                    client.delete_manager(employee_id)
                    actions.append("manager deleted")
                except Exception as e:
                    actions.append(f"manager delete failed: {e}")

        if not actions:
            result = "Not found"
        elif any("failed" in action for action in actions):
            result = "; ".join(actions)
        else:
            result = "Success: " + ", ".join(actions)
        with status_lock:
            delete_status["results"][ip] = result
        return result
    except Exception as e:
        logger.error(f"Error deleting user from machine {ip}: {e}")
        msg = f"Error: {str(e)}"
        with status_lock:
            delete_status["results"][ip] = msg
        return msg

def bulk_delete_users_from_machine(ip: str, employee_ids: list):
    """Deletes multiple Hanvon employee/manager identities from a machine in a single connection."""
    deleted_count = 0
    details = {}
    try:
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=15,
        ) as client:
            existing_employee_ids, _face_ids = client.get_employee_ids()
            existing_manager_ids = client.get_manager_ids()
            for emp_id in employee_ids:
                emp_id = str(emp_id)
                actions = []
                try:
                    deleted_any = False
                    if emp_id in existing_employee_ids:
                        client.delete_employee(emp_id)
                        deleted_any = True
                        actions.append("employee deleted")
                    if emp_id in existing_manager_ids:
                        client.delete_manager(emp_id)
                        deleted_any = True
                        actions.append("manager deleted")
                    if deleted_any:
                        deleted_count += 1
                        details[emp_id] = {"status": "Success", "actions": actions}
                    else:
                        details[emp_id] = {"status": "Not found", "actions": []}
                except Exception as e:
                    logger.error(f"Failed to delete {emp_id} from {ip}: {e}")
                    details[emp_id] = {"status": f"Error: {str(e)}", "actions": actions}

        failed = [d for d in details.values() if str(d["status"]).startswith("Error:")]
        status = "Success" if not failed else f"Partial failure: {len(failed)} errors"
        return deleted_count, status, details
    except Exception as e:
        logger.error(f"Error bulk deleting from machine {ip}: {e}")
        return deleted_count, f"Error: {str(e)}", details


def check_user_biometric_on_machine(ip: str, employee_id: str):
    """Checks Hanvon registration, manager role, and face coverage on a machine."""
    try:
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=10,
        ) as client:
            employee_ids, face_ids = client.get_employee_ids()
            manager_ids = client.get_manager_ids()

            is_employee = employee_id in employee_ids
            is_manager = employee_id in manager_ids
            role = "not_registered"

            if is_manager:
                role = "admin"
                manager_has_face = False
                try:
                    manager_detail = client.get_manager(employee_id)
                    manager_has_face = bool(str(manager_detail.get("capturejpg") or "").strip())
                    if _to_int(manager_detail.get("authority"), 2) == 0:
                        role = "super_admin"
                except Exception as e:
                    logger.warning(f"Error fetching manager detail for {employee_id} from {ip}: {e}")
            elif is_employee:
                role = "employee"

            return {
                "ip": ip,
                "status": "Online",
                "registered": is_employee or is_manager,
                "role": role,
                "has_face": manager_has_face if is_manager else employee_id in face_ids,
            }
    except Exception as e:
        logger.error(f"Error checking biometric on {ip}: {e}")
        return {
            "ip": ip,
            "status": "Offline",
            "error": str(e),
            "registered": False,
            "role": "not_registered",
            "has_face": False,
        }

def get_biometric_coverage(employee_id: str):
    """Check across all machines."""
    ips = get_machine_list()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, len(ips))) as executor:
        future_to_ip = {executor.submit(check_user_biometric_on_machine, ip, employee_id): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            results.append(future.result())
    return results

def delete_user_from_all_machines(employee_id: str):
    """Orchestrates deletion across all known hardware."""
    global delete_status
    with status_lock:
        if delete_status["is_running"]: return
        delete_status.update({
            "is_running": True, "employee_id": employee_id,
            "results": {}, "processed_count": 0, "current_ip": ""
        })

    try:
        ips = get_machine_list()
        delete_status["total_machines"] = len(ips)
        for ip in ips:
            with status_lock: delete_status["current_ip"] = ip
            delete_user_from_machine(ip, employee_id)
            with status_lock: delete_status["processed_count"] += 1
    finally:
        with status_lock: delete_status["is_running"] = False

# State for bulk global operations
bulk_delete_status = {
    "is_running": False,
    "employee_ids": [],
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {}
}

bulk_status_lock = threading.Lock()

def bulk_delete_ids_from_selected_machines(employee_ids: list, target_ips: list):
    """
    Parallel bulk deletion across a specific list of machines.
    Updates the global bulk_delete_status as it progresses.
    """
    results = {}
    total = len(target_ips)

    # Reset/Update status if we're starting a fresh operation
    with bulk_status_lock:
        bulk_delete_status["total_machines"] = total
        bulk_delete_status["processed_count"] = 0
        bulk_delete_status["results"] = {}

    with ThreadPoolExecutor(max_workers=max(1, total)) as executor:
        future_to_ip = {executor.submit(bulk_delete_users_from_machine, ip, employee_ids): ip for ip in target_ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            with bulk_status_lock:
                bulk_delete_status["current_ip"] = ip

            try:
                result = future.result()
                if len(result) == 2:
                    deleted_count, status = result
                    details = {}
                else:
                    deleted_count, status, details = result
                results[ip] = {"deleted": deleted_count, "status": status, "details": details}
            except Exception as e:
                results[ip] = {"deleted": 0, "status": f"Error: {str(e)}"}

            with bulk_status_lock:
                bulk_delete_status["processed_count"] += 1
                bulk_delete_status["results"][ip] = results[ip]

    return results

def bulk_delete_users_from_all_machines(employee_ids: list):
    """
    Background task for bulk deletion across ALL machines.
    Maintains compatibility with existing global delete status.
    """
    global bulk_delete_status
    with bulk_status_lock:
        if bulk_delete_status["is_running"]: return
        bulk_delete_status.update({
            "is_running": True,
            "employee_ids": employee_ids,
            "results": {},
            "processed_count": 0,
            "current_ip": "Starting...",
            "total_machines": 0
        })

    try:
        ips = get_machine_list()
        # This function now handles updating processed_count and current_ip internally
        results = bulk_delete_ids_from_selected_machines(employee_ids, ips)

        with bulk_status_lock:
            bulk_delete_status["current_ip"] = "Done"

    finally:
        with bulk_status_lock:
            bulk_delete_status["is_running"] = False

def run_bulk_delete_on_machines(employee_ids: list, target_ips: list):
    """
    Background task for bulk deletion across SELECTED machines.
    """
    global bulk_delete_status
    with bulk_status_lock:
        if bulk_delete_status["is_running"]: return
        bulk_delete_status.update({
            "is_running": True,
            "employee_ids": employee_ids,
            "results": {},
            "processed_count": 0,
            "current_ip": "Starting...",
            "total_machines": len(target_ips)
        })

    try:
        # This helper now updates progress internally
        bulk_delete_ids_from_selected_machines(employee_ids, target_ips)
        with bulk_status_lock:
            bulk_delete_status["current_ip"] = "Done"
    finally:
        with bulk_status_lock:
            bulk_delete_status["is_running"] = False
# State for push/clone operations


# State for sync employee operations
sync_employee_status: Dict[str, Any] = {
    "is_running": False,
    "employee_id": "",
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {}
}
sync_employee_status_lock = threading.Lock()

def sync_employee_to_machines(
    source_ip: str,
    employee_id: str,
    employee_name: str,
    target_ips: list
):
    """
    Syncs an employee's details (face template, photo, privilege, password)
    from a source Hanvon machine (or local registry DB) to target Hanvon machines.
    """
    global sync_employee_status
    with sync_employee_status_lock:
        if sync_employee_status["is_running"]:
            return
        sync_employee_status.update({
            "is_running": True,
            "employee_id": employee_id,
            "total_machines": len(target_ips),
            "processed_count": 0,
            "current_ip": "",
            "results": {}
        })

    # 1. Fetch employee details from source machine
    name = employee_name
    role = "employee"
    photo_base64 = ""
    face_data = []
    password = "123456"
    authority = 2

    # Get from DB registry to verify role/name first
    db = SessionLocal()
    try:
        from database import EmployeeLocalRegistry
        emp_reg = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == employee_id).first()
        if emp_reg:
            if not name and emp_reg.emp_name:
                name = str(emp_reg.emp_name)
            if emp_reg.privilege == 3 or emp_reg.privilege == 14:
                role = "admin"
                authority = 2
    except Exception as e:
        logger.warning(f"Error querying local registry for sync: {e}")
    finally:
        db.close()

    # Query source machine to get face templates/photos if online
    try:
        with HanvonClient(
            source_ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=10
        ) as client:
            # Check if this ID is a manager
            managers = client.get_manager_ids()
            if employee_id in managers:
                try:
                    manager_detail = client.get_manager(employee_id)
                    role = "super_admin" if _to_int(manager_detail.get("authority"), 2) == 0 else "admin"
                    authority = _to_int(manager_detail.get("authority"), 2)
                    password = manager_detail.get("password") or "123456"
                    photo_base64 = manager_detail.get("capturejpg") or ""
                except Exception as ex:
                    logger.warning(f"Failed to fetch manager details from source machine: {ex}")
            else:
                try:
                    # Retrieve employee photo and face templates
                    emp_detail = client.get_employee(employee_id)
                    if emp_detail:
                        if not name and emp_detail.get("name"):
                            name = str(emp_detail.get("name"))
                        photo_base64 = emp_detail.get("capturejpg") or ""
                        face_data = emp_detail.get("face_data") or []
                        role = "employee"
                except Exception as ex:
                    logger.warning(f"Failed to fetch employee details from source machine: {ex}")
    except Exception as e:
        logger.warning(f"Source machine {source_ip} offline or error during fetch: {e}")

    # 2. Add/update employee on each target machine
    for ip in target_ips:
        with sync_employee_status_lock:
            sync_employee_status["current_ip"] = ip

        try:
            with HanvonClient(
                ip,
                port=config.HANVON_PORT,
                secret_key=config.HANVON_SECRET_KEY,
                timeout=10
            ) as client:
                if role in ("admin", "super_admin"):
                    # For managers/admins, photo is REQUIRED by the device. If missing, we fail.
                    if not photo_base64:
                        raise ValueError("Photo (capturejpg) is required to register a Hanvon manager, but it is empty.")

                    client.set_manager(
                        manager_id=employee_id,
                        photo_base64=photo_base64,
                        password=password,
                        authority=authority
                    )
                else:
                    client.set_employee(
                        employee_id=employee_id,
                        name=name,
                        photo_base64=photo_base64,
                        face_data=face_data
                    )

            with sync_employee_status_lock:
                sync_employee_status["results"][ip] = "Success"
        except Exception as e:
            logger.error(f"Error syncing employee {employee_id} to machine {ip}: {e}")
            with sync_employee_status_lock:
                sync_employee_status["results"][ip] = str(e)
        finally:
            with sync_employee_status_lock:
                sync_employee_status["processed_count"] = int(sync_employee_status["processed_count"]) + 1

    with sync_employee_status_lock:
        sync_employee_status["is_running"] = False
