from zk import ZK
from database import SessionLocal, AttendanceLog, EmployeeMetadata, EmployeeFingerprint
from config import config
from sqlalchemy import exists, and_
from utils.encoding import sanitize_machine_name
import logging
import datetime
import pandas as pd
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import threading

# Progress Tracking State
sync_status = {
    "is_running": False,
    "total_machines": 0,
    "current_machine_index": 0,
    "current_machine_ip": "",
    "processed_count": 0,
    "last_sync_time": None
}

delete_status = {
    "is_running": False,
    "employee_id": None,
    "total_machines": 0,
    "processed_count": 0,
    "current_ip": "",
    "results": {}
}

excel_sync_status = {
    "is_running": False,
    "progress": 0,
    "total": 0,
    "current_step": "",
    "error": None,
    "success_count": 0
}

def get_devices_capacity_info():
    machines = get_machine_list()
    results = []
    for ip in machines:
        zk = ZK(ip, port=4370, timeout=5)
        conn = None
        try:
            conn = zk.connect()
            # This populates users, users_cap, fingers, fingers_cap, records, records_cap
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
                try:
                    conn.disconnect()
                except:
                    pass
    return results
status_lock = threading.Lock()

def get_machine_list(file_path=config.MACHINES_FILE):
    try:
        with open(file_path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Could not read machines.txt: {e}")
        return []

def sync_all_machines():
    global sync_status
    machine_ips = get_machine_list()
    
    with status_lock:
        if sync_status["is_running"]:
            return 0
        sync_status["is_running"] = True
        sync_status["total_machines"] = len(machine_ips)
        sync_status["current_machine_index"] = 0
        sync_status["total_added"] = 0

    if not machine_ips:
        with status_lock:
            sync_status["is_running"] = False
        return 0

    local_total_added = 0
    db = SessionLocal()

    for i, ip in enumerate(machine_ips):
        with status_lock:
            sync_status["current_machine_index"] = i + 1
            sync_status["current_machine_ip"] = ip
            
        logger.info(f"Connecting to machine {i+1}/{len(machine_ips)} at {ip}...")
        zk = ZK(ip, port=4370, timeout=10, force_udp=False)
        conn = None
        try:
            conn = zk.connect()
            attendances = conn.get_attendance()
            logger.info(f"Machine {ip}: Found {len(attendances)} records.")

            # OPTIMIZATION: Fetch all existing keys for this machine into a set
            existing_keys = set(
                db.query(AttendanceLog.employee_id, AttendanceLog.attendance_time)
                  .filter(AttendanceLog.machine_ip == ip)
                  .all()
            )

            new_logs = []
            for att in attendances:
                user_id = str(att.user_id)
                if user_id == '1':
                    continue
                timestamp = att.timestamp.replace(tzinfo=None)
                
                # O(1) Memory lookup instead of O(N) DB query
                if (user_id, timestamp) not in existing_keys:
                    new_item = AttendanceLog(
                        employee_id=user_id,
                        attendance_date=timestamp.date(),
                        attendance_time=timestamp,
                        machine_ip=ip
                    )
                    db.add(new_item)
                    new_logs.append(new_item)
                    # Add to set so we don't duplicate within the same connection list
                    existing_keys.add((user_id, timestamp))

                    if len(new_logs) >= 500: # Batch commit every 500
                        db.commit()
                        local_total_added += len(new_logs)
                        new_logs = []

            if new_logs:
                db.commit()
                local_total_added += len(new_logs)
            
            logger.info(f"Machine {ip}: Finished. Sync added {local_total_added} records in total.")
            
        except Exception as e:
            logger.error(f"Error syncing machine {ip}: {e}")
            db.rollback()
        finally:
            if conn:
                try: conn.disconnect()
                except: pass

    db.close()
    
    with status_lock:
        sync_status["is_running"] = False
        sync_status["total_added"] = local_total_added
        sync_status["last_sync_time"] = datetime.datetime.now().isoformat()
    
    return local_total_added

def delete_user_from_all_machines(employee_id: str):
    """Deletes a user from all machines listed in machines.txt."""
    with status_lock:
        if delete_status["is_running"]:
            return
        delete_status["is_running"] = True
        delete_status["employee_id"] = employee_id
        delete_status["results"] = {}
        delete_status["processed_count"] = 0
        delete_status["current_ip"] = ""
    
    try:
        machine_ips = get_machine_list()
        delete_status["total_machines"] = len(machine_ips)
        
        for ip in machine_ips:
            delete_user_from_machine(ip, employee_id)
            with status_lock:
                delete_status["processed_count"] += 1
    finally:
        with status_lock:
            delete_status["is_running"] = False

def get_users_from_machine(ip: str):
    """Fetches all users from a specific machine."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        users = conn.get_users()
        # Convert ZK user objects to serializable dicts
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
    logger.info(f"Connecting to {ip} to delete user {employee_id}...")
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        
        # Fetch users to find UID
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
    """Deletes multiple users from a specific machine in a single connection."""
    logger.info(f"Connecting to {ip} to bulk delete {len(employee_ids)} users...")
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    deleted_count = 0
    try:
        conn = zk.connect()
        conn.disable_device()
        
        # Fetch users to find UIDs dynamically
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
        logger.error(f"Error bulk deleting users from machine {ip}: {e}")
        return deleted_count, str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def sync_employees_from_excel(file_path=config.EXCEL_FILE, file_bytes=None):
    """Reads Excel and updates the Employee table. Accepts a file path or a BytesIO object."""
    global excel_sync_status
    
    with status_lock:
        if excel_sync_status["is_running"]:
            return 0, "Already running"
        excel_sync_status.update({
            "is_running": True, 
            "progress": 0, 
            "total": 0, 
            "current_step": "Initializing...", 
            "error": None, 
            "success_count": 0
        })

    try:
        source = file_bytes if file_bytes is not None else file_path
        with status_lock:
            excel_sync_status["current_step"] = "Reading Excel file..."
            
        df = pd.read_excel(source)
        # Strip whitespace/newlines from column headers
        df.columns = df.columns.str.strip()
        
        # Expected columns: EMP_ID, SHIFT
        if 'EMP_ID' not in df.columns or 'SHIFT' not in df.columns:
            logger.error("Excel file missing required columns: EMP_ID, SHIFT")
            with status_lock:
                excel_sync_status.update({"is_running": False, "error": "Excel file missing required columns (EMP_ID, SHIFT)"})
            return 0, "Missing columns"

        total_rows = len(df)
        with status_lock:
            excel_sync_status["total"] = total_rows
            excel_sync_status["current_step"] = f"Processing {total_rows} employees..."

        db = SessionLocal()
        # OPTIMIZATION: Fetch all existing employees once to avoid N+1 queries
        existing_employees = {e.employee_id: e for e in db.query(EmployeeMetadata).all()}
        
        count = 0
        for idx, row in df.iterrows():
            emp_id = str(row['EMP_ID'])
            shift_val = str(row['SHIFT']).strip().upper()
            
            # Map TV to Resigned status
            status = 'TV' if shift_val == 'TV' else 'Active'
            
            # Use dictionary lookup instead of DB query
            employee = existing_employees.get(emp_id)
            if not employee:
                employee = EmployeeMetadata(employee_id=emp_id)
                db.add(employee)
                # Add to dictionary so we don't duplicate if same ID appears twice in Excel
                existing_employees[emp_id] = employee
            
            # Update values
            if shift_val != 'TV':
                employee.shift = shift_val
            employee.status = status
            
            if 'EMP_NAME' in df.columns and pd.notna(row['EMP_NAME']):
                employee.emp_name = str(row['EMP_NAME'])
            if 'DEPARTMENT' in df.columns and pd.notna(row['DEPARTMENT']):
                employee.department = str(row['DEPARTMENT'])
            if 'GROUP' in df.columns and pd.notna(row['GROUP']):
                employee.group = str(row['GROUP'])
            if 'START_DATE' in df.columns and pd.notna(row['START_DATE']):
                # Force pd.to_datetime to handle format consistently
                employee.start_date = pd.to_datetime(row['START_DATE']).date()
                
            count += 1
            
            # Update status object
            if count % 10 == 0 or count == total_rows:
                with status_lock:
                    excel_sync_status["progress"] = int((count / total_rows) * 100)
                    excel_sync_status["success_count"] = count
        
        db.commit()
        db.close()
        
        with status_lock:
            excel_sync_status.update({
                "progress": 100, 
                "success_count": count, 
                "current_step": f"Successfully synced {count} employees.",
                "is_running": False
            })
        return count, "Success"
        
    except Exception as e:
        logger.error(f"Failed to sync employees from Excel: {e}")
        import traceback
        traceback.print_exc()
        with status_lock:
            excel_sync_status.update({"is_running": False, "error": str(e)})
        return 0, str(e)
    finally:
        with status_lock:
            excel_sync_status["is_running"] = False

def update_user_name_on_machine(ip: str, employee_id: str, new_name: str):
    """Updates the user's name on a specific machine with safe encoding."""
    # Experiment with windows-1258 which better supports Vietnamese for many ZK models
    zk = ZK(ip, port=4370, timeout=10, force_udp=False, encoding='windows-1258')
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        
        # Must find the user first to get their full current record (uid, privilege, etc.)
        users = conn.get_users()
        target = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target:
            return f"User {employee_id} not found on machine {ip}"
        
        # Sanitize name: remove accents and trim to limit
        safe_name = sanitize_machine_name(new_name)
        
        conn.set_user(
            uid=target.uid, 
            name=safe_name, 
            privilege=target.privilege, 
            password=target.password, 
            group_id=target.group_id, 
            user_id=target.user_id,
            card=target.card
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

def update_user_name_all_machines(employee_id: str, new_name: str):
    """Updates the employee name across all machines and in the database."""
    # 1. Update machine IPs
    machine_ips = get_machine_list()
    results = {}
    for ip in machine_ips:
        res = update_user_name_on_machine(ip, employee_id, new_name)
        results[ip] = res
        
    # 2. Update local DB
    db = SessionLocal()
    try:
        emp = db.query(EmployeeMetadata).filter(EmployeeMetadata.employee_id == employee_id).first()
        if emp:
            emp.emp_name = new_name
            db.commit()
    except Exception as e:
        logger.error(f"Error updating name in DB: {e}")
        db.rollback()
    finally:
        db.close()
        
    return results

def download_fingerprints_from_machine(ip: str, employee_id: str):
    """Downloads all fingerprint templates for a user from a machine and saves to DB."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        
        # Get machine UID first
        users = conn.get_users()
        target = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target:
            return 0, f"User {employee_id} not found on machine {ip}"
        
        # Method 1: Try bulk retrieval (fastest if supported)
        logger.info(f"Attempting bulk fingerprint retrieval for {employee_id} on {ip}")
        templates = conn.get_templates()
        
        # Aggressive matching: Check both UID and UserID safely
        user_templates = [
            t for t in templates 
            if str(t.uid) == str(target.uid) or str(getattr(t, 'user_id', '')) == str(employee_id)
        ]
        
        # Method 2: If bulk found nothing, try slot-by-slot retrieval (0-9)
        if not user_templates:
            logger.info(f"Bulk retrieval failed for {employee_id}, falling back to slot-by-slot scan (0-9)")
            for fid in range(10):
                try:
                    # Provide both UID and UserID for maximum compatibility
                    tmp = conn.get_user_template(uid=target.uid, temp_id=fid, user_id=target.user_id)
                    if tmp and tmp.template:
                        user_templates.append(tmp)
                except Exception as e:
                    continue
        
        if not user_templates:
            return 0, f"No fingerprints found for employee {employee_id} (Internal UID: {target.uid}) on this machine."

        db = SessionLocal()
        import base64
        count = 0
        try:
            # Clear existing to avoid duplicates
            db.query(EmployeeFingerprint).filter(EmployeeFingerprint.employee_id == employee_id).delete()
            
            for t in user_templates:
                template_data = getattr(t, 'template', None)
                if not template_data:
                    continue
                # template is usually bytes
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
            logger.error(f"Error saving fingerprints to DB for {employee_id}: {e}")
            db.rollback()
            return 0, str(e)
        finally:
            db.close()
            
        conn.enable_device()
        return count, "Success"
    except Exception as e:
        logger.error(f"Error downloading fingerprints from machine {ip}: {e}")
        return 0, str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def bulk_download_fingerprints_from_machine(ip: str):
    """Downloads all fingerprint templates from a machine and saves them to the DB, mapping to local employees."""
    zk = ZK(ip, port=4370, timeout=10, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        
        # 1. Get all users to map UID -> UserID (Employee ID)
        logger.info(f"Bulk sync: Getting user list from {ip}")
        users = conn.get_users()
        uid_map = {str(u.uid): u.user_id for u in users}
        
        # 2. Get all templates
        logger.info(f"Bulk sync: Getting template list from {ip}")
        templates = conn.get_templates()
        
        db = SessionLocal()
        import base64
        count = 0
        try:
            # We'll use a transaction for all updates
            # Note: We only update fingerprints for users we found on this machine
            found_uids = set(uid_map.keys())
            
            # Clear existing fingerprints for THESE found users to avoid duplicates
            target_emp_ids = list(uid_map.values())
            db.query(EmployeeFingerprint).filter(EmployeeFingerprint.employee_id.in_(target_emp_ids)).delete(synchronize_session=False)
            
            for t in templates:
                emp_id = uid_map.get(str(t.uid))
                if not emp_id:
                    continue
                
                template_data = getattr(t, 'template', None)
                if not template_data:
                    continue
                
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
            logger.info(f"Bulk sync: Successfully saved {count} fingerprints from {ip}")
        except Exception as e:
            logger.error(f"Error during bulk fingerprint save: {e}")
            db.rollback()
            return 0, str(e)
        finally:
            db.close()
            
        conn.enable_device()
        return count, "Success"
    except Exception as e:
        logger.error(f"Error in bulk_download_fingerprints: {e}")
        return 0, str(e)
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def check_user_biometric_on_machine(ip: str, employee_id: str):
    """Checks if a user has fingerprints on a specific machine."""
    zk = ZK(ip, port=4370, timeout=3, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        # Find user
        users = conn.get_users()
        target = next((u for u in users if u.user_id == str(employee_id)), None)
        
        if not target:
            return {"ip": ip, "status": "Online", "has_user": False, "has_finger": False}
        
        # Check templates
        templates = conn.get_templates()
        has_finger = any(str(t.uid) == str(target.uid) or str(getattr(t, 'user_id', '')) == str(employee_id) for t in templates)
        
        return {"ip": ip, "status": "Online", "has_user": True, "has_finger": has_finger}
    except Exception as e:
        return {"ip": ip, "status": "Offline", "error": str(e), "has_user": False, "has_finger": False}
    finally:
        if conn:
            try: conn.disconnect()
            except: pass

def get_biometric_coverage(employee_id: str):
    """Checks biometric status for an employee across all machines in parallel."""
    ips = get_machine_list()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, len(ips))) as executor:
        future_to_ip = {executor.submit(check_user_biometric_on_machine, ip, employee_id): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            results.append(future.result())
    return results

if __name__ == "__main__":
    count = sync_all_machines()
    print(f"Sync complete. Total new records added: {count}")
