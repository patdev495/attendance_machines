from zk import ZK
from zk.user import User
from zk.finger import Finger
from database import SessionLocal, EmployeeMetadata, EmployeeFingerprint
from config import config
from shared.hardware import get_machine_list, update_machine_tags, get_all_machine_configs
from utils.encoding import sanitize_machine_name
import logging
import datetime
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import base64
import time
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# State for machine operations (deletion, etc.)
delete_status = {
    "is_running": False,
    "employee_id": None,
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {}
}

global_sync_status = {
    "is_running": False,
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {}
}

# Global state for enrollment progress
# { "ip": { "status": "waiting|success|failed|cancelled", "message": "...", "timestamp": 123 } }
enrollment_sessions: Dict[str, dict] = {}
enrollment_lock = threading.Lock()

status_lock = threading.Lock()
global_sync_lock = threading.Lock()

def get_devices_capacity_info():
    """Checks capacity for all machines in hardware list."""
    machines = get_machine_list()
    results = []
    for ip in machines:
        zk = ZK(ip, port=4370, timeout=5)
        conn = None
        try:
            conn = zk.connect()
            conn.read_sizes()
            results.append({
                "ip": ip,
                "status": "Online",
                "users": getattr(conn, 'users', 0),
                "users_cap": getattr(conn, 'users_cap', 0),
                "fingers": getattr(conn, 'fingers', 0),
                "fingers_cap": getattr(conn, 'fingers_cap', 0),
                "records": getattr(conn, 'records', 0),
                "records_cap": getattr(conn, 'records_cap', 0)
            })
        except Exception as e:
            results.append({
                "ip": ip,
                "status": "Offline",
                "error": str(e)
            })
        finally:
            if conn:
                try: conn.disconnect()
                except: pass
    return results

