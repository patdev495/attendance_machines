from zk import ZK
from database import SessionLocal, AttendanceLog
from config import config
import logging
import datetime
import threading
from shared.hardware import get_machine_list

logger = logging.getLogger(__name__)

# Progress Tracking State for Logs
sync_status = {
    "is_running": False,
    "total_machines": 0,
    "current_machine_index": 0,
    "current_machine_ip": "",
    "processed_count": 0,
    "last_sync_time": None,
    "fail_count": 0,
    "total_added": 0
}

status_lock = threading.Lock()

def sync_all_machines():
    global sync_status
    machine_ips = get_machine_list()
    
    with status_lock:
        if not sync_status["is_running"]:
            # Direct call (not pre-initialized by router) - set state now
            sync_status["is_running"] = True
            sync_status["total_machines"] = len(machine_ips)
            sync_status["current_machine_index"] = 0
            sync_status["total_added"] = 0
            sync_status["fail_count"] = 0

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
        # PyZK initialization
        zk = ZK(ip, port=4370, timeout=10, force_udp=False)
        conn = None
        try:
            conn = zk.connect()
            attendances = conn.get_attendance()
            logger.info(f"Machine {ip}: Found {len(attendances)} records.")

            # Fetch all existing keys for this machine into a set to avoid duplicates
            existing_keys = set(
                db.query(AttendanceLog.employee_id, AttendanceLog.attendance_time)
                  .filter(AttendanceLog.machine_ip == ip)
                  .all()
            )

            new_logs = []
            for att in attendances:
                user_id = str(att.user_id)
                if user_id == '1': # Skip admin/system user
                    continue
                timestamp = att.timestamp.replace(tzinfo=None)
                
                if (user_id, timestamp) not in existing_keys:
                    new_item = AttendanceLog(
                        employee_id=user_id,
                        attendance_date=timestamp.date(),
                        attendance_time=timestamp,
                        machine_ip=ip
                    )
                    db.add(new_item)
                    new_logs.append(new_item)
                    existing_keys.add((user_id, timestamp))

                    if len(new_logs) >= 500: # Batch commit every 500 records
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
            with status_lock:
                sync_status["fail_count"] += 1
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
