from zk import ZK
from db import SessionLocal, AttendanceLog
from sqlalchemy import exists, and_
import logging
import datetime

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
    "total_added": 0,
    "last_sync_time": None
}
status_lock = threading.Lock()

def get_machine_list(file_path="machines.txt"):
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
            
            logger.info(f"Machine {ip}: Finished. Sync added {local_total_added} in total so far.")
            
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

if __name__ == "__main__":
    count = sync_all_machines()
    print(f"Sync complete. Total new records added: {count}")