def get_users_from_machine(ip: str):
    """Fetches all users from a specific machine."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        user_list = []
        for u in users:
            user_list.append({
                "uid": u.uid,
                "user_id": u.user_id,
                "name": u.name,
                "privilege": u.privilege,
                "password": u.password,
                "group_id": u.group_id,
                "card": u.card
            })
        conn.enable_device()
        return user_list, "Success"
    except Exception as e:
        logger.error(f"Error fetching users from machine {ip}: {e}")
        return [], str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def delete_user_from_machine(ip: str, employee_id: str):
    """Deletes a user from a specific machine."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        target_user = next((u for u in users if u.user_id == str(employee_id)), None)
        
        result = "Not in device"
        if target_user:
            conn.delete_user(uid=target_user.uid, user_id=target_user.user_id)
            result = "Success"
            
        conn.enable_device()
        with status_lock:
            delete_status["results"][ip] = result
        return result
    except Exception as e:
        logger.error(f"Error deleting user from machine {ip}: {e}")
        msg = f"Error: {str(e)}"
        with status_lock:
            delete_status["results"][ip] = msg
        return msg
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def bulk_delete_users_from_machine(ip: str, employee_ids: list):
    """Deletes multiple users from a machine in a single connection."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    deleted_count = 0
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        user_map = {str(u.user_id): u for u in users}
        
        for emp_id in employee_ids:
            target_user = user_map.get(str(emp_id))
            if target_user:
                try:
                    conn.delete_user(uid=target_user.uid, user_id=target_user.user_id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {emp_id} from {ip}: {e}")
                    
        conn.enable_device()
        return deleted_count, "Success"
    except Exception as e:
        logger.error(f"Error bulk deleting from machine {ip}: {e}")
        return deleted_count, str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def update_user_name_on_machine(ip: str, employee_id: str, new_name: str):
    """Updates user's name on a specific machine."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False, encoding='windows-1258')
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        target = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target:
            return f"User {employee_id} not found on machine {ip}"
        
        safe_name = sanitize_machine_name(new_name)
        conn.set_user(
            uid=target.uid, name=safe_name, privilege=target.privilege, 
            password=target.password, group_id=target.group_id, 
            user_id=target.user_id, card=target.card
        )
        conn.enable_device()
        return "Success"
    except Exception as e:
        logger.error(f"Error updating name on machine {ip}: {e}")
        return str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def download_fingerprints_from_machine(ip: str, employee_id: str):
    """Downloads fingerprints for a user from a machine and saves to DB."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        target = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target:
            return 0, f"User {employee_id} not found on machine {ip}"
        
        templates = conn.get_templates()
        user_templates = [
            t for t in templates 
            if str(t.uid) == str(target.uid) or str(getattr(t, 'user_id', '')) == str(employee_id)
        ]
        
        if not user_templates:
            # Fallback to slot-by-slot scan
            for fid in range(10):
                try:
                    tmp = conn.get_user_template(uid=target.uid, temp_id=fid, user_id=target.user_id)
                    if tmp and tmp.template:
                        user_templates.append(tmp)
                except: continue
        
        if not user_templates:
            return 0, f"No fingerprints found for {employee_id} on {ip}."

        db = SessionLocal()
        count = 0
        try:
            db.query(EmployeeFingerprint).filter(EmployeeFingerprint.employee_id == employee_id).delete()
            for t in user_templates:
                template_data = getattr(t, 'template', None)
                if not template_data: continue
                template_str = base64.b64encode(template_data).decode('utf-8')
                new_f = EmployeeFingerprint(
                    employee_id=employee_id,
                    template_id=getattr(t, 'fid', getattr(t, 'temp_id', 0)),
                    template_data=template_str,
                    source_ip=ip
                )
                db.add(new_f)
                count += 1
            
            # Update privilege in registry/metadata
            from database import EmployeeLocalRegistry, EmployeeMetadata
            for model in [EmployeeLocalRegistry, EmployeeMetadata]:
                emp = db.query(model).filter(model.employee_id == employee_id).first()
                if emp:
                    emp.privilege = target.privilege

            db.commit()
        except Exception as e:
            db.rollback()
            return 0, str(e)
        finally: db.close()
            
        conn.enable_device()
        return count, "Success"
    except Exception as e:
        return 0, str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def bulk_download_fingerprints_from_machine(ip: str):
    """Downloads all fingerprints from a machine and maps them to DB."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        uid_map = {str(u.uid): u.user_id for u in users}
        templates = conn.get_templates()
        
        db = SessionLocal()
        count = 0
        try:
            target_ids = list(uid_map.values())
            db.query(EmployeeFingerprint).filter(EmployeeFingerprint.employee_id.in_(target_ids)).delete(synchronize_session=False)
            
            for t in templates:
                emp_id = uid_map.get(str(t.uid))
                if not emp_id: continue
                template_data = getattr(t, 'template', None)
                if not template_data: continue
                template_str = base64.b64encode(template_data).decode('utf-8')
                new_f = EmployeeFingerprint(
                    employee_id=emp_id,
                    template_id=getattr(t, 'fid', getattr(t, 'temp_id', 0)),
                    template_data=template_str,
                    source_ip=ip
                )
                db.add(new_f)
                count += 1
            
            # Update privileges for all users found on machine
            from database import EmployeeLocalRegistry, EmployeeMetadata
            for user in users:
                eid = str(user.user_id)
                for model in [EmployeeLocalRegistry, EmployeeMetadata]:
                    emp = db.query(model).filter(model.employee_id == eid).first()
                    if emp:
                        emp.privilege = user.privilege

            db.commit()
        except Exception as e:
            db.rollback()
            return 0, str(e)
        finally: db.close()
        conn.enable_device()
        return count, "Success"
    except Exception as e:
        return 0, str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def check_user_biometric_on_machine(ip: str, employee_id: str):
    """Checks biometric status on a machine efficiently."""
    zk = ZK(ip, port=4370, timeout=5, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        target = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target:
            return {"ip": ip, "status": "Online", "has_user": False, "has_finger": False}
        
        # Optimized: Check specific slots instead of downloading thousands of templates
        has_finger = False
        finger_count = 0
        # Most users have fingers in slots 0-9
        for fid in range(10):
            try:
                tmp = conn.get_user_template(uid=target.uid, temp_id=fid, user_id=target.user_id)
                if tmp and tmp.template:
                    has_finger = True
                    finger_count += 1
            except:
                continue
                
        conn.enable_device()
        return {"ip": ip, "status": "Online", "has_user": True, "has_finger": has_finger, "finger_count": finger_count}
    except Exception as e:
        logger.error(f"Error checking biometric on {ip}: {e}")
        return {"ip": ip, "status": "Online" if "connect" not in str(e).lower() else "Offline", "error": str(e), "has_user": False, "has_finger": False}
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

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

def update_user_name_all_machines(employee_id: str, new_name: str):
    """Updates name on machines and in DB."""
    ips = get_machine_list()
    results = {}
    for ip in ips:
        results[ip] = update_user_name_on_machine(ip, employee_id, new_name)
    
    db = SessionLocal()
    try:
        emp = db.query(EmployeeMetadata).filter(EmployeeMetadata.employee_id == employee_id).first()
        if emp:
            emp.emp_name = new_name
            db.commit()
    except Exception as e:
        logger.error(f"Error updating name in DB: {e}")
        db.rollback()
    finally: db.close()
    return results

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
                deleted_count, status = future.result()
                results[ip] = {"deleted": deleted_count, "status": status}
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
push_status = {
    "is_running": False,
    "employee_id": "",
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {}
}

push_status_lock = threading.Lock()

def push_fingerprints_to_machines(employee_id: str, target_ips: list):
    """
    Pushes fingerprints from DB to multiple machines.
    If user doesn't exist on target, it will be created first.
    """
    global push_status
    with push_status_lock:
        if push_status["is_running"]: return
        push_status.update({
            "is_running": True, 
            "employee_id": employee_id,
            "results": {}, 
            "processed_count": 0, 
            "current_ip": "",
            "total_machines": len(target_ips)
        })

    db = SessionLocal()
    try:
        # 1. Get fingerprints from DB
        fingerprints = db.query(EmployeeFingerprint).filter(EmployeeFingerprint.employee_id == employee_id).all()
        if not fingerprints:
            with push_status_lock:
                push_status["is_running"] = False
                push_status["results"]["General"] = "No fingerprints in DB for this employee"
            return
        
        # 2. Get user info from metadata/registry
        from database import EmployeeLocalRegistry
        emp_info = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == employee_id).first()
        emp_name = emp_info.emp_name if emp_info and emp_info.emp_name else employee_id
        emp_privilege = emp_info.privilege if emp_info and emp_info.privilege is not None else 0

        for ip in target_ips:
            with push_status_lock:
                push_status["current_ip"] = ip
            
            zk = ZK(ip, port=4370, timeout=10, force_udp=False)
            conn = None
            try:
                conn = zk.connect()
                conn.disable_device()
                
                # Check if user exists, otherwise create
                users = conn.get_users()
                target_user = next((u for u in users if u.user_id == str(employee_id)), None)
                
                if not target_user:
                    # Determine a new UID (some machines need unique UID)
                    new_uid = max([u.uid for u in users] + [0]) + 1
                    target_user = User(uid=new_uid, name=emp_name, privilege=emp_privilege, user_id=str(employee_id))
                    conn.set_user(uid=target_user.uid, name=target_user.name, privilege=target_user.privilege, user_id=target_user.user_id)
                elif target_user.privilege != emp_privilege:
                    # Update existing user privilege
                    target_user.privilege = emp_privilege
                    conn.set_user(uid=target_user.uid, name=target_user.name, privilege=target_user.privilege, user_id=target_user.user_id)
                
                # Push each fingerprint
                finger_objs = []
                for f in fingerprints:
                    template_data = base64.b64decode(f.template_data)
                    # Create Finger object: Finger(uid, fid, valid, template)
                    finger_objs.append(Finger(target_user.uid, f.template_id, 1, template_data))
                
                if finger_objs:
                    conn.save_user_template(target_user, fingers=finger_objs)
                
                conn.enable_device()
                with push_status_lock:
                    push_status["results"][ip] = "Success"
            except Exception as e:
                logger.error(f"Error pushing to {ip}: {e}")
                with push_status_lock:
                    push_status["results"][ip] = f"Error: {str(e)}"
            finally:
                if conn:
                    try: conn.disconnect()
                    except: pass
            
            with push_status_lock:
                push_status["processed_count"] += 1
                
    finally:
        db.close()
        with push_status_lock:
            push_status["is_running"] = False

