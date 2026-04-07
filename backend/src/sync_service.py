from zk import ZK
from .database import SessionLocal, AttendanceLog, EmployeeMetadata
from .config import config
from sqlalchemy import exists, and_
import logging
import datetime
import pandas as pd
import threading

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
        count = 0
        for idx, row in df.iterrows():
            emp_id = str(row['EMP_ID'])
            shift_val = str(row['SHIFT']).strip().upper()
            
            # Map TV to Resigned status
            status = 'TV' if shift_val == 'TV' else 'Active'
            
            # Try to find existing employee
            employee = db.query(EmployeeMetadata).filter(EmployeeMetadata.employee_id == emp_id).first()
            if not employee:
                employee = EmployeeMetadata(employee_id=emp_id)
                db.add(employee)
            
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

if __name__ == "__main__":
    count = sync_all_machines()
    print(f"Sync complete. Total new records added: {count}")
