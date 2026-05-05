from zk import ZK
from zk.user import User
from zk.finger import Finger
from database import SessionLocal, EmployeeMetadata, EmployeeFingerprint
from config import config
from shared.hardware import get_machine_list
from utils.encoding import sanitize_machine_name
import logging
import datetime
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import base64

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

status_lock = threading.Lock()

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
                    target_user = User(uid=new_uid, name=emp_name, privilege=0, user_id=str(employee_id))
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