# State for bulk push operations (list of users to list of machines)
bulk_push_status = {
    "is_running": False,
    "total_machines": 0,
    "processed_machines": 0,
    "total_employees": 0,
    "processed_employees_total": 0,
    "active_ips": [],
    "results": {}
}

bulk_push_lock = threading.Lock()

def _push_to_single_machine(ip, pushable_ids, fp_map, emp_map, emp_priv_map):
    """Push fingerprints to a single machine with delta sync. Runs in a thread."""
    global bulk_push_status
    
    with bulk_push_lock:
        bulk_push_status["active_ips"].append(ip)
    
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        
        users = conn.get_users()
        user_dict = {str(u.user_id): u for u in users}
        
        # Delta Sync: get existing templates to skip what's already there
        existing_templates = conn.get_templates()
        uid_to_user_id = {u.uid: str(u.user_id) for u in users}
        existing_fp_keys = set()
        for t in existing_templates:
            uid_user_id = uid_to_user_id.get(t.uid)
            if uid_user_id:
                existing_fp_keys.add((uid_user_id, t.fid))
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, eid in enumerate(pushable_ids):
            # 1. Ensure User object and Privilege are correct first
            target_user = user_dict.get(str(eid))
            stored_priv = emp_priv_map.get(eid, 0)
            
            user_was_created_or_updated = False
            if not target_user:
                new_uid = max([u.uid for u in users] + [0]) + 1
                target_user = User(uid=new_uid, name=emp_map.get(eid, eid), privilege=stored_priv, user_id=str(eid))
                conn.set_user(uid=target_user.uid, name=target_user.name, privilege=target_user.privilege, user_id=target_user.user_id)
                users.append(target_user)
                user_dict[str(eid)] = target_user
                user_was_created_or_updated = True
            elif target_user.privilege != stored_priv:
                # Update privilege if it has changed in our DB
                target_user.privilege = stored_priv
                conn.set_user(uid=target_user.uid, name=target_user.name, privilege=target_user.privilege, user_id=target_user.user_id)
                user_was_created_or_updated = True

            # 2. Check which fingerprints this employee is missing on this machine
            needed_fps = []
            for f in fp_map[eid]:
                if (eid, f.template_id) not in existing_fp_keys:
                    needed_fps.append(f)
            
            if not needed_fps:
                # All fingerprints already exist on this machine
                skip_count += 1
                # If we updated privilege, we count it as a partial success/activity even if no FPs
                with bulk_push_lock:
                    bulk_push_status["processed_employees_total"] += 1
                continue
            
            finger_objs = []
            for f in needed_fps:
                template_data = base64.b64decode(f.template_data)
                finger_objs.append(Finger(target_user.uid, f.template_id, 1, template_data))
            
            if finger_objs:
                try:
                    conn.save_user_template(target_user, fingers=finger_objs)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error pushing fingerprint for {eid} to {ip}: {e}")
                    error_count += 1
            
            with bulk_push_lock:
                bulk_push_status["processed_employees_total"] += 1
        
        conn.enable_device()
        with bulk_push_lock:
            bulk_push_status["results"][ip] = f"OK: {success_count} đẩy mới, {skip_count} đã có, {error_count} lỗi"
    except Exception as e:
        logger.error(f"Error bulk pushing to {ip}: {e}")
        with bulk_push_lock:
            bulk_push_status["results"][ip] = f"Lỗi kết nối: {str(e)}"
    finally:
        if conn:
            try: conn.disconnect()
            except: pass
        with bulk_push_lock:
            bulk_push_status["processed_machines"] += 1
            if ip in bulk_push_status["active_ips"]:
                bulk_push_status["active_ips"].remove(ip)

def bulk_push_fingerprints_to_machines(employee_ids: list, target_ips: list):
    global bulk_push_status
    with bulk_push_lock:
        if bulk_push_status["is_running"]: return
        bulk_push_status.update({
            "is_running": True, 
            "results": {}, 
            "processed_machines": 0, 
            "total_machines": len(target_ips),
            "total_employees": 0,
            "processed_employees_total": 0,
            "active_ips": []
        })

    db = SessionLocal()
    try:
        from database import EmployeeLocalRegistry
        fingerprints_db = db.query(EmployeeFingerprint).filter(EmployeeFingerprint.employee_id.in_(employee_ids)).all()
        fp_map = {}
        for f in fingerprints_db:
            if f.employee_id not in fp_map:
                fp_map[f.employee_id] = []
            fp_map[f.employee_id].append(f)
        
        pushable_ids = [eid for eid in employee_ids if eid in fp_map and fp_map[eid]]
        
        emp_infos = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id.in_(employee_ids)).all()
        emp_map = {e.employee_id: (e.emp_name if e.emp_name else e.employee_id) for e in emp_infos}
        emp_priv_map = {e.employee_id: (e.privilege if e.privilege is not None else 0) for e in emp_infos}
        for eid in employee_ids:
            if eid not in emp_map:
                emp_map[eid] = eid
            if eid not in emp_priv_map:
                emp_priv_map[eid] = 0

        with bulk_push_lock:
            # Total work = employees × machines (since each machine gets all employees)
            bulk_push_status["total_employees"] = len(pushable_ids) * len(target_ips)
        
        # Push to ALL machines in parallel
        with ThreadPoolExecutor(max_workers=max(1, len(target_ips))) as executor:
            futures = {
                executor.submit(_push_to_single_machine, ip, pushable_ids, fp_map, emp_map, emp_priv_map): ip 
                for ip in target_ips
            }
            for future in concurrent.futures.as_completed(futures):
                ip = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Thread error for {ip}: {e}")
                    with bulk_push_lock:
                        bulk_push_status["results"][ip] = f"Lỗi thread: {str(e)}"
                
    finally:
        db.close()
        with bulk_push_lock:
            bulk_push_status["is_running"] = False

clear_fp_status = {
    "is_running": False,
    "ip": "",
    "total_users": 0,
    "processed_users": 0,
    "result": ""
}

clear_fp_lock = threading.Lock()

def _safe_clear_data(conn):
    """Wrapper for conn.clear_data() — fixes Python 2→3 str/bytes bug in pyzk without modifying library source."""
    from zk import const as zk_const
    command = zk_const.CMD_CLEAR_DATA
    cmd_response = conn._ZK__send_command(command, b'')
    if cmd_response.get('status'):
        conn.next_uid = 1
        return True
    raise Exception("Can't clear data on device")

def clear_all_fingerprints_on_machine(ip: str):
    """Clear all user data and fingerprints on a machine, keeping attendance logs. Runs as background task."""
    global clear_fp_status
    with clear_fp_lock:
        if clear_fp_status["is_running"]: return
        clear_fp_status.update({
            "is_running": True, "ip": ip,
            "total_users": 0, "processed_users": 0, "result": ""
        })
    
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        
        # Get count for display
        users = conn.get_users()
        with clear_fp_lock:
            clear_fp_status["total_users"] = len(users)
        
        # One command clears all users+fingerprints, keeps attendance logs
        _safe_clear_data(conn)
        
        with clear_fp_lock:
            clear_fp_status["processed_users"] = len(users)
        
        conn.enable_device()
        with clear_fp_lock:
            clear_fp_status["result"] = f"Đã xóa {len(users)} người dùng và vân tay trên máy {ip}"
    except Exception as e:
        logger.error(f"Error clearing fingerprints on {ip}: {e}")
        with clear_fp_lock:
            clear_fp_status["result"] = f"Lỗi: {str(e)}"
    finally:
        if conn:
            try: conn.disconnect()
            except: pass
        with clear_fp_lock:
            clear_fp_status["is_running"] = False

def sync_time_on_machine(ip: str):
    """Synchronizes the time of a specific machine with the current system time."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        current_time = datetime.datetime.now()
        conn.set_time(current_time)
        conn.enable_device()
        return "Success"
    except Exception as e:
        logger.error(f"Error syncing time on machine {ip}: {e}")
        return str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def set_user_privilege_on_machine(ip: str, employee_id: str, privilege: int):
    """Sets a user's privilege on a specific machine and updates local DB."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        target_user = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target_user:
             return "User not found on device"
             
        # Update on device
        conn.set_user(uid=target_user.uid, name=target_user.name, privilege=privilege, user_id=target_user.user_id)
        conn.enable_device()
        
        # Sync to local DB
        db = SessionLocal()
        try:
             from database import EmployeeLocalRegistry, EmployeeMetadata
             for model in [EmployeeLocalRegistry, EmployeeMetadata]:
                 emp = db.query(model).filter(model.employee_id == employee_id).first()
                 if emp:
                     emp.privilege = privilege
             db.commit()
        finally: db.close()
        
        return "Success"
    except Exception as e:
        logger.error(f"Error setting privilege on machine {ip}: {e}")
        return str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def global_sync_all_fingerprints():
    global global_sync_status
    with global_sync_lock:
        if global_sync_status["is_running"]: return
        ips = get_machine_list()
        global_sync_status.update({
            "is_running": True, 
            "total_machines": len(ips),
            "processed_count": 0,
            "current_ip": "",
            "results": {}
        })
        
    db = SessionLocal()
    try:
        # 1. Wipe out existing DB fingerprints
        db.query(EmployeeFingerprint).delete()
        db.commit()
        
        master_fingerprints = {}
        
        for ip in ips:
            with global_sync_lock:
                global_sync_status["current_ip"] = ip
                
            zk = ZK(ip, port=4370, timeout=10, force_udp=False)
            conn = None
            try:
                conn = zk.connect()
                conn.disable_device()
                
                users = conn.get_users()
                uid_to_user_id = {u.uid: str(u.user_id) for u in users}
                
                templates = conn.get_templates()
                success_count = 0
                for t in templates:
                    actual_user_id = uid_to_user_id.get(t.uid)
                    if not actual_user_id:
                        continue # Orphaned template, ignore
                        
                    key = (actual_user_id, t.fid)
                    encoded_data = base64.b64encode(t.template).decode('utf-8')
                    
                    master_fingerprints[key] = EmployeeFingerprint(
                        employee_id=key[0],
                        template_id=key[1],
                        template_data=encoded_data,
                        source_ip=ip
                    )
                    success_count += 1
                
                # Update privileges in Registry/Metadata (capture highest privilege across all machines)
                from database import EmployeeLocalRegistry, EmployeeMetadata
                for user in users:
                    eid = str(user.user_id)
                    for model in [EmployeeLocalRegistry, EmployeeMetadata]:
                        emp = db.query(model).filter(model.employee_id == eid).first()
                        if emp:
                            # Only update if machine has higher privilege (e.g. Admin > User)
                            if emp.privilege is None or user.privilege > emp.privilege:
                                emp.privilege = user.privilege
                db.commit()
                
                conn.enable_device()
                with global_sync_lock:
                    global_sync_status["results"][ip] = f"Success ({success_count} vân tay)"
                    
            except Exception as e:
                logger.error(f"Global sync error on {ip}: {e}")
                with global_sync_lock:
                    global_sync_status["results"][ip] = f"Error: {str(e)}"
            finally:
                if conn:
                    try: conn.disconnect()
                    except: pass
            
            with global_sync_lock:
                global_sync_status["processed_count"] += 1
                
        # Now bulk insert all gathered fingerprints
        if master_fingerprints:
            db.bulk_save_objects(list(master_fingerprints.values()))
            db.commit()
            
    finally:
        db.close()
        with global_sync_lock:
            global_sync_status["is_running"] = False

def preview_bulk_push(employee_ids: list):
    """
    Preview the bulk push operation without actually executing it.
    Returns statistics about what will be pushed.
    """
    db = SessionLocal()
    try:
        from database import EmployeeLocalRegistry
        emp_count = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id.in_(employee_ids)).count()
        fingerprints_db = db.query(EmployeeFingerprint).filter(EmployeeFingerprint.employee_id.in_(employee_ids)).all()
        employees_with_fp = set(f.employee_id for f in fingerprints_db)
        return {
            "total_input_ids": len(employee_ids),
            "employees_found_in_db": emp_count,
            "employees_with_fingerprints": len(employees_with_fp),
            "total_fingerprints": len(fingerprints_db)
        }
    finally:
        db.close()

def bulk_sync_time_all_machines():
    """Synchronizes time across all configured machines."""
    ips = get_machine_list()
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, len(ips))) as executor:
        future_to_ip = {executor.submit(sync_time_on_machine, ip): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                status = future.result()
                results[ip] = status
            except Exception as e:
                results[ip] = f"Error: {str(e)}"
    return results

def enroll_user_remote(ip: str, employee_id: str, temp_id: int = 0):
    """
    Triggers the remote enrollment mode on a ZKTeco machine.
    Now updates enrollment_sessions for progress tracking.
    """
    with enrollment_lock:
        enrollment_sessions[ip] = {
            "status": "initiating",
            "message": "Connecting to machine...",
            "timestamp": time.time()
        }

    # Use a very long timeout (e.g., 30 minutes) to effectively "disable" the auto-timeout from software side
    zk = ZK(ip, port=4370, timeout=1800, verbose=False) 
    conn = None
    try:
        conn = zk.connect()
        
        with enrollment_lock:
            enrollment_sessions[ip].update({
                "status": "waiting",
                "message": "Machine screen active. Waiting for worker..."
            })

        # 1. Ensure user exists
        users = conn.get_users()
        target = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target:
            db = SessionLocal()
            try:
                from database import EmployeeLocalRegistry
                emp_info = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == employee_id).first()
                emp_name = emp_info.emp_name if emp_info and emp_info.emp_name else employee_id
                new_uid = max([u.uid for u in users] + [0]) + 1
                conn.set_user(uid=new_uid, name=emp_name, privilege=0, user_id=str(employee_id))
                target_uid = new_uid
            finally:
                db.close()
        else:
            target_uid = target.uid

        # 2. Trigger enrollment using low-level commands to avoid hardcoded 60s timeout
        # Reference: pyzk base.py lines 1189-1193
        from zk import const
        from struct import pack, unpack
        import codecs

        if zk.tcp:
            command_string = pack('<24sbb', str(employee_id).encode(), temp_id, 1)
        else:
            command_string = pack('<Ib', int(employee_id), temp_id)
        
        conn.cancel_capture()
        # Send STARTENROLL
        res = conn._ZK__send_command(const.CMD_STARTENROLL, command_string)
        if not res.get('status'):
            raise Exception(f"Machine rejected enrollment command: {res.get('code')}")

        # 3. Custom wait loop
        # We use a loop with short timeouts on the socket to check if 'cancelled' was set in global state
        success = False
        start_time = time.time()
        
        # Set a short socket timeout just for the recv calls so we can loop and check cancellation
        conn._ZK__sock.settimeout(2.0) 
        
        attempts = 3
        while attempts > 0:
            # Check if user cancelled via web UI
            with enrollment_lock:
                if ip in enrollment_sessions and enrollment_sessions[ip]["status"] == "cancelled":
                    logger.info(f"Enrollment on {ip} aborted by user.")
                    return {"status": "cancelled", "ip": ip}

            try:
                # Wait for progress data from machine
                data_recv = conn._ZK__sock.recv(1032)
                conn._ZK__ack_ok()
                
                # Logic to detect successful scans (simplified from pyzk)
                # res 0x64 (100) means a successful partial scan
                if len(data_recv) > 16:
                    res_code = unpack("H", data_recv.ljust(24, b"\x00")[16:18])[0]
                    if res_code == 0x64:
                        attempts -= 1
                        logger.info(f"Scan {3-attempts}/3 received for {ip}")
                    elif res_code == 0: # 0 often means final success
                        success = True
                        break
                    elif res_code in [4, 6]: # Failed or timeout codes
                        # We ignore internal machine timeouts if we want to stay in loop,
                        # but usually the machine exits the screen. 
                        # To be safe, we break if the machine says it failed.
                        break
            except Exception:
                # Timeout on recv (2.0s) - just loop and check cancellation
                continue

        # 4. Final Verification
        if not success:
            templates = conn.get_templates()
            success = any(t for t in templates if t.uid == target_uid and t.fid == temp_id)

        with enrollment_lock:
            if success:
                enrollment_sessions[ip].update({"status": "success", "message": "Enrollment successful!"})
            elif enrollment_sessions[ip]["status"] != "cancelled":
                enrollment_sessions[ip].update({"status": "failed", "message": "Enrollment failed or machine timed out."})

        return {"status": "success" if success else "failed", "ip": ip}
        
    except Exception as e:
        logger.error(f"Enrollment thread error for {ip}: {e}")
        with enrollment_lock:
            if ip in enrollment_sessions and enrollment_sessions[ip]["status"] != "cancelled":
                enrollment_sessions[ip].update({
                    "status": "failed",
                    "message": str(e)
                })
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def cancel_enroll_remote(ip: str):
    """
    Cancels the enrollment on the machine by sending CMD_CANCELCAPTURE via a new connection.
    """
    with enrollment_lock:
        if ip in enrollment_sessions:
            enrollment_sessions[ip]["status"] = "cancelled"
            enrollment_sessions[ip]["message"] = "Operation cancelled by user."

    # Send actual cancel command to hardware
    zk = ZK(ip, port=4370, timeout=5)
    conn = None
    try:
        conn = zk.connect()
        conn.cancel_capture()
        conn.enable_device() # Returns to standby
        return {"status": "cancelled", "ip": ip}
    except Exception as e:
        logger.error(f"Error cancelling enrollment on {ip}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def get_enroll_status(ip: str):
    """
    Returns the current enrollment status for an IP.
    """
    return enrollment_sessions.get(ip, {"status": "idle", "message": "No active session."})
